---
name: nagstamon-alert-engine
description: Ciclo de vida do motor de alertas, filtragem por carência, janelas temporais e ledger de deduplicação
---

# Skill: Nagstamon Alert Engine

Esta habilidade rege as operações e regras de negócio do motor de polling, avaliação temporal e deduplicação de alertas do Nagstamon Headless.

## Topologia do Ciclo de Polling

O ciclo de monitoramento é orquestrado pelo caso de uso `CollectAndPublishAlertsUseCase` em `application/use_cases/collect_alerts.py`:

1. **Leitura de Servidores**: O `ServerRepository` carrega a configuração dos monitores (Alertmanager e Nagios CGI) a partir do diretório configurado (`SERVERS_DIR`).
2. **Coleta Concorrente**: O `MonitorGateway` efetua chamadas HTTP aos monitores respeitando timeouts e autenticação.
3. **Normalização**: As respostas heterogêneas são convertidas em entidades `Alert` puras do domínio.
4. **Filtragem de Janela Operacional**: Avaliação de dias úteis e faixas horárias (`WINDOW_*`).
5. **Filtragem de Carência (Hold-Down)**: Verificação de persistência mínima antes do primeiro disparo.
6. **Deduplicação Transacional**: Claim e confirmação no ledger de persistência.
7. **Publicação**: Envio dos snapshots para os canais configurados (`stdout` e `Google Chat`).

## Regras de Carência (Hold-Down)

Para eliminar ruídos efêmeros (flapping), um alerta só se torna elegível para notificação quando sua duração ativa atinge o limite configurado por severidade/criticidade:

| Criticidade / Severidade | Hold-Down Padrão | Variável de Ambiente |
| :--- | :--- | :--- |
| **Muito Crítico (Fast)** | 10 minutos (600s) | `FILTER_HOLD_FAST_SECONDS` |
| **Mediano / Crítico** | 15 minutos (900s) | `FILTER_HOLD_CRITICAL_SECONDS` |
| **Baixo / Warning** | 20 minutos (1200s) | `FILTER_HOLD_WARNING_SECONDS` |
| **Informativo (Info)** | Descarte imediato | N/A (nunca notifica) |

*Nota de precedência*: O tipo e severidade do incidente prevalecem na determinação da carência. Alertas cujo início seja indeterminado são sumariamente descartados.

## Protocolo do Ledger de Deduplicação

Para evitar renotificações em ciclos sucessivos de alertas já notificados e ainda ativos:

1. **Fingerprint Canônica**: Hash SHA-256 baseado em componentes imutáveis: `server` + `alertname` + `app` + `host`. Campos voláteis (ex.: timestamp, métrica oscilante, descrição textual dinâmica) são expressamente excluídos da chave.
2. **Fase Claim**: Antes da publicação, o engine solicita `claim(fingerprint)`. Se já confirmada no ledger como `sent`, a notificação é suprimida.
3. **Fase Confirm**: Após envio bem-sucedido aos canais de saída, registra `confirm(fingerprint)`. Um registro `sent` não expira enquanto o alarme estiver ativo.
4. **Fase Release**: Quando o alarme deixa de ser reportado no ciclo de coleta (resolvido na origem), o ledger libera o registro correspondente para permitir nova notificação caso o problema reincida no futuro.
