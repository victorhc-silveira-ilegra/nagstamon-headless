# Prompt-modelo de engenharia

Contrato reutilizavel derivado deste repositorio (Nagstamon Headless). Use este arquivo para orientar um agente a gerar ou adaptar qualquer projeto (Python ou outra linguagem) com o mesmo padrao de engenharia: DDD, hexagonal, TDD, qualidade, DX e documentacao.

Dominio Alertmanager / Nagios CGI e exemplo de referencia, nao regra obrigatoria do novo projeto.

## 1. Papel e objetivo

Voce e um engenheiro senior. Ao receber um novo dominio de negocio e (opcionalmente) uma linguagem, deve:

- Projetar e implementar a solucao no padrao deste contrato.
- Adaptar ferramentas e pastas a linguagem escolhida sem abandonar os invariantes.
- Manter docs, Makefile, hooks e gates alinhados ao codigo.
- Preferir TDD: testes primeiro nas camadas de dominio e application; integracao nos adapters de IO.

Objetivo final: o novo repositorio deve “parecer” este projeto em arquitetura, qualidade e operacao — nao copiar o negocio de monitoramento.

## 2. Contrato invariavel (language-agnostic)

### Camadas (hexagonal / DDD)

| Camada | Conteudo | Pode depender de |
|--------|----------|------------------|
| domain | Entidades, value objects, domain services, validacoes | Ninguem de fora do dominio |
| application | Use cases + ports (contratos) | domain |
| infrastructure | Adapters (HTTP, DB, filas), config, logging de borda | application, domain |
| presentation | CLI/API/UI/worker + composition root | application, domain, infrastructure |

Regras:

- domain e application nao importam infrastructure nem presentation.
- Ports sao contratos (Protocol / interface / trait). Adapters implementam ports na infrastructure.
- Validacao de entidades fica no dominio.
- Politica de filtros de negocio (hold-down por criticidade, ack, janela horaria e dias uteis, inicio apos o boot do processo) vive no dominio, e calculada em codigo (datetime), e injetada pelo composition root; dominio nao loga.
- Formatacao de payload / regras de saida ficam no dominio ou application — nao na CLI/controller.
- Snapshot operacional de alertas (Client, Host, Service, Status, Duration, Started, Status information) e formatado no dominio.
- Sink operacional pode ter canal extra (ex.: webhook de mensagem de texto, nao card estruturado); despacho idempotente por problema via ledger (claim/confirm/release), sem segredo no git.
- Domain e use case nao emitem logs. Logging semantico fica na presentation e/ou adapters.
- Composition root (wiring Settings → adapters → use case) fica na presentation.

### Qualidade e estilo

- Sem comentarios no codigo de aplicacao (codigo autodescritivo).
- Documentacao tecnica em PT-BR; sem emojis em codigo, logs ou docs.
- Conventional Commits.
- Config via `.env` na raiz + `.env.example`; nunca commitar segredos.
- Cobertura alta nas camadas de app (neste repo: 100% com branch coverage em domain, application, infrastructure, presentation).
- Limite de tamanho por arquivo de codigo (~300 linhas); extrair quando passar.
- Type checking estrito quando a linguagem permitir.

### Testes (TDD)

- Unitarios por camada: `tests/unit/{domain,application,infrastructure,presentation}`.
- Integracao para adapters de IO (HTTP mock transport, DB fake/testcontainer, etc.).
- Application: preferir fakes dos ports.
- Isolar testes do `.env` local (flag/env do tipo `*_DISABLE_DOTENV`).

## 3. Arquitetura de pastas (template)

Ajuste nomes de entrypoint/build file a linguagem; preserve a intencao das pastas.

```text
.
├── app/
│   ├── src/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── presentation/
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── scripts/
│   │   ├── setup.sh
│   │   └── operations/
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── requirements-dev.txt
├── docs/
├── infra/
├── linters/
├── Makefile
├── AGENTS.md
├── prompt-model.md
├── README.md
├── .env.example
└── run.py
```

Imports da aplicacao devem ser limpos (sem prefixo desnecessario tipo `app.src`): `from domain...`, `from application...`.

## 4. Qualidade e DX

Gates conceituais obrigatorios: lint/format, type check, dead code, test+coverage, security, hooks (pre-commit + commit-msg), Make (`app-install`, `app-lint`, `app-test`, `app-security`, `app-clean`, `app-setup`).

Orquestrador central (`app/scripts/operations/clean_workspace.py`) deve ser o unico ponto chamado pelo Makefile para lint/test/security/clean.

Para Python novo: preserve o stack deste projeto (Ruff, mypy strict, vulture, pytest-cov 100%, bandit, pip-audit, pre-commit, commitlint, Makefile).

## 5. Logging semantico

- API unica do tipo `log_event(logger, level, event, **fields)`.
- Eventos nomeados e estaveis: `<contexto>.run.started|finished|failed`, `<contexto>.*.skipped_*`, `<contexto>.*.sent|failed`.
- Caminho feliz: ~3 linhas INFO.
- Sem dump de payload JSON nem body HTTP em INFO.
- Redact de URLs/segredos (query string → `?***`); campo logado como host/redacted, nunca secret cru.
- `exc_info` / stack apenas em DEBUG nas falhas.
- Silenciar loggers ruidosos de HTTP clients em WARNING+.

Detalhes: [docs/engineering-logging.md](docs/engineering-logging.md).

## 6. Documentacao obrigatoria

Manter alinhada ao codigo: `docs/arquitetura.md`, `docs/structure.md`, `docs/engineering-<lang>.md`, `docs/engineering-logging.md`, `AGENTS.md`, `README.md`, `.env.example`.

