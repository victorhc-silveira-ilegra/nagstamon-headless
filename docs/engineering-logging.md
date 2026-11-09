# Engenharia de Observabilidade e Logging Semântico

Diretrizes e especificações técnicas de observabilidade e emissão de logs estruturados no **Nagstamon Headless**.

## 1. Princípios de Observabilidade

1. **Separação entre Sink e Log**: O snapshot de alertas exibido no terminal (`stdout`) é a saída funcional do produto (`AlertSinkPort`), não uma linha de log. Os eventos de log fornecem contexto operacional (ciclos, conexões e publicações) e nunca devem poluir nem quebrar o snapshot funcional.
2. **Semântica e Rastreabilidade**: Cada linha de log emite um evento canônico tipado (`event=<dominio>.<acao>`) acompanhado de metadados estruturados em formato chave-valor (`text`) ou JSON (`json`).
3. **Silêncio Operacional em Ciclos Ociosos**: Ciclos de monitoramento que não encontram novos incidentes operam em completo silêncio após o ciclo inicial (heartbeat), evitando poluição de disco e ferramentas de agregação.
4. **Isolamento de Camadas**: Entidades de domínio e casos de uso da aplicação não possuem referências a loggers. A observabilidade é exercida exclusivamente na camada de apresentação e adaptadores de infraestrutura.

## 2. Níveis de Log e Critérios de Aplicação

| Nível | Critério de Disparo | Exemplo Prático |
| :--- | :--- | :--- |
| **INFO** | Marcos operacionais relevantes do fluxo normal | Inicialização do daemon (`worker.started`), heartbeat do primeiro ciclo, publicação bem-sucedida de incidente |
| **WARNING** | Degradação tolerada com continuidade operacional (fail-open) | Falha transitória de consulta a um servidor isolado (`monitor.fetch.failed`), overlap de ciclo evitado, webhook indisponível |
| **ERROR** | Falhas que impedem a execução do serviço | Erro fatal de inicialização (`worker.boot.failed`), falha irrecuperável no loop do processo |
| **DEBUG** | Detalhes diagnósticos aprofundados | Rastreamento de pilha de exceções (`exc_info`) durante investigação técnica |

## 3. Catálogo Canônico de Eventos

| Evento | Nível | Componente Emissor | Significado |
| :--- | :--- | :--- | :--- |
| `worker.started` | INFO | `presentation/worker` | Daemon inicializado com parâmetros de configuração |
| `worker.boot.failed` | ERROR | `presentation/worker` | Parâmetros de ambiente corrompidos ou inválidos |
| `poll.cycle.started` | INFO | `presentation/worker` | Início do primeiro ciclo de polling (heartbeat) |
| `poll.cycle.finished` | INFO | `presentation/worker` | Ciclo concluído com sucesso contendo novos alertas ou no heartbeat |
| `poll.cycle.failed` | ERROR | `presentation/worker` | Exceção não tratada na execução do ciclo |
| `poll.cycle.skipped_in_flight` | WARNING | `worker/cycle_guard` | Ciclo suprimido pois a execução anterior ainda está ativa |
| `poll.sink.published` | INFO | `StdoutAlertSink` | Snapshot impresso no terminal |
| `poll.gchat.published` | INFO | `GoogleChatHttpAdapter` | Snapshot transmitido com sucesso via webhook |
| `poll.gchat.failed` | WARNING | `GoogleChatHttpAdapter` | Falha de rede ou HTTP 5xx ao comunicar com o Google Chat |
| `poll.sound.failed` | WARNING | `PopenAlertSound` | Falha ao invocar binário de reprodução de áudio |
| `monitor.fetch.failed` | WARNING | Adapters HTTP | Erro de conexão ou HTTP 5xx ao consultar um servidor específico |
| `monitor.config.failed` | WARNING | `IniServerConfig` | Arquivo de servidor corrompido ou inacessível |
| `monitor.config.empty` | WARNING | `presentation/worker` | Nenhum servidor ativo encontrado para monitoramento |
| `monitor.ping.started` | INFO | `presentation/cli/ping` | Início da rotina de diagnóstico de servidores |
| `monitor.ping.finished` | INFO | `presentation/cli/ping` | Conclusão do diagnóstico com balanço de conectividade |
| `monitor.ping.failed` | WARNING | `presentation/cli/ping` | Servidor inacessível durante o probe pontual |

## 4. Gestão de Logs em Disco (Daily Tee)

O sistema implementa o espelhamento de fluxos (`tee`) gravando continuamente em arquivos diários no diretório configurado por `LOG_DIR` (padrão `logs/`):
- **Nomenclatura**: `nagstamon-YYYY-MM-DD.log`, respeitando o fuso horário corporativo configurado em `WINDOW_TIMEZONE`.
- **Filtro de Ruído**: O arquivo diário registra estritamente os eventos em nível `INFO` e os snapshots de alertas emitidos, descartando linhas ruidosas de debug ou warnings isolados.
- **Higienização Automática**: O comando `make app-clean` remove arquivos de datas retroativas, mantendo unicamente o log do dia corrente e o marcador `.gitkeep`.

## 5. Medidas de Proteção e Sanitização de Dados Sensíveis

- **Redação de URLs Corporativas**: Parâmetros de consulta e tokens embutidos em query strings (ex.: webhooks do Google Chat) são mascarados com `?***` antes da gravação.
- **Supressão de Bibliotecas Terceiras**: Os emissores de bibliotecas de transporte HTTP (`httpx`, `httpcore`, `urllib3`) são fixados em nível `WARNING`, impedindo vazamento de cabeçalhos de autorização ou dados brutos em nível `INFO`.
- **Ausência de Payloads Crus**: O sistema nunca descarrega JSONs brutos de resposta ou HTMLs de monitoramento nos logs de produção.
