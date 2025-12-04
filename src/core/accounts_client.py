"""
Cliente MCP para interagir com o accounts_server.py.

Este módulo implementa um cliente MCP que se conecta ao servidor de contas via stdio,
permitindo:
- Listar ferramentas disponíveis no servidor
- Chamar ferramentas do servidor (buy_shares, sell_shares, etc.)
- Ler recursos do servidor (account details, strategy)
- Converter ferramentas MCP para formato OpenAI Function Tools

Objetivo: Fornecer uma interface Python para acessar funcionalidades do accounts_server
sem precisar usar o MCPServerStdio diretamente. Útil para leitura de recursos que
serão incorporados nas instruções dos agentes.
"""

import mcp
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters
from agents import FunctionTool
import json

# Parâmetros para conectar ao servidor MCP de contas
# Executa accounts_server.py via 'uv run' e comunica via stdio
import pathlib
project_root = pathlib.Path(__file__).parent.parent.parent
accounts_server_path = project_root / "src" / "core" / "accounts_server.py"
params = StdioServerParameters(command="uv", args=["run", str(accounts_server_path)], env=None)


async def list_accounts_tools():
    """
    Lista todas as ferramentas disponíveis no accounts_server.
    
    Objetivo: Descobrir quais ferramentas o servidor MCP expõe (ex: buy_shares, sell_shares,
    get_balance, etc.) sem precisar conhecer a implementação do servidor.
    
    Processo:
    1. Conecta ao servidor MCP via stdio
    2. Inicializa sessão MCP
    3. Solicita lista de ferramentas
    4. Retorna lista de objetos Tool
    
    Retorna: Lista de objetos Tool com informações sobre cada ferramenta disponível.
    """
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            return tools_result.tools
        
async def call_accounts_tool(tool_name, tool_args):
    """
    Chama uma ferramenta específica do accounts_server.
    
    Objetivo: Executar uma ferramenta do servidor MCP (ex: buy_shares, sell_shares) de forma
    assíncrona, permitindo que código Python chame funcionalidades do servidor diretamente.
    
    Parâmetros:
        tool_name: Nome da ferramenta a ser chamada (ex: "buy_shares", "get_balance")
        tool_args: Dicionário com argumentos da ferramenta (ex: {"name": "Ed", "symbol": "AAPL", "quantity": 10})
    
    Processo:
    1. Conecta ao servidor MCP via stdio
    2. Inicializa sessão MCP
    3. Chama a ferramenta com os argumentos fornecidos
    4. Retorna resultado da execução
    
    Retorna: Resultado da execução da ferramenta (geralmente texto ou dados estruturados).
    
    Exemplo de uso:
        result = await call_accounts_tool("get_balance", {"name": "Ed"})
    """
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_args)
            return result
            
async def read_accounts_resource(name):
    """
    Lê o recurso de conta de um trader específico.
    
    Objetivo: Obter informações completas da conta (saldo, holdings, transações) em formato
    JSON/texto para incorporar nas instruções dos agentes. Este é um RECURSO MCP, não uma
    ferramenta - fornece dados, não executa ações.
    
    Parâmetros:
        name: Nome do trader (ex: "Ed", "Warren")
    
    Processo:
    1. Conecta ao servidor MCP via stdio
    2. Inicializa sessão MCP
    3. Lê recurso usando URI: "accounts://accounts_server/{name}"
    4. Retorna conteúdo do recurso (JSON string com dados da conta)
    
    Retorna: String JSON com dados completos da conta:
        {
            "name": "ed",
            "balance": 10000.0,
            "holdings": {"AAPL": 10},
            "transactions": [...],
            "total_portfolio_value": 15000.0,
            "total_profit_loss": 5000.0
        }
    
    Uso: Incorporado nas instruções do trader agent para dar contexto sobre estado atual.
    
    Relacionamento com accounts_server.py:
        O servidor expõe este recurso via @mcp.resource() decorator.
    """
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.read_resource(f"accounts://accounts_server/{name}")
            return result.contents[0].text
        
async def read_strategy_resource(name):
    """
    Lê o recurso de estratégia de investimento de um trader específico.
    
    Objetivo: Obter a estratégia de investimento do trader em formato texto para incorporar
    nas instruções dos agentes. Este é um RECURSO MCP que fornece a descrição da estratégia
    (ex: "You are a day trader that aggressively buys and sells...").
    
    Parâmetros:
        name: Nome do trader (ex: "Ed", "Warren")
    
    Processo:
    1. Conecta ao servidor MCP via stdio
    2. Inicializa sessão MCP
    3. Lê recurso usando URI: "accounts://strategy/{name}"
    4. Retorna conteúdo do recurso (string com descrição da estratégia)
    
    Retorna: String com a estratégia de investimento do trader.
        Exemplo: "You are a day trader that aggressively buys and sells shares based on news and market conditions."
    
    Uso: Incorporado nas instruções do trader agent para definir seu comportamento e personalidade.
    
    Relacionamento com accounts_server.py:
        O servidor expõe este recurso via @mcp.resource() decorator, que lê Account.get(name).strategy.
    """
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.read_resource(f"accounts://strategy/{name}")
            return result.contents[0].text

async def get_accounts_tools_openai():
    """
    Converte ferramentas MCP do accounts_server para formato OpenAI Function Tools.
    
    Objetivo: Transformar ferramentas MCP em FunctionTools compatíveis com o OpenAI Agents SDK,
    permitindo que agentes OpenAI usem as ferramentas do accounts_server diretamente.
    
    Processo:
    1. Lista todas as ferramentas disponíveis no servidor
    2. Para cada ferramenta:
       - Extrai schema de entrada (inputSchema)
       - Cria FunctionTool com nome, descrição e schema
       - Configura callback que chama a ferramenta MCP quando invocada
    3. Retorna lista de FunctionTools prontas para uso
    
    Retorna: Lista de FunctionTool objetos que podem ser passados para Agent:
        [
            FunctionTool(name="buy_shares", ...),
            FunctionTool(name="sell_shares", ...),
            FunctionTool(name="get_balance", ...),
            ...
        ]
    
    Uso: Permite usar ferramentas do accounts_server com agentes OpenAI sem precisar
    configurar MCPServerStdio diretamente.
    
    Exemplo de uso:
        tools = await get_accounts_tools_openai()
        agent = Agent(tools=tools, ...)
    
    Nota: Esta função não é usada no projeto atual (usamos MCPServerStdio diretamente),
    mas está disponível para casos onde se precisa de mais controle sobre as ferramentas.
    """
    openai_tools = []
    for tool in await list_accounts_tools():
        # Copia o schema e adiciona restrição adicional
        schema = {**tool.inputSchema, "additionalProperties": False}
        
        # Cria FunctionTool que, quando invocada, chama a ferramenta MCP correspondente
        openai_tool = FunctionTool(
            name=tool.name,
            description=tool.description,
            params_json_schema=schema,
            # Callback: quando agente chama a ferramenta, executa call_accounts_tool
            on_invoke_tool=lambda ctx, args, toolname=tool.name: call_accounts_tool(toolname, json.loads(args))
                
        )
        openai_tools.append(openai_tool)
    return openai_tools