# Changelog

## [1.2.0](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/compare/v1.1.1...v1.2.0) (2026-08-14)

## [1.1.1](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/compare/v1.1.0...v1.1.1) (2026-08-14)

## [1.1.0](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/compare/v1.0.0...v1.1.0) (2026-08-14)

## Unreleased

- Filtros alinhados ao Nagstamon: ack, hold-down (`FILTER_HOLD_*`) e janela via `.env`. Data/horario/intervalo so em Python.
- Som fail-open (`SOUND_ENABLED`) apos publish de alerta claimed; evento `poll.sound.failed` em WARNING.
- Snapshot stdout em cards: Client, Host, Service, Status, Duration, Started, Status information.
- Google Chat: mesmo card via `GCHAT_WEBHOOK_URL`; ledger persistente (`DEDUP_LEDGER_PATH`) com claim/confirm por alerta; `poll.gchat.failed` libera o fingerprint.
- Parser INI desofusca username/password no formato Nagstamon (zlib/base64/reverse).
- CGI Nagios: parser de tabelas aninhadas (`statusCRITICAL` / `statusCRITICALACK`); janela `FILTER_WINDOW_*` em `now` e no inicio do alerta (hoje), quando conhecido.
- Cards: Duration com espacos normalizados; Started no CGI via duracao, formato BR `DD/MM/YYYY HH:MM:SS`; aspas envolventes do AM removidas; logs no stdout para nao fatiar o snapshot no `docker logs`.
- AM: Host tambem de `pod` e `namespace`. `make docker-logs` segue INFO + cards, sem prefixo/timestamps do Compose (`F=0` uma vez; `LEVEL=all` todos os niveis; `T=1` / `P=1` para religar).
- `make docker-smoke`: VPN/proxy + um ciclo real (`docker run` one-shot, `--max-cycles 1`) com os `*.conf` do host; nao disputa o container do `docker-up`.
- Hold-down SRE: `FILTER_HOLD_FAST/CRITICAL` 180s, `FILTER_HOLD_WARNING` 600s; INFO e sem inicio conhecido nao disparam; tipo ganha de severidade.
- Nao despacha alerta cujo inicio conhecido e anterior ao boot do daemon.
- Card: labels em negrito (markdown do Chat) e colunas alinhadas com NBSP.

## 1.0.0 (2026-08-13)

## 1.0.0

- Daemon headless em DDD / hexagonal (Alertmanager + Nagios CGI, filtros Nagstamon, stdout).
- Dedup in-memory (`try_claim`/`release`) e `CycleGuard` contra ciclo sobreposto.
- Logs semanticos: INFO no caminho feliz, WARNING em fail-open/overlap, ERROR em boot ou ciclo quebrado.
- Gates de qualidade Python (Ruff, mypy strict, vulture, pytest 100% branch, bandit, pip-audit).
- Runtime Docker minimo em `infra/docker`.
- CI GitHub Actions (lint, test, security, semantic-release).
