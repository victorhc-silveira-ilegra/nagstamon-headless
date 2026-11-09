# Regra de Engenharia: Qualidade, Testes e CI/CD

Esta regra padroniza as práticas de desenvolvimento orientado a testes (TDD), verificações estáticas, convenções de código e esteira de automação.

---

## 1. Test-Driven Development e Cobertura 100%

1. **Metodologia TDD**:
   - Para alterações em regras de filtragem (`alert_filter.py`), formatação (`alert_view.py`) ou carência (`alert_hold.py`), escreva primeiro os casos de teste que reproduzem o cenário desejado.
   - Aplique as mudanças no domínio até a suíte passar.
2. **Cobertura Estrita de 100% com Branch Coverage**:
   - As camadas `domain`, `application`, `infrastructure` e `presentation` exigem **100% de cobertura de linhas e ramos** (`branch = true`).
   - Nenhuma linha ou desvio condicional (`if/else`, `try/except`) pode ser adicionado sem teste unitário correspondente.
3. **Isolamento de Testes**:
   - A suíte de testes nunca deve depender de configurações reais ou arquivos locais do desenvolvedor (`.env`).
   - O arquivo `conftest.py` injeta automaticamente `NAGSTAMON_DISABLE_DOTENV=1`.
   - Adapters externos em testes unitários devem utilizar Fakes ou mocks controlados baseados em `httpx.MockTransport` / `unittest.mock`.

---

## 2. A Matriz de 5 Estágios

Tanto localmente (`pre-commit` e `Makefile`) quanto no GitHub Actions (`.github/workflows/ci.yml`), a validação de código executa estritamente nas 4 categorias (`python`, `docker`, `github`, `scripts`) os 5 estágios abaixo na ordem exata:

```text
1. Lint      -> Verificação de estilo, formatação e análise estática de tipos
2. Seguranca -> Varredura de vulnerabilidades (SAST), segredos e dependências
3. Testes    -> Execução de suítes de teste automatizadas com meta de cobertura
4. Validate  -> Validação estrutural de empacotamento, sintaxe e contratos
5. Build     -> Compilação de pacotes (wheels/sdist) ou imagens Docker
```

- **Orquestrador Único**: O comando `clean_workspace.py --area <area> --stage <stage>` é a única fonte de verdade para a execução dos estágios.

---

## 3. Padrão de Estilo e Nomenclatura

- **Linter & Formatador**: `Ruff` configurado com tamanho de linha de 88 caracteres, ordenação automática de imports (`isort`) e correções automáticas de convenções Python modernas.
- **Tipagem Estrita**: `mypy --strict` em todas as camadas de produção.
- **Detecção de Código Morto**: `vulture` com confiança mínima de 80%.
- **Zero Comentários**: Todo código em `app/src` deve ser autoexplicativo por sua semântica estrutural.
- **Tamanho Máximo de Arquivos**: Máximo de 300 linhas de código por arquivo.

---

## 4. Conventional Commits e Versionamento Semântico

- Todas as mensagens de commit devem seguir rigorosamente a especificação [Conventional Commits](https://www.conventionalcommits.org/):
  ```text
  feat(dominio): adiciona nova regra de deteccao de alerta
  fix(infra): corrige timeout no probe http
  refactor(application): simplifica orquestracao de ciclo de poll
  docs(arquitetura): atualiza diagrama de camadas
  test(domain): adiciona cobertura para caso de borda de horario
  ```
- O repositório utiliza **Semantic Release** automatizado na branch `main`. A criação de releases e tags no GitHub é gerada a partir dos tipos de commit.
