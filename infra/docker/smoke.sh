#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"

if [[ ! -f .env ]]; then
  echo "SMOKE FAIL: .env ausente (copie .env.example e preencha proxy/VPN/servers)" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "SMOKE FAIL: docker nao encontrado" >&2
  exit 1
fi

if ! command -v ip >/dev/null 2>&1; then
  echo "SMOKE FAIL: ip nao encontrado" >&2
  exit 1
fi

load_key() {
  local line
  line="$(grep -E "^${1}=" "${ROOT}/.env" | tail -n1 || true)"
  printf '%s' "${line#*=}"
}

HOST_SERVERS_DIR="$(load_key HOST_SERVERS_DIR)"
HOST_SERVERS_DIR="${HOST_SERVERS_DIR:-${HOME}/.nagstamon/servers}"
HOST_SERVERS_DIR="${HOST_SERVERS_DIR/#\~/${HOME}}"
PROXY_ADDR="$(load_key PROXY_ADDR)"
VPN_IFACE="$(load_key VPN_IFACE)"
VPN_ADDR="$(load_key VPN_ADDR)"

if [[ -z "${PROXY_ADDR}" || "${PROXY_ADDR}" == *"proxy.example"* ]]; then
  echo "SMOKE FAIL: PROXY_ADDR real obrigatorio no .env" >&2
  exit 1
fi
if [[ -z "${VPN_IFACE}" ]]; then
  echo "SMOKE FAIL: VPN_IFACE obrigatorio no .env" >&2
  exit 1
fi
if [[ ! -d "${HOST_SERVERS_DIR}" ]]; then
  echo "SMOKE FAIL: HOST_SERVERS_DIR inexistente: ${HOST_SERVERS_DIR}" >&2
  exit 1
