---
name: nagstamon-alert-view
description: Formata o snapshot de alertas efetivos (stdout e Google Chat em mensagem texto) com colunas Client Host Service Status Duration Started Status information. Use when changing alert output, StdoutAlertSink, GoogleChatWebhookSink, alert_view, alert_hold/hold-down, parsers AM/CGI, ledger/dedup, or when the user mentions colunas, card, UI/UX do alerta.
---

# Snapshot de alerta efetivo

A saida operacional (sink, nao log) e o produto. Logs nao repetem payload.

## Layout

```text
*#1  CRITICAL*
*Status:*                CRITICAL
*Client:*                core
*Host:*                  db01.prod
*Service:*               DiskFull
*Ambiente:*              PRD
*Duração no Nagstamon:*  0d 2h 15m
*Horário do envio:*      14:00:00 (14/08/2026)
*Início do alarme:*      11:45:00 (14/08/2026)
*Status information:*    filesystem /var is 95 percent full
*Criticidade SLA:*       Muito Crítico (Carência: 10m)
*Tempo decorrido (SLA):* 8100s (135m 0s)
*ID do Incidente (SLA):* core/DiskFull/db01.prod
```

Stdout e Google Chat usam o **mesmo** texto plano (`text` do webhook, sem card JSON e sem fence monoespaçado). Labels em `*negrito*` e colunas com NBSP. Valores alinhados apos o label mais longo (`Tempo decorrido (SLA):`).

Com `DEDUP_ENABLED` (ledger ligado): cada alerta claimed vira um `publish([alert])` — cabecalho `1 alerta efetivo`, bloco `#1`, um POST no Google Chat com o mesmo texto. Com dedup off: um publish da lista efetiva (plural `N alertas efetivos` se N>1). Zero alertas = so o cabecalho.

## Regras

- Formatacao em `domain/services/alert_view.py`; `StdoutAlertSink` imprime e emite `poll.sink.published`.
- `GoogleChatWebhookSink` envia o mesmo texto (`render_effective_alerts`), um POST por publish, com `Lock`; HTTP/rede: `poll.gchat.failed` e raises; o use case faz `release` do fingerprint.
- Fluxo com ledger: `try_claim` → `publish` → `confirm`; fingerprint identifica o problema (`server`/`alertname`/`app`/`host`, sem `desc` dinamico; `DEDUP_LEDGER_PATH` = arquivo com flock; vazio = memoria). `sent` nao expira (uma emissao por problema enquanto persistir).
- Kubernetes (`kubelet` / `k8s` / `kube` / alertname com `pod`) nao entra no snapshot.
- Inicio conhecido (`starts_at` ou duracao) anterior ao boot do daemon nao entra no snapshot (salvo no turno da manha com `WINDOW_ALLOW_PAST_ACTIVE_ALERTS=true`).
- Hold-down silencioso antes do snapshot: muito critico 10 min (`FILTER_HOLD_FAST_SECONDS`), mediano 15 min (`FILTER_HOLD_CRITICAL_SECONDS`), baixo 20 min (`FILTER_HOLD_WARNING_SECONDS`); tipo ganha de severidade; INFO nao dispara.
- Fuso = `WINDOW_TIMEZONE`; janela comercial = `WINDOW_ENABLED` / `WINDOW_START` / `WINDOW_END` / `WINDOW_DAYS` / `WINDOW_ALLOW_PAST_ACTIVE_ALERTS` (worker injeta).
- Ordenar CRITICAL, WARNING, demais; depois Client, Host, Service.
- AM: Host de `hostname|host|pod|instance|application|namespace`; Info de `description|summary|message|title`.
- CGI: tabelas aninhadas do status.cgi; Host/Service dos href `host=`/`service=`; Duration `0d 2h 15m` (espacos normalizados); Started derivado da duracao se nao houver `starts_at`; ack via `statusCRITICALACK` ou texto acknowledged.
- Sem emojis, sem one-liner antigo, sem comentarios no codigo.
- UI: mensagem de texto com labels em negrito (`*Label:*`) e tabulacao com NBSP; gutter = pad ate `Status information:` + 1 NBSP; sem cards estruturados do Chat e sem bloco de codigo.
