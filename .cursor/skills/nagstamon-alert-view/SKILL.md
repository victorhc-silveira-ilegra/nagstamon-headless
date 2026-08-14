---
name: nagstamon-alert-view
description: Formata o snapshot de alertas efetivos no stdout em cards Nagstamon (Client, Host, Service, Status, Duration, Started, Status information). Use when changing alert output, StdoutAlertSink, GoogleChatWebhookSink, alert_view, parsers AM/CGI, ledger/dedup, or when the user mentions colunas, card, UI/UX do alerta.
---

# Snapshot de alerta efetivo

A saida operacional (sink, nao log) e o produto. Logs nao repetem payload.

## Layout

```text
*[2026-08-14 14:00:00 -0300]*  *1 alerta efetivo*

*#1  CRITICAL*
*Client:*             core
*Host:*               db01.prod
*Service:*            DiskFull
*Status:*             CRITICAL
*Duration:*           0d 2h 15m
*Started:*            14/08/2026 11:45:00
*Status information:* filesystem /var is 95 percent full
```

Labels em `*negrito*` (Chat). Colunas alinhadas com NBSP para o Chat nao colapsar espacos. Mesmo texto no stdout.

Com `DEDUP_ENABLED` (ledger ligado): cada alerta claimed vira um `publish([alert])` — cabecalho `1 alerta efetivo`, card `#1`, um POST no Google Chat com o mesmo texto. Com dedup off: um publish da lista efetiva (plural `N alertas efetivos` se N>1). Zero alertas = so o cabecalho.

## Regras

- Formatacao em `domain/services/alert_view.py`; `StdoutAlertSink` imprime e emite `poll.sink.published`.
- `GoogleChatWebhookSink` envia o mesmo texto (`render_effective_alerts`), um POST por publish, com `Lock`; HTTP/rede: `poll.gchat.failed` e raises; o use case faz `release` do fingerprint.
- Fluxo com ledger: `try_claim` → `publish` → `confirm`; fingerprint inclui `host` (`DEDUP_LEDGER_PATH` = arquivo com flock; vazio = memoria).
- Inicio conhecido (`starts_at` ou duracao) anterior ao boot do daemon nao entra no snapshot.
- Fuso = `FILTER_TIMEZONE` (worker injeta).
- Ordenar CRITICAL, WARNING, demais; depois Client, Host, Service.
- AM: Host de `hostname|host|pod|instance|application|namespace`; Info de `description|summary|message|title`.
- CGI: tabelas aninhadas do status.cgi; Host/Service dos href `host=`/`service=`; Duration `0d 2h 15m` (espacos normalizados); Started derivado da duracao se nao houver `starts_at`; ack via `statusCRITICALACK` ou texto acknowledged.
- Sem emojis, sem one-liner antigo, sem comentarios no codigo.
- UI do card: labels em negrito (`*Label:*`) e tabulação com NBSP (Chat preserva colunas).
