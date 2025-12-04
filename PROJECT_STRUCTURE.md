# Estrutura do Projeto - Traders

## Visão Geral

Este documento descreve a organização completa do projeto Autonomous Traders

## Estrutura de Diretórios

```
traders/
├── .gitignore              # Arquivos ignorados pelo Git
├── .env.example            # Exemplo de variáveis de ambiente
├── README.md               # Documentação principal
├── SETUP.md                # Instruções de configuração
├── PROJECT_STRUCTURE.md    # Este arquivo
├── requirements.txt        # Dependências Python
├── start_ui.sh             # Script para iniciar UI
├── start_trading_floor.sh  # Script para iniciar trading floor
│
├── config/                 # Arquivos de configuração
│   └── .env.example        # Exemplo de variáveis de ambiente (backup)
│
├── data/                   # Dados persistentes (não versionado)
│   ├── .gitkeep           # Garante que a pasta seja rastreada
│   ├── accounts.db        # Banco de dados SQLite (criado automaticamente)
│   └── memory/            # Banco de dados de memória (criado automaticamente)
│
├── docs/                   # Documentação adicional
│   └── (documentação futura)
│
└── src/                    # Código fonte
    ├── __init__.py
    │
    ├── core/               # Lógica de negócios e servidores MCP
    │   ├── __init__.py
    │   ├── accounts.py              # Classe Account (lógica de contas)
    │   ├── accounts_server.py       # Servidor MCP de contas
    │   ├── accounts_client.py       # Cliente MCP de contas
    │   ├── database.py              # Persistência SQLite
    │   ├── market.py                # Obtenção de preços de ações
    │   ├── market_server.py         # Servidor MCP de mercado
    │   └── push_server.py           # Servidor MCP de notificações
    │
    ├── agents/             # Agentes traders e orquestração
    │   ├── __init__.py
    │   ├── traders.py              # Classe Trader
    │   ├── trading_floor.py        # Loop principal de execução
    │   └── reset.py                # Inicialização de estratégias
    │
    ├── ui/                 # Interface de usuário
    │   ├── __init__.py
    │   ├── app.py                  # Aplicação Gradio principal
    │   └── util.py                 # Utilitários UI (CSS, JS, cores)
    │
    └── utils/              # Utilitários e configurações
        ├── __init__.py
        ├── tracers.py              # Sistema de tracing customizado
        ├── templates.py            # Templates de prompts
        └── mcp_params.py           # Configuração de servidores MCP
```

## Descrição dos Módulos

### `src/core/`

**Lógica de negócios e servidores MCP**

- **`accounts.py`**: Implementa a classe `Account` com toda a lógica de gerenciamento de contas (saldo, holdings, transações, P&L)
- **`accounts_server.py`**: Servidor MCP que expõe funcionalidades de contas como ferramentas e recursos
- **`accounts_client.py`**: Cliente MCP para interagir com o accounts_server
- **`database.py`**: Funções para persistência em SQLite (contas, logs, dados de mercado)
- **`market.py`**: Funções para obter preços de ações via Polygon API (com cache)
- **`market_server.py`**: Servidor MCP que expõe funcionalidades de mercado
- **`push_server.py`**: Servidor MCP para envio de notificações push

### `src/agents/`

**Agentes traders e orquestração**

- **`traders.py`**: Classe `Trader` que encapsula um trader autônomo com seu agente, modelo e lógica de execução
- **`trading_floor.py`**: Loop principal que orquestra a execução de todos os traders periodicamente
- **`reset.py`**: Define estratégias iniciais e função para resetar traders

### `src/ui/`

**Interface de usuário Gradio**

- **`app.py`**: Aplicação Gradio principal com 4 colunas (uma para cada trader), gráficos, logs e tabelas
- **`util.py`**: Utilitários de UI (CSS customizado, JavaScript, enum de cores)

### `src/utils/`

**Utilitários e configurações**

- **`tracers.py`**: Sistema de tracing customizado (`LogTracer`) que captura eventos e salva no banco
- **`templates.py`**: Templates de prompts para Researcher e Trader agents
- **`mcp_params.py`**: Configuração de todos os servidores MCP (trader e researcher), incluindo configuração automática do PYTHONPATH para permitir imports dos módulos `src`

## Fluxo de Dados

