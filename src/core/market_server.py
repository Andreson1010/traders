"""
Servidor MCP para fornecer dados de mercado (preços de ações) aos traders.

OBJETIVO:
Este módulo expõe a funcionalidade de obtenção de preços de ações como um servidor MCP
(Model Context Protocol), permitindo que os agentes traders consultem preços de ações
através do protocolo MCP.

COMO SE CONECTA COM O PROJETO:
1. Usado pelos traders: Cada trader agent recebe acesso a este servidor via MCP
2. Configurado em mcp_params.py: Incluído na lista trader_mcp_server_params
3. Executado via uv run: Iniciado como processo separado quando traders são criados
4. Comunicação: Via stdio (standard input/output) seguindo protocolo MCP

QUANDO É USADO:
- Quando POLYGON_PLAN=free (plano gratuito): Este servidor local é usado
- Quando POLYGON_PLAN=paid ou realtime: Usa servidor externo mcp_polygon via uvx

FERRAMENTA EXPOSTA:
- lookup_share_price(symbol): Retorna preço atual de uma ação
  - Usa get_share_price() de market.py
  - Suporta cache e fallback para valores aleatórios se API falhar
  - Retorna float com preço da ação

ARQUITETURA:
- FastMCP: Framework que facilita criação de servidores MCP
- @mcp.tool(): Decorador que expõe função como ferramenta MCP
- transport='stdio': Comunicação via entrada/saída padrão (protocolo MCP)

FLUXO DE USO:
1. Trader agent precisa saber preço de uma ação (ex: "AAPL")
2. Chama ferramenta lookup_share_price("AAPL") via MCP
3. market_server.py recebe requisição via stdio
4. Chama get_share_price("AAPL") de market.py
5. Retorna preço para o trader agent
6. Trader usa preço para tomar decisões de compra/venda
"""

# Configura o caminho do projeto para permitir imports 'from src.core...'
# Isso garante que o módulo funcione mesmo quando executado via uv run ou como servidor MCP
import sys
import pathlib

# Obtém o diretório raiz do projeto (3 níveis acima deste arquivo: src/core/market_server.py)
project_root = pathlib.Path(__file__).parent.parent.parent
project_root_str = str(project_root)

# Adiciona ao sys.path se ainda não estiver lá
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from mcp.server.fastmcp import FastMCP
from src.core.market import get_share_price

# Cria instância do servidor MCP usando FastMCP
# FastMCP facilita criação de servidores MCP sem implementar protocolo manualmente
mcp = FastMCP("market_server")

@mcp.tool()
async def lookup_share_price(symbol: str) -> float:
    """
    Ferramenta MCP que fornece o preço atual de uma ação.
    
    OBJETIVO:
    Permite que traders agents consultem preços de ações através do protocolo MCP.
    Esta é a única ferramenta exposta por este servidor.
    
    PARÂMETROS:
        symbol: Ticker da ação (ex: "AAPL", "TSLA", "MSFT", "GOOGL")
    
    PROCESSO:
    1. Recebe símbolo da ação do trader agent via MCP
    2. Chama get_share_price() de market.py
    3. get_share_price() tenta obter preço via Polygon API
    4. Se API falhar, retorna valor aleatório (permite simulação continuar)
    5. Retorna preço (real ou simulado) para o trader
    
    RETORNA:
        float: Preço da ação em dólares
        - Preço real se API Polygon funcionar
        - Valor aleatório $1-100 se API falhar (para simulação continuar)
    
    USO PELO TRADER:
    O trader agent pode chamar esta ferramenta quando precisa:
    - Verificar preço antes de comprar/vender
    - Analisar valor de ações para decisões de investimento
    - Calcular custos de transações
    
    EXEMPLO:
        Trader: "Quero comprar AAPL, qual o preço?"
        → Chama lookup_share_price("AAPL")
        → Retorna: 150.25 (ou valor aleatório se API offline)
    """
    return get_share_price(symbol)

if __name__ == "__main__":
    """
    Ponto de entrada quando servidor é executado diretamente.
    
    EXECUÇÃO:
    - Normalmente executado via: uv run market_server.py
    - Configurado em mcp_params.py como parte dos servidores MCP dos traders
    
    TRANSPORT:
    - stdio: Comunicação via standard input/output
    - Segue protocolo MCP para comunicação com clientes MCP
    """
    mcp.run(transport='stdio')