## 7. Protocolo de adaptacao (checklist do agente)

1. Ler o dominio/requisitos do novo projeto e a linguagem alvo.
2. Listar entidades, use cases, ports e adapters necessarios.
3. Criar a arvore de pastas e impor regras de dependencia.
4. Configurar build, `.env.example`, Makefile e orquestrador de qualidade.
5. Instalar hooks (pre-commit + Conventional Commits).
6. Implementar em TDD: domain → application (fakes) → adapters → presentation.
7. Adicionar `infra/` somente se o contexto exigir runtime local.
8. Escrever/atualizar docs listadas na secao 6 e `AGENTS.md`.
9. Rodar `make app-lint`, `make app-test`, `make app-security` ate verde.
10. Garantir commits Conventional Commits e ausencia de segredos.

## 8. Anti-padroes

- HTTP client, SQL ou framework web dentro de domain / application.
- Comentarios no codigo de aplicacao.
- Logs dentro de use case ou entidade.
- Composition root espalhado ou fora de presentation.
- Cobertura “quase” o suficiente; baixar fail-under sem decisao explicita.
- Commits fora de Conventional Commits.
- Docs desatualizadas apos mudanca de arquitetura.
- Commitar `.env` ou tokens.
- Copiar stack Docker de outro dominio sem necessidade.

## 9. PROMPT PARA COLAR

Copie o bloco abaixo integralmente em um novo chat/projeto. Substitua apenas as linhas marcadas com `<<< >>>`.

```text
Voce e um engenheiro senior. Adapte ou crie o repositorio abaixo para ficar equivalente ao contrato de engenharia do projeto de referencia (DDD + hexagonal + TDD + DX forte).

NOVO PROJETO
- Nome: <<<NOME>>>
- Dominio / objetivo: <<<DESCRICAO DO NEGOCIO>>>
- Linguagem/runtime: <<<python|go|rust|ts|outra>>>
- Entrada principal: <<<CLI|API HTTP|worker|outro>>>
- Integracoes externas: <<<listar ou "nenhuma ainda">>>
- Infra local necessaria: <<<sim/nao; se sim, o minimo>>>

INVARIANTES (obrigatorios)
1. Camadas: domain, application (ports + use_cases), infrastructure (adapters/config/logging), presentation (composition root).
2. domain e application NAO importam infrastructure nem presentation.
3. Ports como contratos; adapters na infrastructure.
4. Validacao no dominio; formatacao de payload em domain/application, nao na borda de UI/CLI. Filtros de negocio (hold-down por criticidade, janela, dias uteis, boot) em codigo no dominio.
5. Domain e use case NAO logam; logging semantico na presentation/adapters (eventos *.started|finished|failed|skipped_*; sem dump de payload/segredos; redact de URLs; ~3 INFO no caminho feliz).
6. Sem comentarios no codigo; docs em PT-BR; sem emojis; Conventional Commits.
7. Config via .env na raiz + .env.example; nunca commitar segredos.
8. Testes TDD: unit por camada + integracao nos adapters de IO; fakes nos ports da application.
9. Cobertura alta nas camadas de app (meta 100% branch se a ferramenta permitir).
10. Gates via Makefile: install, lint, test, security, clean, setup; orquestrador unico em app/scripts/operations (ou equivalente).
11. Limite ~300 linhas por arquivo de codigo.
12. Type checking estrito quando a linguagem permitir.

PASTAS ALVO
app/src/{domain,application,infrastructure,presentation}
app/tests/{unit,integration}
app/scripts/operations/
docs/{arquitetura,structure,engineering-<lang>,engineering-logging}.md
linters/ (commitlint + git-hooks)
Makefile, AGENTS.md, README.md, .env.example, entrypoint na raiz
infra/ somente se necessario ao dominio

QUALIDADE
- Python: Ruff, mypy --strict, vulture, pytest+cov fail-under 100, bandit, pip-audit, pre-commit, commitlint.
- Outra linguagem: escolha equivalentes idiomaticos mantendo os MESMOS gates conceituais (lint, types, dead-code, test+coverage, security, hooks, conventional commits).

DOCS A MANTER ALINHADAS AO CODIGO
docs/arquitetura.md, docs/structure.md, docs/engineering-<lang>.md, docs/engineering-logging.md, AGENTS.md, README.md

PROTOCOLO
1) Mapear entidades/use cases/ports/adapters do dominio informado.
2) Criar arvore e regras de dependencia.
3) Configurar build, env, Makefile, hooks.
4) Implementar TDD (domain → application → adapters → presentation).
5) Nao copiar stack Docker de outro dominio a menos que o dominio peca algo equivalente.
6) Atualizar docs e AGENTS.md.
7) Rodar gates ate verde.

ANTI-PADROES
HTTP/DB no dominio; comentarios; logs no use case; composition root fora de presentation; commits nao convencionais; docs defasadas; segredos no git.

Entregue: estrutura, codigo, testes, Makefile, docs e AGENTS.md coerentes com este contrato.
```

## Referencia deste repositorio

Projeto que originou este contrato nesta pasta (exemplo de aplicacao do padrao, nao template de negocio):

- [AGENTS.md](AGENTS.md)
- [docs/arquitetura.md](docs/arquitetura.md)
- [docs/structure.md](docs/structure.md)
- [docs/engineering-python.md](docs/engineering-python.md)
- [docs/engineering-logging.md](docs/engineering-logging.md)
- [docs/infra-docker.md](docs/infra-docker.md)
