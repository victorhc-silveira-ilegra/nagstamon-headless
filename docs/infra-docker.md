# Engenharia de Infraestrutura e Contêineres

Especificações técnicas de empacotamento, orquestração e execução do **Nagstamon Headless** em contêineres Docker.

## 1. Topologia de Execução e Rede

O contêiner do Nagstamon Headless opera intencionalmente em modo de rede do host (`network_mode: host`):

- **Roteamento Corporativo Transparente**: Permite ao daemon utilizar diretamente os túneis de VPN ativos na estação de trabalho (`fctvpn*`, `tun*`, `wireguard`), sem necessidade de configurar clientes VPN ou certificados adicionais no interior do contêiner.
- **Resolução de Proxy e DNS Interno**: O daemon herda a tabela de rotas do sistema hospedeiro, garantindo alcance aos proxies HTTP corporativos e serviços em faixas privadas (RFC 1918) sem NAT duplicado.
- **Princípio do Menor Privilégio**: O contêiner não executa como `root`. A imagem final opera com usuário não-privilegiado dedicado, garantindo conformidade com padrões de segurança em tempo de execução.

## 2. Estrutura de Volumes e Persistência

O arquivo de composição `infra/docker/docker-compose.yml` mapeia 3 pontos essenciais de persistência:

| Volume no Host | Ponto de Montagem no Contêiner | Permissão | Finalidade |
| :--- | :--- | :--- | :--- |
| `${HOST_SERVERS_DIR:-~/.nagstamon/servers}` | `/etc/nagstamon/servers` | Somente Leitura (`ro`) | Ingestão das configurações de servidores `.conf` |
| `data/` | `/var/lib/nagstamon-headless` | Leitura e Escrita (`rw`) | Persistência do ledger JSON de deduplicação |
| `logs/` | `/var/log/nagstamon-headless` | Leitura e Escrita (`rw`) | Gravação em tempo real do arquivo diário `nagstamon-YYYY-MM-DD.log` |

*Nota de Áudio*: Em contêiner Docker, a variável `SOUND_ENABLED` é forçada para `false`, uma vez que servidores e contêineres headless não contam com dispositivo físico de saída de áudio PulseAudio/ALSA.

## 3. Especificação do Dockerfile Multi-Stage

A compilação do contêiner adota padrão multi-stage (`infra/docker/Dockerfile`):
1. **Stage de Build (`builder`)**: Base Python 3.11 Slim instalando ferramentas de compilação, compilando dependências C (`wheel`) e instalando o pacote Python em diretório isolado.
2. **Stage Final (`runtime`)**: Imagem limpa contendo apenas o runtime essencial do Python e as dependências compiladas transferidas do builder. Todos os compiladores, cabeçalhos de desenvolvimento e arquivos transitórios são excluídos da imagem final.

## 4. Comandos e Ciclo de Vida Operacional

```bash
# Inicialização do serviço em segundo plano
make docker-up

# Teste smoke funcional de ponta a ponta
make docker-smoke

# Visualização de logs consolidados em tempo real
make docker-logs

# Exibição do status do contêiner
make docker-ps

# Parada e desmontagem do serviço
make docker-down
```

### Protocolo do Teste Smoke (`smoke.sh`)

O comando `make docker-smoke` executa validação rigorosa de ponta a ponta:
1. Verifica se a interface de VPN configurada está ativa no host.
2. Valida se a rota até o proxy corporativo está estabelecida.
3. Inicia um contêiner efêmero com limite de um ciclo (`--max-cycles 1`).
4. Assegura que o ciclo conclui com sucesso (`poll.cycle.finished`), confirmando conectividade contra os servidores reais sem quebras de execução.
