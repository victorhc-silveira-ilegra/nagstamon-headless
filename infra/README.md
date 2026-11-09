# Infraestrutura

Diretório dedicado aos artefatos de empacotamento, orquestração e execução do Nagstamon Headless em ambientes conteinerizados ou provisionados.

## Módulos

- [docker/](docker/): Dockerfile multi-stage em conformidade com as melhores práticas de segurança (usuário não-root, distroless/slim, dependências compiladas em stage isolado) e scripts de ciclo de vida do contêiner.

Para detalhes completos de operação e comandos, consulte [docs/infra-docker.md](../docs/infra-docker.md).
