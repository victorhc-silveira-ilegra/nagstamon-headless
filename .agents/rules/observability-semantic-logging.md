# Regra de Observabilidade: Logging Semântico e Separação de Sinks

Esta regra define os padrões de emissão de logs estruturados, severidades e separação categórica entre logs de processo e sinks de entrega de alertas.

---

## 1. Separação Estrita: Sink vs Log

- **Sink (Produto Operacional)**: O snapshot de alertas entregue no terminal (`StdoutAlertSink`) e no webhook (`GoogleChatWebhookSink`) é o produto final do software.
- **Log (Diagnóstico do Sistema)**: Eventos emitidos via `log_event(logger, level, event, **fields)` que informam o ciclo de vida do worker, contagens agregadas e degradações.
- **Invariante**: Logs nunca duplicam a carga útil dos alertas em nível `INFO`. O payload formatado pertence exclusivamente ao sink.

---

## 2. Níveis de Severidade Semântica

| Nível | Uso Exclusivo | Comportamento Operacional |
| :--- | :--- | :--- |
| **`INFO`** | Apenas no caminho feliz estrutural: boot do worker, heartbeat do primeiro ciclo, confirmação de publicação de alertas e finalização com incidentes despachados. | Em ciclos ociosos subsequentes (sem novos alertas claimed), o worker opera em silêncio absoluto para evitar poluição visual. |
| **`WARNING`** | Falhas parciais onde o processo continua operando normalmente (fail-open): timeout de fetch em um servidor específico, rejeição transitória no Google Chat, ausência de player de áudio local. | Aciona investigação sem interrupção do daemon. |
| **`ERROR`** | Falhas fatais que impedem o funcionamento do daemon: erro de sintaxe/parsing nas configurações de boot, crash do loop principal. | O worker encerra imediatamente com exit code 1. |
| **`DEBUG`** | Detalhes de rastreamento e `exc_info` em exceções. | Desativado em produção por padrão. |

---

## 3. Catálogo de Eventos Semânticos

| Evento | Nível | Origem | Descrição |
| :--- | :--- | :--- | :--- |
| `worker.started` | `INFO` | Worker | Inicialização bem-sucedida do daemon |
| `worker.boot.failed` | `ERROR` | Worker | Falha fatal nas configurações de boot |
| `poll.cycle.started` | `INFO` | Worker | Início do primeiro ciclo de polling (heartbeat) |
| `poll.cycle.finished` | `INFO` | Worker | Finalização do primeiro ciclo ou ciclo com alertas claimed |
| `poll.cycle.failed` | `ERROR` | Worker | Exceção não tratada durante o ciclo de polling |
| `poll.cycle.skipped_in_flight`| `WARNING` | Worker | Ciclo anterior ainda em execução (`CycleGuard`) |
| `poll.sink.published` | `INFO` | Sink | Publicação de alertas realizada no stdout |
| `poll.gchat.published` | `INFO` | Sink | Publicação de alertas realizada com sucesso no Google Chat |
| `poll.gchat.failed` | `WARNING` | Sink | Falha de conexão ou HTTP no webhook do Google Chat |
| `poll.sound.failed` | `WARNING` | Sound | Falha ao reproduzir sinal sonoro (player inexistente) |
| `monitor.fetch.failed` | `WARNING` | HTTP Client | Falha ao consultar um monitor específico (fail-open) |
| `monitor.config.failed` | `WARNING` | Config Adapter| Falha ao processar arquivo `.conf` (fail-open) |
| `monitor.config.empty` | `WARNING` | Worker | Nenhum servidor ativo encontrado no primeiro ciclo |
| `monitor.ping.started` | `INFO` | CLI Ping | Início do diagnóstico de sondagem HTTP |
| `monitor.ping.finished` | `INFO` | CLI Ping | Conclusão do diagnóstico com métricas consolidadas |
| `monitor.ping.failed` | `WARNING` | CLI Ping | Servidor monitor inacessível durante sondagem |

---

## 4. Segurança e Redação de Segredos

- URLs de monitores com tokens de autenticação ou parâmetros de query são automaticamente mascaradas através do utilitário `redact_url(url)` (`?***`).
- Segredos de autenticação nunca são registrados em arquivos de log ou streams de saída.
- Arquivos de log diários (`nagstamon-YYYY-MM-DD.log`) gerados em `LOG_DIR` espelham exatamente os eventos `INFO` e os snapshots formatados, servindo de auditoria operacional unificada.