fi
shopt -s nullglob
confs=("${HOST_SERVERS_DIR}"/*.conf)
shopt -u nullglob
if [[ ${#confs[@]} -eq 0 ]]; then
  echo "SMOKE FAIL: nenhum .conf em ${HOST_SERVERS_DIR}" >&2
  exit 1
fi

if ! ip -br link show "${VPN_IFACE}" 2>/dev/null | grep -qw UP; then
  auto_iface=""
  if [[ -n "${VPN_ADDR}" ]]; then
    auto_iface="$(ip -br addr show 2>/dev/null | grep -F "${VPN_ADDR}" | awk '{print $1}' | head -n1 || true)"
  fi
  if [[ -z "${auto_iface}" ]]; then
    auto_iface="$(
      ip -br link show 2>/dev/null \
        | grep -E "^(fctvpn|tun|ppp|wireguard|wg)" \
        | grep -w UP \
        | awk '{print $1}' \
        | head -n1 || true
    )"
  fi
  if [[ -n "${auto_iface}" ]]; then
    echo "SMOKE: VPN_IFACE=${VPN_IFACE} fora do ar, usando interface VPN ativa: ${auto_iface}"
    VPN_IFACE="${auto_iface}"
    if grep -q "^VPN_IFACE=" "${ROOT}/.env" 2>/dev/null; then
      sed -i "s/^VPN_IFACE=.*/VPN_IFACE=${auto_iface}/" "${ROOT}/.env" || true
    fi
  else
    echo "SMOKE FAIL: VPN ${VPN_IFACE} fora do ar" >&2
    exit 1
  fi
fi
if [[ -n "${VPN_ADDR}" ]] && ! ip -br addr show "${VPN_IFACE}" | grep -q "${VPN_ADDR}"; then
  echo "SMOKE FAIL: ${VPN_IFACE} sem endereco ${VPN_ADDR}" >&2
  exit 1
fi

proxy_net="${PROXY_ADDR#http://}"
proxy_net="${proxy_net#https://}"
proxy_host="${proxy_net%%[:/]*}"
proxy_port="${proxy_net#*:}"
proxy_port="${proxy_port%%/*}"
if [[ "${proxy_port}" == "${proxy_net}" || -z "${proxy_port}" ]]; then
  proxy_port=3128
fi

if ! ip route get "${proxy_host}" 2>/dev/null | grep -q "${VPN_IFACE}"; then
  echo "SMOKE FAIL: rota para ${proxy_host} nao usa ${VPN_IFACE}" >&2
  exit 1
fi
if ! timeout 8 bash -c "echo >/dev/tcp/${proxy_host}/${proxy_port}" 2>/dev/null; then
  echo "SMOKE FAIL: proxy inacessivel ${PROXY_ADDR}" >&2
  exit 1
fi

export HOST_SERVERS_DIR
export SOUND_ENABLED=false

COMPOSE=(
  docker compose
  --env-file "${ROOT}/.env"
  -f "${ROOT}/infra/docker/docker-compose.yml"
  --project-directory "${ROOT}/infra/docker"
)

SMOKE_NAME="nagstamon-headless-smoke"
IMAGE="nagstamon-headless:local"

"${COMPOSE[@]}" build nagstamon-headless

LOG="$(mktemp "${TMPDIR:-/tmp}/nagstamon-smoke.XXXXXX.log")"
cleanup() {
  docker rm -f "${SMOKE_NAME}" >/dev/null 2>&1 || true
  rm -f "${LOG}"
}
trap cleanup EXIT INT TERM

docker rm -f "${SMOKE_NAME}" >/dev/null 2>&1 || true

echo "SMOKE: 1 ciclo em ${IMAGE} (nao usa o container nagstamon-headless)"

mkdir -p "${ROOT}/data" "${ROOT}/logs"

set +e
timeout --kill-after=15 300 docker run --rm --init \
  --name "${SMOKE_NAME}" \
  --network host \
  --env-file "${ROOT}/.env" \
  -e SERVERS_DIR=/etc/nagstamon/servers \
  -e SOUND_ENABLED=false \
  -v "${HOST_SERVERS_DIR}:/etc/nagstamon/servers:ro" \
  -v "${ROOT}/data:/var/lib/nagstamon-headless" \
  -v "${ROOT}/logs:/var/log/nagstamon-headless" \
  -e DEDUP_LEDGER_PATH=/var/lib/nagstamon-headless/dispatch-ledger.json \
  -e LOG_DIR=/var/log/nagstamon-headless \
  "${IMAGE}" nagstamon-headless --max-cycles 1 2>&1 | tee "${LOG}"
STATUS="${PIPESTATUS[0]}"
set -e

if [[ "${STATUS}" -eq 124 ]]; then
  echo "SMOKE FAIL: timeout" >&2
  exit 1
fi
if [[ "${STATUS}" -ne 0 ]]; then
  echo "SMOKE FAIL: exit ${STATUS}" >&2
  exit 1
fi

missing=0
for event in worker.started poll.cycle.started poll.cycle.finished; do
  if ! grep -Eq "event=${event}|\"event\": \"${event}\"" "${LOG}"; then
    echo "SMOKE FAIL: ausente ${event}" >&2
    missing=1
  fi
done
if grep -Eq "event=worker.boot.failed|event=poll.cycle.failed|\"event\": \"worker.boot.failed\"|\"event\": \"poll.cycle.failed\"" "${LOG}"; then
  echo "SMOKE FAIL: evento de falha" >&2
  missing=1
fi
if grep -Eq "event=monitor.config.empty|\"event\": \"monitor.config.empty\"" "${LOG}"; then
  echo "SMOKE FAIL: nenhum servidor carregado" >&2
  missing=1
fi

servers_count="$(
  grep -E "event=poll.cycle.finished|\"event\": \"poll.cycle.finished\"" "${LOG}" \
    | grep -Eo "servers_count[=:] ?[0-9]+" \
    | tail -n1 \
    | grep -Eo "[0-9]+$" || true
)"
if [[ -z "${servers_count}" || "${servers_count}" -lt 1 ]]; then
  echo "SMOKE FAIL: servers_count invalido (${servers_count:-vazio})" >&2
  missing=1
fi

failed_count="$(grep -cE "event=monitor.fetch.failed|\"event\": \"monitor.fetch.failed\"" "${LOG}" || true)"
if [[ -n "${servers_count}" && "${failed_count}" -ge "${servers_count}" ]]; then
  echo "SMOKE FAIL: todos os fetches falharam (${failed_count}/${servers_count}) via ${PROXY_ADDR}" >&2
  missing=1
fi

if [[ "${missing}" -ne 0 ]]; then
  exit 1
fi

echo "SMOKE OK servers=${servers_count} fetch_failed=${failed_count} vpn=${VPN_IFACE} proxy=${PROXY_ADDR}"
