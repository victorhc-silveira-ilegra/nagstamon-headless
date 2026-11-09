---
name: nagstamon-alert-view
description: Diretrizes formais para renderização do snapshot de alerta em texto puro idêntico para stdout e Google Chat
---

# Skill: Nagstamon Alert View

Esta habilidade orienta a implementação, manutenção e teste da renderização de alertas consolidada pelo serviço de domínio `domain/services/alert_view.py`.

## Princípios Arquiteturais

1. **Paridade Absoluta**: O snapshot impresso no terminal (`stdout`) e a mensagem transmitida via webhook do Google Chat compartilham 100% do mesmo texto e formato.
2. **Mensagem em Texto Puro**: O Google Chat consome a API padrão enviando JSON `{"text": "..."}`. Não são utilizados cards estruturados, blocos visuais customizados nem emojis informais.
3. **Imutabilidade e Idempotência**: Dada a mesma entidade `Alert` e instante temporal de referência (`now`), a projeção do snapshot produz sempre a mesma string.

## Layout Canônico do Alerta

Cada alerta formatado deve seguir rigorosamente a seguinte estrutura de campos:

```text
*Status:* <STATUS_NORMALIZADO>
*Client:* <NOME_DO_CLIENTE>
*Host:* <NOME_DO_HOST>
*Service:* <NOME_DO_SERVICO>
*Ambiente:* <AMBIENTE>
*Duração no Nagstamon:* <DURACAO_NAGSTAMON>
*Horário do envio:* <DD/MM/AAAA HH:MM:SS>
*Início do alarme:* <DD/MM/AAAA HH:MM:SS>
*Status information:* <MENSAGEM_DO_ALARME>
*Criticidade SLA:* <CRITICIDADE_SLA>
*Tempo decorrido (SLA):* <TEMPO_DECORRIDO_SLA>
*ID do Incidente (SLA):* <ID_INCIDENTE_SLA>
```

Entre múltiplos alertas em um mesmo ciclo de publicação, utiliza-se como delimitador canônico:

```text
---
```

## Extração e Mapeamento de Metadados

1. **Client / Servidor**: Extraído do nome do servidor (`server_name`), normalizando prefixos e identificadores de clientes cadastrados.
2. **Ambiente**: Inferido a partir do hostname, monitor host ou tags (`PRD`, `HML`, `DEV`, `SBM`, `LEGADOS`).
3. **Início do Alarme**:
   - `starts_at` nativo (Alertmanager RFC 3339).
   - Se ausente ou Nagios CGI legado, parse de `duration_str` retroagindo a partir do instante do ciclo (`now - duration`).
   - Se indeterminado: o alerta deve ser descartado pelo filtro de carência e jamais emitido no snapshot.
4. **Criticidade SLA e Prazos**:
   - Mapeada segundo a tabela operacional de severidades e serviços.
   - `Tempo decorrido (SLA)` calcula a diferença entre `now` e o instante de disparo de carência.
   - `ID do Incidente (SLA)` projeta identificador estável para abertura e correlação de chamados.
