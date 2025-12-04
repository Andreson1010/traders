import os
from dotenv import load_dotenv
from src.core.market import is_paid_polygon, is_realtime_polygon

load_dotenv(override=True)

# Obtém o diretório raiz do projeto para configurar PYTHONPATH
import pathlib
project_root = pathlib.Path(__file__).parent.parent.parent
project_root_str = str(project_root)

# Configura PYTHONPATH para que os servidores MCP possam importar módulos 'src'
# Preserva PYTHONPATH existente se houver
existing_pythonpath = os.environ.get("PYTHONPATH", "")
if existing_pythonpath:
    pythonpath = f"{project_root_str}:{existing_pythonpath}"
else:
    pythonpath = project_root_str

brave_env = {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")}
polygon_api_key = os.getenv("POLYGON_API_KEY")

# Ambiente base para servidores MCP Python locais
# Inclui PYTHONPATH para permitir imports 'from src.core...'
mcp_python_env = {"PYTHONPATH": pythonpath}

# The MCP server for the Trader to read Market Data

if is_paid_polygon or is_realtime_polygon:
    market_mcp = {
        "command": "uvx",
        "args": ["--from", "git+https://github.com/polygon-io/mcp_polygon@v0.1.0", "mcp_polygon"],
        "env": {"POLYGON_API_KEY": polygon_api_key},
    }
else:
    # Use absolute path or relative from project root
    market_server_path = project_root / "src" / "core" / "market_server.py"
    # Adiciona PYTHONPATH ao ambiente para permitir imports
    market_env = mcp_python_env.copy()
    market_mcp = {
        "command": "uv",
        "args": ["run", str(market_server_path)],
        "env": market_env,
    }


# The full set of MCP servers for the trader: Accounts, Push Notification and the Market

accounts_server_path = project_root / "src" / "core" / "accounts_server.py"
push_server_path = project_root / "src" / "core" / "push_server.py"

# Configura servidores MCP com PYTHONPATH para permitir imports 'from src.core...'
trader_mcp_server_params = [
    {
        "command": "uv",
        "args": ["run", str(accounts_server_path)],
        "env": mcp_python_env.copy(),  # Inclui PYTHONPATH
    },
    {
        "command": "uv",
        "args": ["run", str(push_server_path)],
        "env": mcp_python_env.copy(),  # Inclui PYTHONPATH
    },
    market_mcp,
]

# The full set of MCP servers for the researcher: Fetch, Brave Search and Memory


def researcher_mcp_server_params(name: str):
    """
    Retorna configuração dos servidores MCP para o pesquisador (researcher).
    
    PARÂMETROS:
        name: Nome do trader (ex: "Warren", "George") - usado para criar banco de memória único
    
    SERVIDORES RETORNADOS:
    1. Fetch Server: Busca páginas web (via uvx)
    2. Brave Search Server: Pesquisa na web (via npx)
    3. Memory Server: Memória persistente libSQL (via npx)
       - Cada trader tem seu próprio banco de memória
       - Caminho absoluto garante que funciona independente do diretório de execução
    """
    # Caminho absoluto para o banco de memória do trader
    # Usa caminho absoluto para garantir que funciona mesmo quando npx executa de outro diretório
    memory_db_path = project_root / "data" / "memory" / f"{name}.db"
    memory_db_url = f"file:{memory_db_path}"
    
    return [
        {"command": "uvx", "args": ["mcp-server-fetch"]},
        {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": brave_env,
        },
        {
            "command": "npx",
            "args": ["-y", "mcp-memory-libsql"],
            "env": {"LIBSQL_URL": memory_db_url},
        },
    ]
