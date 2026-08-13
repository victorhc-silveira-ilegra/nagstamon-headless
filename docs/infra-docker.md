# Infra Docker

Stack minima para rodar o daemon headless. Nao inclui monitores (Alertmanager/Nagios): eles sao alcancados via rede do host e proxy.

## Servico

- Imagem: Python 3.11, pacote `nagstamon-headless`
- `network_mode: host` para usar o proxy e rotas locais
- Volume somente leitura: `${HOST_SERVERS_DIR:-~/.nagstamon/servers}` → `/etc/nagstamon/servers`
- `SERVERS_DIR=/etc/nagstamon/servers` dentro do container

## Comandos

```bash
cp .env.example .env
make docker-up
make docker-logs
make docker-ps
make docker-down
```

O IP/URL do proxy vai em `PROXY_ADDR` no `.env` local, nunca no compose versionado.

## Arquivos

- [`infra/docker/Dockerfile`](../infra/docker/Dockerfile)
- [`infra/docker/docker-compose.yml`](../infra/docker/docker-compose.yml)
