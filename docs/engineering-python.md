# Engenharia de Software em Python

Diretrizes formais de engenharia de software para o daemon **Nagstamon Headless** cobrindo padrões arquiteturais, tipagem estrita, gestão de ciclo de vida e garantias de qualidade.

## 1. Princípios de Engenharia e Boas Práticas

1. **Ausência de Comentários no Código**: O código-fonte em Python não deve conter comentários explicativos nem docstrings genéricas. A clareza decorre de nomenclatura expressiva, granularidade adequada de funções e contratos estritos.
2. **Tipagem Estrita (`mypy --strict`)**: Todas as assinaturas de funções, métodos e atributos de classe possuem anotações de tipo explícitas. Tipos genéricos como `Any` ou casts inseguros são sumariamente rejeitados.
3. **Imutabilidade e Encapsulamento**: Estruturas de dados são representadas prioritariamente por `dataclasses` congeladas (`frozen=True`) ou NamedTuples quando aplicável.
4. **Isolamento de Efeitos Colaterais**: Operações de entrada/saída (I/O), resolução de relógio do sistema e acessos a rede residem exclusivamente em adaptadores da camada de infraestrutura.

## 2. Portas e Adaptadores (Ports & Adapters)

Na camada de aplicação, todas as dependências externas são modeladas como protocolos puros (`typing.Protocol`), sem herança de classes base abstratas (ABCs) pesadas:

| Porta (Application) | Adaptador Concreto (Infrastructure) | Finalidade Operacional |
| :--- | :--- | :--- |
| `ServerConfigPort` | `IniServerConfigAdapter` | Leitura e atualização de arquivos de servidor `.conf` estilo Nagstamon |
| `MonitorClientPort` | `CompositeMonitorClient` | Polling paralelo a múltiplos servidores com balanceamento assíncrono |
| `MonitorProbePort` | `HttpMonitorProbeAdapter` | Validação de conectividade HTTP (2xx) para comandos de ping |
| `AlertSinkPort` | `StdoutAlertSink` / `GoogleChatHttpAdapter` | Publicação unificada de snapshots em terminal e chat |
| `AlertDispatchLedgerPort` | `FileAlertDispatchLedger` / `InMemoryAlertDispatchLedger` | Gestão de deduplicação transacional persistente |
| `AlertSoundPort` | `PopenAlertSoundAdapter` | Disparo não-bloqueante de alertas sonoros locais |
| `ClockPort` | `SystemClock` | Abstração do relógio do sistema para garantia de testes determinísticos |

## 3. Serviços de Domínio e Políticas

### 3.1 Classificação de Carência (Hold-Down Matrix)

O serviço `AlertHoldService` (`domain/services/alert_hold.py`) determina a latência mínima de disparo com base na severidade e semântica do incidente:

| Criticidade | Padrões de Alarme Reconhecidos | Carência Padrão |
| :--- | :--- | :--- |
| **Muito Crítico** | Hosts DOWN, partições cheias (`Disk Root`, `All disks`), certificados TLS expirando, falhas críticas de infraestrutura e serviços bancários | 10 min (`FILTER_HOLD_FAST_SECONDS=600`) |
| **Mediano** | Demais ocorrências classificadas como `CRITICAL` | 15 min (`FILTER_HOLD_CRITICAL_SECONDS=900`) |
| **Baixo** | Ocorrências com severidade `WARNING`, métricas oscilantes de CPU, memória, latência de rede e saturação de fila | 20 min (`FILTER_HOLD_WARNING_SECONDS=1200`) |
| **Informativo** | Ocorrências `INFO` ou sem início conhecido | Descarte imediato |

### 3.2 Filtragem de Ruído (`AlertFilterService`)

O serviço de filtragem descarta automaticamente:
- Alertas já reconhecidos no monitor (`acknowledged=True` ou silenciados por `silenced_by`).
- Alarmes com início indeterminado ou anterior à janela estipulada (salvo quando `WINDOW_ALLOW_PAST_ACTIVE_ALERTS=true`).
- Ruídos transitórios e probes de debug de legado.
- Alertas de infraestrutura interna do Kubernetes sem impacto em disponibilidade ou SLOs de produção.

### 3.3 Projeção Canônica (`AlertViewService`)

O formatador unificado `AlertViewService` projeta o alarme no padrão canônico de pares chave-valor em markdown limpo, sem caracteres de controle não padronizados:

```text
*Status:* CRITICAL
*Client:* inbursa-alertmanager-mip-prd
*Host:* app-servicos-prd-01
*Service:* HighErrorRate5xx
*Ambiente:* PRD
*Duração no Nagstamon:* 18m
*Horário do envio:* 09/11/2026 15:30:00
*Início do alarme:* 09/11/2026 15:12:00
*Status information:* HTTP 5xx rate exceeded 5% threshold over 5m window
*Criticidade SLA:* Muito Crítico (10m)
*Tempo decorrido (SLA):* 8m
*ID do Incidente (SLA):* inbursa-alertmanager-mip-prd/HighErrorRate5xx/app-servicos-prd-01
```

## 4. Estratégia de Testes e Qualidade

- **Cobertura Integral (100% Branch Coverage)**: A suíte executada via `pytest --cov` audita todas as linhas e caminhos condicionais. Nenhum código entra em produção sem teste unitário correspondente.
- **Isolamento de Ambiente**: Os testes configuram `NAGSTAMON_DISABLE_DOTENV=1`, garantindo que variáveis da máquina do desenvolvedor não interfiram nos resultados.
- **Transposição de IO**: Chamadas de rede utilizam `httpx.MockTransport` para emulação determinística de códigos HTTP e payloads heterogêneos.

## 5. Entrypoints e Execução

- **Worker de Produção**: `presentation/worker/main.py` (executado por `make app-run` ou binário de console `nagstamon-headless`).
- **Utilitário de Ping**: `presentation/cli/ping.py` (executado por `make app-ping` ou binário `nagstamon-headless-ping`).
- **Execução em Contêiner**: Inicializado via `make docker-up` com monitoramento via `make docker-logs`.
