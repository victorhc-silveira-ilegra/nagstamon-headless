# Scripts Operacionais e de Automação

Este diretório armazena scripts auxiliares de inicialização, configuração de ambiente e ferramentas de quality gate do repositório.

## Estrutura

- [operations/](operations/): Contém o runner central de qualidade (`clean_workspace.py`) e os validadores especializados de cada área (`gates/`).
- `setup.sh`: Script de inicialização e verificação de pré-requisitos locais.

Para documentação sobre os quality gates e execução de testes contínuos, consulte [docs/devops.md](../../docs/devops.md).
