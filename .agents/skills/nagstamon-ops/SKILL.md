---
name: nagstamon-ops
description: Procedimentos de diagnóstico operacional, conectividade de rede, containerização e inspeção de logs
---

# Skill: Nagstamon Ops

Esta habilidade orienta a execução operacional de rotinas de diagnóstico de rede, verificação de conectividade contra servidores de monitoramento, execução em contêiner Docker e monitoramento de logs.

## Testes de Conectividade e Ping

Para validar se os endpoints de monitoramento (Alertmanager e Nagios) estão alcançáveis através da rede atual ou túnel corporativo VPN:

```bash
# Executa ping em todos os servidores configurados no diretório SERVERS_DIR
make app-ping
```

### Interpretação dos Resultados do Ping

- **HTTP 200/302**: Monitor ativo e acessível.
- **HTTP 401**: Credenciais ausentes ou inválidas no arquivo de configuração do monitor.
- **HTTP 502 / 503**: Serviço no alvo indisponível ou proxy com erro de upstream.
- **ReadTimeout / ConnectTimeout**: Endpoint inalcançável (VPN desconectada, rota de rede ausente ou regra de firewall bloqueando tráfego).

## Operações com Docker

O serviço headless é empacotado para execução em contêiner utilizando a rede do host (`--network host`) para herdar o roteamento de VPN local da estação:

```bash
# Build e inicialização em segundo plano
make docker-up

# Teste smoke de inicialização e saúde do contêiner
make docker-smoke

# Visualização de logs consolidados do contêiner
make docker-logs

# Parada e remoção do contêiner
make docker-down
```

## Inspeção e Higienização de Logs

1. **Localização**: Os logs da aplicação são gravados no diretório configurado por `LOG_DIR` (padrão `logs/`), utilizando rotação diária no formato `nagstamon-YYYY-MM-DD.log`.
2. **Visualização Direta**:
   ```bash
   tail -f logs/nagstamon-$(date +%Y-%m-%d).log
   ```
3. **Limpeza Automática**:
   O comando `make app-clean` remove artefatos temporários de compilação, caches de teste e logs diários de datas anteriores ao dia corrente, preservando o arquivo do dia de hoje para auditoria.
