# Changelog

## [1.7.0](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/compare/v1.6.0...v1.7.0) (2026-08-17)

## [1.6.0](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/compare/v1.5.0...v1.6.0) (2026-08-17)

## Unreleased

- Janela comercial respeita `WINDOW_ENABLED` (default `true`; `false` ignora horario e dias uteis).
- Filtro de ruido Kubernetes (`kubelet` / `k8s` / `kube` / alertname com `pod`).
- Ledger nao republica fingerprint `sent` (uma emissao ate `release` ou apagar o arquivo).
- Arquivo diario em `LOG_DIR` segue o recorte do `make docker-logs` (INFO + snapshot).

## [1.5.0](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/compare/v1.4.0...v1.5.0) (2026-08-17)

## [1.4.0](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/compare/v1.3.1...v1.4.0) (2026-08-14)

## [1.3.1](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/compare/v1.3.0...v1.3.1) (2026-08-14)

## [1.3.0](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/compare/v1.2.0...v1.3.0) (2026-08-14)

## [1.2.0](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/compare/v1.1.1...v1.2.0) (2026-08-14)

## [1.1.1](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/compare/v1.1.0...v1.1.1) (2026-08-14)

## [1.1.0](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/compare/v1.0.0...v1.1.0) (2026-08-14)

## Unreleased

- Filtros alinhados ao Nagstamon: ack, hold-down (`FILTER_HOLD_*`) e janela via `.env` (`FILTER_WINDOW_*`, `FILTER_WEEKDAYS` seg–sex). Data/horario/intervalo so em Python.
- Som fail-open (`SOUND_ENABLED`) apos publish de alerta claimed; evento `poll.sound.failed` em WARNING.
- Snapshot stdout em texto (bloco por alerta): Client, Host, Service, Status, Duration, Started, Status information.
- Google Chat: mesma mensagem `text` via `GCHAT_WEBHOOK_URL` (sem card estruturado); ledger persistente (`DEDUP_LEDGER_PATH`) com claim/confirm por alerta; `poll.gchat.failed` libera o fingerprint.
- Parser INI desofusca username/password no formato Nagstamon (zlib/base64/reverse).
- CGI Nagios: parser de tabelas aninhadas (`statusCRITICAL` / `statusCRITICALACK`); janela `FILTER_WINDOW_*` e `FILTER_WEEKDAYS` em `now` e no inicio do alerta (hoje), quando conhecido.
- Snapshot: Duration com espacos normalizados; Started no CGI via duracao, formato BR `DD/MM/YYYY HH:MM:SS`; aspas envolventes do AM removidas; logs no stdout para nao fatiar o snapshot no `docker logs`.
- AM: Host tambem de `pod` e `namespace`. `make docker-logs` segue INFO + snapshot, sem prefixo/timestamps do Compose (`F=0` uma vez; `LEVEL=all` todos os niveis; `T=1` / `P=1` para religar).
- `make docker-smoke`: VPN/proxy + um ciclo real (`docker run` one-shot, `--max-cycles 1`) com os `*.conf` do host; nao disputa o container do `docker-up`.
- Hold-down SRE por criticidade: muito critico 10 min (`FILTER_HOLD_FAST` 600), mediano 15 min (`FILTER_HOLD_CRITICAL` 900), baixo 20 min (`FILTER_HOLD_WARNING` 1200); INFO e sem inicio conhecido nao disparam; tipo ganha de severidade.
- Nao despacha alerta cujo inicio conhecido e anterior ao boot do daemon.
- Snapshot: labels em negrito (markdown do Chat) e colunas alinhadas com NBSP; webhook como mensagem de texto (sem fence monoespaçado / card estruturado).
- Log diario em `logs/nagstamon-YYYY-MM-DD.log` (`LOG_DIR`; tee de stdout/stderr com flush); Docker monta `logs/` no host; `make app-clean` remove logs que nao sejam do dia atual.
- Nomes de config alinhados ao padrao corporativo: `GCHAT_WEBHOOK_URL`, `WINDOW_*` (incluindo `WINDOW_ENABLED`), `REFRESH_INTERVAL_SECONDS` (sem aliases legados).

## 1.0.0 (2026-08-13)

## 1.0.0

- Daemon headless em DDD / hexagonal (Alertmanager + Nagios CGI, filtros Nagstamon, stdout).
- Dedup in-memory (`try_claim`/`release`) e `CycleGuard` contra ciclo sobreposto.
- Logs semanticos: INFO no caminho feliz, WARNING em fail-open/overlap, ERROR em boot ou ciclo quebrado.
- Gates de qualidade Python (Ruff, mypy strict, vulture, pytest 100% branch, bandit, pip-audit).
- Runtime Docker minimo em `infra/docker`.
- CI GitHub Actions (lint, test, security, semantic-release).
