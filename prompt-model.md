# Prompt-Modelo de Engenharia

Contrato reutilizável derivado da arquitetura deste repositório (Nagstamon Headless). Utilize este arquivo como diretriz canônica para orientar agentes autônomos ou equipes na concepção, geração ou refatoração de sistemas corporativos com o mais alto padrão de engenharia: Domain-Driven Design (DDD), Arquitetura Hexagonal (Ports & Adapters), Test-Driven Development (TDD), observabilidade semântica, automação de testes contínuos e documentação viva.

O domínio de monitoramento Alertmanager / Nagios CGI serve como exemplo prático de implementação; os princípios aqui consolidados aplicam-se a qualquer domínio de negócio e ecossistema tecnológico.

## 1. Papel e Responsabilidade do Agente

Ao atuar sobre um novo domínio e linguagem, o agente deve:

- Projetar a topologia e a implementação aderindo rigorosamente aos contratos invariantes.
- Organizar a estrutura de pacotes e ferramentas nativas sem comprometer as fronteiras arquiteturais.
- Manter documentação técnica, Makefile, git hooks e quality gates perfeitamente sincronizados com o código.
- Priorizar a disciplina de TDD: testes unitários primeiro para regras de domínio e casos de uso; testes de integração para adapters de entrada/saída (I/O).
- Garantir que a base de código seja autoexplicativa, tipada estritamente e sem comentários desnecessários.

## 2. Contrato Invariante (Agnóstico a Linguagem)

### Camadas da Arquitetura Hexagonal

| Camada | Conteúdo e Responsabilidade | Dependência Permitida |
| :--- | :--- | :--- |
| **domain** | Entidades, Value Objects, Domain Services, Regras e Políticas de Negócio puras | Nenhuma dependência externa ao domínio |
| **application** | Casos de uso (Use Cases) e Portas (Ports - interfaces/protocolos de IO) | Exclusivamente `domain` |
| **infrastructure** | Adaptadores (Adapters) de IO, clientes HTTP/DB/Broker, persistência e configurações | `application` e `domain` |
| **presentation** | Pontos de entrada (CLI, Workers, APIs), composition root e orquestração de runtime | `application`, `domain` e `infrastructure` |

### Regras Arquiteturais Absolutas

1. As camadas `domain` e `application` nunca importam nem referenciam detalhes das camadas `infrastructure` ou `presentation`.
2. As Portas (Ports) são contratos abstratos (interfaces puras ou protocolos tipados). Os Adaptadores (Adapters) implementam esses contratos na camada de `infrastructure`.
3. Validações semânticas, invariantes de estado e regras temporais pertencem exclusivamente ao domínio.
4. Formatação de dados de saída e modelos de apresentação canônica pertencem ao domínio ou aplicação, nunca à interface externa de CLI/Controller.
5. Nem o `domain` nem o `application` realizam chamadas de logging ou acessam ferramentas de telemetria; o log é uma preocupação de infraestrutura e apresentação.
6. O Composition Root (injeção de dependências e amarração Settings -> Adapters -> Use Cases) vive estritamente na camada de `presentation`.

### Qualidade e Estilo

- **Zero Comentários**: Ausência de comentários explicativos no código de aplicação. A legibilidade é garantida por nomes semânticos, funções coesas e contratos explícitos.
- **Documentação Formal em PT-BR**: Redação técnica clara e precisa, sem emojis em código, logs ou documentação.
- **Conventional Commits**: Mensagens de commit padronizadas e descritas em português.
- **Isolamento de Segredos**: Parâmetros de runtime injetados exclusivamente por variáveis de ambiente via `.env` / `.env.example`. Nenhum segredo ou credencial real é versionado.
- **Cobertura Contínua**: Meta inegociável de 100% de cobertura de código com análise de desvios (`branch coverage`).
- **Dimensão Coesa de Arquivos**: Limite de aproximadamente 300 linhas por arquivo de código.
- **Tipagem Estrita**: Verificação estática máxima quando suportada pelo ambiente (`strict mode`).

## 3. Matriz de Qualidade Unificada (5 Estágios)

A validação contínua (local, hooks e CI/CD) opera sobre 4 áreas temáticas e 5 estágios determinísticos:

| Ordem | Estágio | Finalidade |
| :---: | :--- | :--- |
| **1** | `Lint` | Análise estática de formatação, sintaxe e conformidade de estilo |
| **2** | `Security` | Varredura de vulnerabilidades de dependências, segredos expostos e SAST |
| **3** | `Test` | Execução automatizada da suíte de testes com medição rigorosa de cobertura |
| **4** | `Validate` | Validação estrutural de contêineres, pipelines de CI e manifestos |
| **5** | `Build` | Validação de empacotamento, compilação de binários e imagens Docker |

O orquestrador unificado (`app/scripts/operations/clean_workspace.py` ou equivalente) centraliza a execução desses estágios para o desenvolvedor, para os git hooks e para o pipeline de CI/CD.

## 4. Observabilidade e Logging Semântico

- API padronizada de eventos estruturados: `log_event(logger, level, event, **fields)`.
- Catálogo de eventos estáveis com padrão `<contexto>.<entidade>.<acao>` (ex.: `monitor.cycle.started`, `alert.hold_down.skipped_too_new`, `notification.gchat.sent`).
- Nível `INFO` reservado para marcos relevantes do fluxo operacional (~3 linhas em caminho feliz). Ciclos ociosos não geram logs ruidosos de início e fim.
- Sanitização obrigatória: redação de credenciais, máscaras em URLs corporativas e ausência de dumps massivos de payloads.

## 5. Harness de Agentes Autônomos

O repositório expõe um harness universal em `.agents/` para consumo por qualquer LLM ou agente inteligente:
- `.agents/rules/`: Regras de conduta, arquitetura, testes e logging.
- `.agents/skills/`: Guias operacionais e manuais passo a passo para execução de rotinas complexas.

## 6. Prompt para Bootstrap de Novos Projetos

Copie o template abaixo para iniciar ou refatorar qualquer sistema corporativo seguindo este padrão:

```text
Você é um Engenheiro de Software Sênior. Projete e implemente a base de código abaixo em conformidade com o Contrato Invariante de Engenharia (DDD + Arquitetura Hexagonal + TDD + Matriz de Qualidade Unificada).

DADOS DO SISTEMA:
- Nome: <<<NOME_DO_PROJETO>>>
- Domínio de Negócio: <<<DESCRICAO_DO_PROBLEMA>>>
- Ecossistema / Linguagem: <<<python|go|rust|typescript|java>>>
- Ponto de Entrada: <<<CLI|API HTTP|Worker|Consumer>>>
- Integrações Externas: <<<LISTA_DE_INTEGRACOES>>>

CONTRATO ARQUITETURAL:
1. Camadas: domain (puro), application (use cases e ports), infrastructure (adapters e settings), presentation (composition root e entrypoint).
2. O domínio e a aplicação nunca conhecem infraestrutura ou frameworks.
3. Zero comentários no código de aplicação; tipagem estrita e nomes autoexplicativos.
4. Cobertura de testes de 100% com branch coverage obrigatória.
5. Validação unificada em 5 estágios: Lint, Security, Test, Validate, Build.
6. Logging semântico sem ruído e sem vazamento de dados sensíveis.
7. Harness universal para agentes em .agents/ e documentação técnica em docs/.

Entregue: estrutura de diretórios, contratos de portas, entidades de domínio com TDD, adaptadores de infraestrutura, orquestração de testes e documentação correspondente.
```
