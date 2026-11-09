# Regra de Negócio: Motor de Filtragem, Carência SLA e Deduplicação

Esta regra governa como alertas candidatos extraídos do Alertmanager e Nagios CGI são filtrados, classificados quanto a criticidade e despachados de forma idempotente.

---

## 1. Carência de SLA e Hold-down

Alertas operacionais possuem um tempo de carência (*hold-down*) antes de se tornarem efetivos para paging/notificação. Alertas que oscilam e se resolvem antes do período de carência não geram alertas no snapshot nem notificações no chat.

| Nível de Criticidade | Critérios de Associação | Variável de Ambiente | Carência Padrão |
| :--- | :--- | :--- | :--- |
| **Muito Crítico** | DOWN/unreachable, canais bancários/PIX/BCB/Celcoin, MQ stopped, connection refused/socket timeout, CrashLoopBackOff, OOMKilled, error budget, NodeNotReady, FailedMount, etcd quorum, disco/filesystem/tablespace/redo log, cert/TLS, login/SSO | `FILTER_HOLD_FAST_SECONDS` | 600s (10 min) |
| **Mediano** | Todos os demais alertas com severidade `CRITICAL` | `FILTER_HOLD_CRITICAL_SECONDS` | 900s (15 min) |
| **Baixo** | Alertas com severidade `WARNING` e métricas de CPU/memória/load/fila/latência/lock/ping/flap | `FILTER_HOLD_WARNING_SECONDS` | 1200s (20 min) |

- **Precedência**: O tipo de problema (palavras-chave na descrição/serviço) tem precedência sobre a severidade original reportada pelo monitor.
- **Severidade INFO**: Severidade informativa nunca é elegível para snapshot ou paging.
- **Início Desconhecido**: Alertas sem início determinável (`starts_at` ausente ou duração não parseável) são descartados por segurança.
- **Teto Máximo**: Alertas com duração superior a `FILTER_DURATION_MAX_SECONDS` (padrão 86400s / 24h) são suprimidos como incidentes conhecidos de longa duração.

---

## 2. Janela de Operação Comercial

A política `AlertFilterPolicy` gerencia o horário comercial através das variáveis:
- `WINDOW_ENABLED`: `true` (padrão) ativa o filtro horário; `false` desativa (processa alertas 24x7).
- `WINDOW_START` e `WINDOW_END`: Horário de início e término no fuso `WINDOW_TIMEZONE` (padrão `13:30` às `18:00`, fuso `America/Sao_Paulo`).
- `WINDOW_DAYS`: Dias da semana elegíveis (padrão `mon,tue,wed,thu,fri` / 0 a 4).
- `WINDOW_ALLOW_PAST_ACTIVE_ALERTS`: Quando `true` (padrão quando `WINDOW_START < 12:00`), permite que alertas que nasceram na madrugada anterior ao boot do daemon e que continuem ativos sejam elegíveis no primeiro ciclo.

---

## 3. Filtro de Ruídos e Falsos Positivos

- **Reconhecimento (Ack)**: Alertas marcados como reconhecidos (`acknowledged=True` no Nagios CGI ou `silenced_by` no Alertmanager) são suprimidos.
- **Falsos Positivos Conhecidos Suprimidos**:
  - Probes com substring `DEBUG` em severidade `WARNING`.
  - Checagens rotineiras `CHECK OBJETOS INVALIDOS` em `WARNING`.
  - Sensores Falcon `falcon-*`.
  - Expirations ruidosas: `KubeletServerCertificateExpiration`, `AltoConsumodeCPUPod`.
  - Alertas intrínsecos de teste: `Watchdog`, `InfoInhibitor`, `ExampleAlert`.
- **Alertas Essenciais Sempre Liberados**:
  - Incidentes de infraestrutura crítica: `ROOT MAIL BOX`, `CHECK TABELAS SEM ESTATISTICAS`, `DBA - CHECK REPLICACAO`, `App Java Heap`, `PUPPET-AGENT`, `All disks`, `TargetDown`.
  - Alertas com severidade `CRITICAL` nunca são silenciados por regras de ruído.

---

## 4. Deduplicação Idempotente (Ledger)

O envio de alertas para o Google Chat e stdout segue um protocolo transacional com ledger persistente (`DEDUP_LEDGER_PATH`):

1. **Fingerprint do Problema**: Chave determinística formada por `server/alertname/app/host`. Detalhes dinâmicos (como métricas variáveis ou texto de porcentagem) são omitidos da chave para evitar reemissões duplicadas do mesmo incidente.
2. **Ciclo Transacional**:
   - `try_claim(dedup_key)`: Reserva o alerta no ledger com status `pending`. Se já estiver `pending` ou `sent`, a emissão é ignorada.
   - `publish(alerts)`: Realiza a emissão no stdout e POST no webhook do Google Chat.
   - `confirm(dedup_key)`: Transiciona o alerta para `sent`. O status `sent` não expira enquanto o alarme continuar ativo.
   - `release(dedup_key)`: Em caso de falha de I/O na publicação (ex: indisponibilidade de rede no Google Chat), a reserva é liberada para nova tentativa no próximo ciclo.
3. **Persistência Concorrente**:
   - `FileAlertDispatchLedger`: Implementa lock de arquivo via `fcntl.flock` no Linux para garantir integridade caso múltiplos processos acessem o mesmo volume.
   - `InMemoryAlertDispatchLedger`: Utilizado em memória para testes e execuções voláteis.
