# Testes Unitários - Autonomous Traders

Este diretório contém os testes unitários para o projeto Autonomous Traders.

## Estrutura

```
tests/
├── __init__.py           # Inicialização do pacote de testes
├── conftest.py           # Fixtures compartilhadas e configuração
├── test_accounts.py      # Testes para src/core/accounts.py
├── test_database.py      # Testes para src/core/database.py
├── test_market.py        # Testes para src/core/market.py
├── test_tracers.py       # Testes para src/utils/tracers.py
└── test_traders.py       # Testes para src/agents/traders.py
```

## Instalação

Instale as dependências de teste:

```bash
uv pip install -r requirements.txt
```

Ou apenas as dependências de teste:

```bash
uv pip install pytest pytest-asyncio pytest-cov
```

## Executando os Testes

### Executar todos os testes

```bash
# A partir da raiz do projeto
pytest

# Ou com mais detalhes
pytest -v

# Ou com output ainda mais detalhado
pytest -vv
```

### Executar testes específicos

```bash
# Testes de um arquivo específico
pytest tests/test_accounts.py

# Testes de uma classe específica
pytest tests/test_accounts.py::TestAccount

# Testes de um método específico
pytest tests/test_accounts.py::TestAccount::test_account_deposit
```

### Executar com cobertura

```bash
# Gera relatório de cobertura
pytest --cov=src --cov-report=html

# Abre o relatório no navegador (Linux)
xdg-open htmlcov/index.html

# Ou apenas mostra no terminal
pytest --cov=src --cov-report=term
```

### Executar testes assíncronos

Os testes assíncronos são executados automaticamente com `pytest-asyncio`. Certifique-se de que os métodos de teste assíncronos estão marcados com `@pytest.mark.asyncio`.

## Fixtures Disponíveis

As fixtures em `conftest.py` estão disponíveis para todos os testes:

- `temp_db`: Cria um banco de dados SQLite temporário
- `mock_database_module`: Mock do módulo database.py
- `mock_get_share_price`: Mock da função get_share_price
- `sample_account_data`: Dados de exemplo para contas
- `mock_polygon_api`: Mock da API Polygon
- `mock_env_vars`: Mock de variáveis de ambiente

## Estrutura dos Testes

Cada arquivo de teste segue a estrutura:

```python
class TestClassName:
    """Testes para a classe/função X."""
    
    def test_method_name(self):
        """Testa comportamento específico."""
        # Arrange
        # Act
        # Assert
```

## Mocks e Stubs

Os testes usam `unittest.mock` para:

- **Mockar APIs externas**: Polygon API, OpenAI API
- **Mockar banco de dados**: Usa banco temporário para isolamento
- **Mockar dependências**: Evita chamadas reais a serviços externos

## Cobertura de Testes

Os testes cobrem:

- ✅ `src/core/accounts.py`: Account, Transaction
- ✅ `src/core/database.py`: Funções de persistência
- ✅ `src/core/market.py`: Obtenção de preços (com mocks)
- ✅ `src/utils/tracers.py`: Sistema de tracing
- ✅ `src/agents/traders.py`: Classe Trader

## Adicionando Novos Testes

1. Crie um novo arquivo `test_<module>.py` no diretório `tests/`
2. Importe os módulos necessários
3. Use as fixtures disponíveis em `conftest.py`
4. Siga o padrão de nomenclatura: `test_<functionality>`
5. Execute `pytest` para verificar

## Troubleshooting

### Erro: "ModuleNotFoundError"

Certifique-se de executar os testes a partir da raiz do projeto:

```bash
cd /home/francisco/projects/agents/6_mcp/traders
pytest
```

### Erro: "asyncio is not defined"

Certifique-se de que `pytest-asyncio` está instalado:

```bash
uv pip install pytest-asyncio
```

### Testes falhando por dependências externas

Os testes devem usar mocks para todas as dependências externas. Se um teste está fazendo chamadas reais à API, verifique se os mocks estão configurados corretamente.

## Integração Contínua

Para usar em CI/CD, adicione ao seu workflow:

```yaml
- name: Run tests
  run: |
    uv pip install -r requirements.txt
    pytest --cov=src --cov-report=xml
```

