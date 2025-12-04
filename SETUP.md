# Setup Instructions

## Estrutura de Diretórios

O projeto está organizado da seguinte forma:

```
traders/
├── src/
│   ├── core/           # Servidores MCP e lógica de negócios
│   ├── agents/         # Agentes traders
│   ├── ui/             # Interface Gradio
│   └── utils/          # Utilitários
├── config/             # Configurações
├── data/               # Dados persistentes
└── docs/               # Documentação
```

## Configuração do Ambiente

### 1. Variáveis de Ambiente

Copie `config/.env.example` para `.env` na raiz do projeto `traders/`:

```bash
cp config/.env.example .env
```

Edite `.env` com suas chaves de API.

### 2. PYTHONPATH

Para que os imports funcionem corretamente, você precisa executar a partir da raiz do projeto `traders/`:

```bash
cd traders
python -m src.ui.app
```

Ou configure o PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### 3. Servidores MCP

Os servidores MCP são executados via `uv run` com caminhos absolutos configurados em `src/utils/mcp_params.py`.

**Nota**: Os servidores precisam ser executados a partir do diretório do projeto para que os caminhos relativos funcionem corretamente.

## Executando o Projeto

### Opção 1: Usando Scripts

```bash
# UI
./start_ui.sh

# Trading Floor
./start_trading_floor.sh
```

### Opção 2: Usando Python diretamente

```bash
# UI
python -m src.ui.app

# Trading Floor
python -m src.agents.trading_floor

# Reset traders
python -m src.agents.reset
```

## Estrutura de Dados

- **Banco de dados**: `data/accounts.db` (criado automaticamente)
- **Memória**: `data/memory/` (criado automaticamente)
- **Logs**: Armazenados no banco de dados

## Troubleshooting

### Erro: "ModuleNotFoundError"

Certifique-se de executar a partir da raiz do projeto `traders/`:

```bash
cd traders
python -m src.ui.app
```

### Erro: Servidores MCP não iniciam

Verifique se:
1. Node.js está instalado (`node --version`)
2. `npx` está disponível (`npx --version`)
3. Você está executando a partir do diretório correto

### Erro: Banco de dados não encontrado

O banco será criado automaticamente na primeira execução. Certifique-se de que o diretório `data/` existe e tem permissões de escrita.

