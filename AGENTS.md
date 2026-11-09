# AGENTS.md

Projeto: Nagstamon Headless (DDD / Arquitetura Hexagonal) — polling de Alertmanager e Nagios CGI com filtros de alertas efetivos, carência SLA e publicação em múltiplos canais.

## Governança do Repositório

Todas as IAs, agentes autônomos e desenvolvedores devem seguir estritamente as regras de arquitetura, qualidade e convenções estabelecidas em `.agents/rules/` e documentadas em `docs/`.

### Prioridades Absolutas

1. **Arquitetura Hexagonal Estrita**: O código reside em `app/src/` dividido exclusivamente em `domain`, `application`, `infrastructure` e `presentation`. A regra de dependência flui apenas para dentro (detalhes dependem de abstrações; o domínio é isolado e puro).
2. **Qualidade e Cobertura 100%**: Toda modificação de código deve ser acompanhada de testes unitários e de integração em `app/tests/`, mantendo 100% de cobertura de desvios (`branch coverage`). Nenhuma regressão é tolerada.
3. **Ausência de Comentários no Código**: Não escrever comentários explicativos nem docstrings desnecessárias nos arquivos Python (`app/src/` e `app/tests/`). O código deve ser autoexplicativo por meio de nomes semânticos, funções coesas e tipagem rigorosa (`mypy --strict`).
4. **Conventional Commits em Português**: Todo commit deve aderir estritamente ao padrão de Conventional Commits, escrito em português brasileiro (ex.: `feat: ...`, `fix: ...`, `refactor: ...`, `test: ...`, `docs: ...`).
5. **Configuração Unificada via Ambiente**: Parâmetros de execução são injetados exclusivamente via variáveis de ambiente carregadas de `.env` pela infraestrutura (`Settings`). Credenciais reais e URLs de webhook pertencem apenas ao `.env` local e nunca são versionadas.
6. **Sincronização de Documentação**: Qualquer alteração arquitetural, contratual ou comportamental deve ser imediatamente refletida na documentação correspondente em `docs/`.
7. **Observabilidade e Logs Semânticos**:
   - `INFO`: Apenas eventos operacionais chave (inicialização, primeiro ciclo, sumário de ciclo com alertas encontrados, publicação com sucesso).
   - `WARNING`: Falhas parciais que admitem continuidade (fail-open de servidor, timeouts tolerados, descarte por validação).
   - `ERROR`: Falhas críticas que impedem o ciclo de execução ou quebram a integridade do processo.
   - O domínio e a aplicação não realizam chamadas de logging nem acessam bibliotecas de infraestrutura. Ciclos ociosos não devem emitir logs de início/fim ruidosos.
   - Logs são gravados em stdout e em arquivo diário gerenciado em `LOG_DIR` (`logs/nagstamon-YYYY-MM-DD.log`).
8. **Paridade Canônica de Snapshots**: O texto emitido no terminal (`stdout`) e a mensagem transmitida via webhook do Google Chat compartilham rigorosamente a mesma formatação em texto puro definida em `domain/services/alert_view.py`. Deduplicação persistente via ledger transacional (`claim` -> `confirm` -> `release`) utilizando fingerprint SHA-256 (`server`/`alertname`/`app`/`host`).
9. **Filtros Temporais e Carência SLA**:
   - Resolução de data/hora exclusivamente em Python sobre `starts_at` ou parse de `duration_str`.
   - Janela comercial controlada por `WINDOW_*` (`WINDOW_ALLOW_PAST_ACTIVE_ALERTS=true` padrão para capturar incidentes ativos pré-existentes ao boot).
   - Carência de hold-down por criticidade/severidade: Muito Crítico = 10 min (`FILTER_HOLD_FAST_SECONDS`), Mediano/Crítico = 15 min (`FILTER_HOLD_CRITICAL_SECONDS`), Baixo/Warning = 20 min (`FILTER_HOLD_WARNING_SECONDS`). Alertas com severidade `info` ou com instante de início indeterminado são sumariamente descartados.

## Comandos Operacionais

```bash
# Instalação de dependências em ambiente virtual
make app-install

# Quality gates de código e segurança
make app-lint
make app-security
make app-test

# Diagnóstico de conectividade contra os servidores monitorados
make app-ping

# Ciclo de vida Docker
make docker-up
make docker-smoke
make docker-logs
make docker-down
```

## Regras e Habilidades Detalhadas

- Regras arquiteturais e governança: `.agents/rules/`
- Habilidades operacionais especializadas: `.agents/skills/`
- Manual de arquitetura do sistema: `docs/arquitetura.md`
- Estrutura completa de diretórios: `docs/structure.md`
- Padrões de desenvolvimento em Python: `docs/engineering-python.md`
- Padrões de logging e observabilidade: `docs/engineering-logging.md`
- Engenharia de contêineres: `docs/infra-docker.md`
- Matriz de CI/CD e automação: `docs/devops.md`

## Escopo e Limitações

- Não utilizar nem portar a interface gráfica desktop Qt do Nagstamon original.
- Não implementar drivers para sistemas de monitoramento além de Alertmanager e Nagios CGI.
- Não rotear alertas para ferramentas de ticketing além dos canais canônicos homologados (stdout e Google Chat).
