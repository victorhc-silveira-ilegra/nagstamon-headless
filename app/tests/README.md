# Suíte de Testes (app/tests)

Suíte de testes automatizados do Nagstamon Headless, mantendo meta estrita de 100% de cobertura com verificação de desvios (`branch coverage`).

## Estrutura

- [unit/](unit/): Testes unitários rápidos e isolados por camada (`domain`, `application`, `infrastructure`, `presentation`).
- [integration/](integration/): Testes de integração para adaptadores que realizam I/O e comunicação de rede.

## Execução

```bash
# Executa a suíte completa com medição de cobertura
make app-test
```

Para a política de qualidade e testes contínuos, consulte [.agents/rules/code-quality-testing.md](../../.agents/rules/code-quality-testing.md).
