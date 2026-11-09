# Testes de Integração

Este diretório contém os testes de integração do sistema, responsáveis por validar o comportamento dos adaptadores de infraestrutura e serviços de borda com dependências reais ou emuladas (ex.: transporte HTTP emulado com respostas reais de Alertmanager e Nagios CGI).

## Estrutura

- [infrastructure/](infrastructure/): Testes de integração dos adaptadores de infraestrutura (`HttpMonitorGateway`, `GChatNotifier`, `JsonFileLedger`, etc.).

Para a suíte de testes unitários rápidos, consulte [app/tests/unit/](../unit/).
Para a política completa de testes e cobertura 100%, consulte [.agents/rules/code-quality-testing.md](../../../.agents/rules/code-quality-testing.md).
