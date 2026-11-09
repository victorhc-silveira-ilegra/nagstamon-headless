# Código-Fonte (app/src)

Estrutura de código do sistema organizada segundo os princípios da Arquitetura Hexagonal (Ports & Adapters) e Domain-Driven Design (DDD).

## Camadas

1. [domain/](domain/): Camada mais interna e pura do sistema. Contém entidades de domínio (`Alert`, `ServerConfig`), value objects e domain services (`alert_view.py`). Não possui dependências externas ou de infraestrutura.
2. [application/](application/): Casos de uso (`collect_alerts.py`, `ping_servers.py`) e contratos de interface/portas (`ports/`). Depende exclusivamente de `domain`.
3. [infrastructure/](infrastructure/): Implementação concreta das portas (adaptadores HTTP para Alertmanager e Nagios CGI, publicadores de alerta, persistência em arquivo de ledger e configurações de runtime).
4. [presentation/](presentation/): Pontos de entrada executáveis (CLI de ping, worker de background para polling contínuo e composition root para injeção de dependências).

Para mais detalhes teóricos e diagramas, consulte [docs/arquitetura.md](../../docs/arquitetura.md).