```
Trading Floor (trading_floor.py)
    │
    ├──► Cria 4 Traders (traders.py)
    │       │
    │       ├──► Conecta a servidores MCP (mcp_params.py)
    │       │       ├──► Accounts Server (accounts_server.py)
    │       │       ├──► Push Server (push_server.py)
    │       │       └──► Market Server (market_server.py)
    │       │
    │       ├──► Cria Researcher Agent (templates.py)
    │       │       └──► Conecta a servidores MCP
    │       │               ├──► Fetch Server
    │       │               ├──► Brave Search Server
    │       │               └──► Memory Server
    │       │
    │       └──► Executa Trader Agent
    │               ├──► Lê conta e estratégia (accounts_client.py)
    │               ├──► Chama Researcher tool
    │               ├──► Executa trades (via accounts_server.py)
    │               └──► Salva logs (database.py)
    │
    └──► LogTracer captura eventos (tracers.py)
            └──► Salva no banco (database.py)
                    └──► UI lê e exibe (app.py)
```

## Arquivos de Configuração

### `.env`

Variáveis de ambiente necessárias (copiar de `.env.example`):

- **Obrigatórias**: `OPENAI_API_KEY`, `BRAVE_API_KEY`
- **Opcionais**: `POLYGON_API_KEY`, `USE_MANY_MODELS`, etc.

### `requirements.txt`

Dependências Python do projeto.

## Scripts de Execução

### `start_ui.sh`

Inicia a interface Gradio:
```bash
./start_ui.sh
# ou
python -m src.ui.app
```

### `start_trading_floor.sh`

Inicia o loop principal de trading:
```bash
./start_trading_floor.sh
# ou
python -m src.agents.trading_floor
```

## Dados Persistentes

### `data/accounts.db`

Banco de dados SQLite contendo:
- Tabela `accounts`: Dados das contas dos traders
- Tabela `logs`: Logs de tracing
- Tabela `market`: Cache de dados de mercado

### `data/memory/`

Bancos de dados libSQL (um por trader) para memória persistente dos pesquisadores.

## Notas Importantes

1. **Imports**: Todos os imports usam caminhos relativos a partir de `src/` (ex: `from src.core.accounts import Account`)

2. **Execução**: Sempre execute a partir da raiz do projeto `traders/`:
   ```bash
   cd traders
   python -m src.ui.app
   ```

3. **Servidores MCP**: 
   - Os caminhos dos servidores são configurados em `mcp_params.py` usando caminhos absolutos
   - O `PYTHONPATH` é configurado automaticamente para cada servidor MCP Python local, permitindo imports `from src.core...`
   - Isso resolve problemas de `ModuleNotFoundError` quando os servidores são executados via `uv run`
   - Servidores externos (Fetch, Brave Search, Memory) não precisam de PYTHONPATH pois são executados via `uvx` ou `npx`

4. **Banco de Dados**: O banco é criado automaticamente na primeira execução.

5. **Memória**: Os bancos de memória são criados automaticamente quando os traders são executados.

## Detalhes Técnicos

### Configuração de Servidores MCP

O arquivo `mcp_params.py` gerencia a configuração de todos os servidores MCP:

1. **Cálculo do PYTHONPATH**: 
   - Calcula automaticamente o diretório raiz do projeto
   - Cria variável de ambiente `PYTHONPATH` com o caminho do projeto
   - Preserva PYTHONPATH existente se houver

2. **Servidores Python Locais**:
   - `accounts_server.py`, `push_server.py`, `market_server.py`
   - Recebem `PYTHONPATH` no ambiente para permitir imports `from src.core...`
   - Executados via `uv run` com caminhos absolutos

3. **Servidores Externos**:
   - Fetch Server: `uvx mcp-server-fetch` (não precisa PYTHONPATH)
   - Brave Search: `npx @modelcontextprotocol/server-brave-search` (Node.js)
   - Memory Server: `npx mcp-memory-libsql` (Node.js)

4. **Polygon Market Server**:
   - Se `POLYGON_PLAN=paid` ou `realtime`: usa servidor externo via `uvx`
   - Se `POLYGON_PLAN=free`: usa servidor local `market_server.py` com PYTHONPATH

## Próximos Passos

1. Adicionar testes unitários
2. Adicionar documentação de API
3. Melhorar tratamento de erros
4. Adicionar logging estruturado
5. Adicionar métricas e monitoramento

