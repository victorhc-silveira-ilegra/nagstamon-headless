# Infra Docker

Stack minima para rodar o daemon headless. Nao inclui monitores (Alertmanager/Nagios): eles sao alcancados via rede do host e proxy.

## Servico

- Imagem: `nagstamon-headless:local` (Python 3.11, pacote `nagstamon-headless`)
- `network_mode: host` para usar o proxy e rotas locais
- Volume somente leitura: `${HOST_SERVERS_DIR:-~/.nagstamon/servers}` → `/etc/nagstamon/servers`
- Volume do ledger: `../../data` → `/var/lib/nagstamon-headless` (`DEDUP_LEDGER_PATH`)
- `SERVERS_DIR=/etc/nagstamon/servers` dentro do container
- `SOUND_ENABLED=false` no compose (container sem dispositivo de audio)

## Comandos

```bash
cp .env.example .env
make docker-up
make docker-smoke
make docker-logs
make docker-ps
make docker-down
```

`make docker-smoke` exige `.env` real (`PROXY_ADDR`, `VPN_IFACE`, `HOST_SERVERS_DIR`). Confere se a VPN esta UP, se a rota do proxy passa pela iface VPN e se o proxy aceita TCP; depois constroi a imagem e dispara um `docker run` one-shot (`nagstamon-headless-smoke`, `--max-cycles 1`, `--network host`) **sem** usar o `container_name` do daemon. Monta o mesmo `data/` do daemon (`DEDUP_LEDGER_PATH` compartilhado + flock). Pode rodar com `make docker-up` ja no ar. Exige `worker.started` / `poll.cycle.started` / `poll.cycle.finished`, `servers_count>=1` e que nem todos os fetches falhem. Timeout de 300s. Script: [`infra/docker/smoke.sh`](../infra/docker/smoke.sh).

`make docker-logs` segue o stdout do daemon (snapshot + eventos INFO), sem prefixo do servico e sem `--timestamps` do Compose. `F=0` imprime o tail e sai; `LEVEL=all` inclui WARNING/ERROR; `T=1` liga o relogio do Docker; `P=1` devolve o prefixo `nagstamon-headless |`.

O IP/URL do proxy vai em `PROXY_ADDR` no `.env` local, nunca no compose versionado. VPN (iface/endereco) tambem fica so no `.env` local (`VPN_IFACE`, `VPN_ADDR`).

## Arquivos

- [`infra/docker/Dockerfile`](../infra/docker/Dockerfile)
- [`infra/docker/docker-compose.yml`](../infra/docker/docker-compose.yml)
- [`infra/docker/smoke.sh`](../infra/docker/smoke.sh)
