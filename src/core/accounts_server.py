"""
Servidor MCP para gerenciamento de contas de trading.

Este módulo expõe funcionalidades do módulo accounts.py como um servidor MCP (Model Context Protocol),
permitindo que agentes de IA acessem e manipulem contas de traders através do protocolo MCP.

Objetivo principal: Transformar a lógica de negócios (accounts.py) em um servidor MCP que pode ser
usado por agentes autônomos para:
- Consultar saldo e holdings
- Executar compras e vendas de ações
- Alterar estratégias de investimento
- Ler dados de conta e estratégia como recursos

Arquitetura:
- FastMCP: Framework para criar servidores MCP rapidamente
- Tools (@mcp.tool): Ações que agentes podem executar (buy, sell, etc.)
- Resources (@mcp.resource): Dados que agentes podem ler (account details, strategy)

Comunicação: Via stdio (standard input/output) quando executado como servidor MCP.
"""

# Configura o caminho do projeto para permitir imports 'from src.core...'
# Isso garante que o módulo funcione mesmo quando executado via uv run ou como servidor MCP
import sys
import pathlib

# Obtém o diretório raiz do projeto (3 níveis acima deste arquivo: src/core/accounts_server.py)
project_root = pathlib.Path(__file__).parent.parent.parent
project_root_str = str(project_root)

# Adiciona ao sys.path se ainda não estiver lá
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from mcp.server.fastmcp import FastMCP
from src.core.accounts import Account
from datetime import datetime

# Cria instância do servidor MCP usando FastMCP
# FastMCP facilita a criação de servidores MCP sem precisar implementar o protocolo manualmente
mcp = FastMCP("accounts_server")

# ============================================================================
# FERRAMENTAS (TOOLS) - Ações que agentes podem executar
# ============================================================================

@mcp.tool()
async def get_balance(name: str) -> float:
    """
    Obtém o saldo em dinheiro de uma conta.
    
    Objetivo: Permitir que o trader agent verifique quanto dinheiro tem disponível
    antes de fazer compras ou para relatórios de portfólio.
    
    Parâmetros:
        name: Nome do trader (ex: "Ed", "Warren")
    
    Retorna: Saldo em dinheiro (float) em dólares.
    
    Uso pelo agente: Verificar fundos disponíveis antes de comprar ações.
    """
    return Account.get(name).balance

@mcp.tool()
async def get_holdings(name: str) -> dict[str, int]:
    """
    Obtém as ações atualmente possuídas por uma conta.
    
    Objetivo: Permitir que o trader agent veja quais ações possui e em que quantidades,
    útil para decidir vendas ou verificar diversificação do portfólio.
    
    Parâmetros:
        name: Nome do trader (ex: "Ed", "Warren")
    
    Retorna: Dicionário {symbol: quantity} com todas as ações possuídas.
        Exemplo: {"AAPL": 10, "TSLA": 5}
    
    Uso pelo agente: Verificar posições atuais antes de tomar decisões de trading.
    """
    return Account.get(name).holdings

@mcp.tool()
async def buy_shares(name: str, symbol: str, quantity: int, rationale: str) -> float:
    """
    Compra ações de uma empresa.
    
    Objetivo: Executar ordem de compra de ações, que é a operação principal do trader agent.
    Esta é a ferramenta mais importante para permitir que agentes façam trading.
    
    Parâmetros:
        name: Nome do trader (ex: "Ed")
        symbol: Ticker da ação (ex: "AAPL", "TSLA", "MSFT")
        quantity: Quantidade de ações a comprar (int)
        rationale: Justificativa da compra e como se alinha com a estratégia do trader
    
    Retorna: String com relatório atualizado da conta após a compra.
    
    Processo interno (via accounts.py):
        1. Obtém preço atual da ação
        2. Aplica spread de compra (0.2%)
        3. Valida se há fundos suficientes
        4. Atualiza holdings
        5. Registra transação
        6. Deduz custo do saldo
        7. Salva no banco de dados
    
    Uso pelo agente: Quando decide comprar ações baseado em pesquisa ou análise de mercado.
    """
    return Account.get(name).buy_shares(symbol, quantity, rationale)


@mcp.tool()
async def sell_shares(name: str, symbol: str, quantity: int, rationale: str) -> float:
    """
    Vende ações de uma empresa.
    
    Objetivo: Executar ordem de venda de ações, permitindo ao trader agent realizar lucros,
    cortar perdas ou rebalancear portfólio.
    
    Parâmetros:
        name: Nome do trader (ex: "Ed")
        symbol: Ticker da ação a vender (ex: "AAPL", "TSLA")
        quantity: Quantidade de ações a vender (int)
        rationale: Justificativa da venda e como se alinha com a estratégia do trader
    
    Retorna: String com relatório atualizado da conta após a venda.
    
    Processo interno (via accounts.py):
        1. Valida se há ações suficientes para vender
        2. Obtém preço atual da ação
        3. Aplica spread de venda (0.2%)
        4. Atualiza holdings (remove ações)
        5. Registra transação
        6. Adiciona receita ao saldo
        7. Salva no banco de dados
    
    Uso pelo agente: Quando decide vender ações para realizar lucros ou cortar perdas.
    """
    return Account.get(name).sell_shares(symbol, quantity, rationale)

@mcp.tool()
async def change_strategy(name: str, strategy: str) -> str:
    """
    Altera a estratégia de investimento de um trader.
    
    Objetivo: Dar autonomia ao trader agent para evoluir sua estratégia baseado em
    aprendizado, mudanças de mercado ou reflexão sobre performance.
    
    Parâmetros:
        name: Nome do trader (ex: "Ed")
        strategy: Nova estratégia de investimento (string descritiva)
            Exemplo: "You are a value investor focused on long-term growth"
    
    Retorna: Confirmação da mudança de estratégia.
    
    Uso pelo agente: Quando o trader decide que sua estratégia atual não está funcionando
    bem ou quer adaptar-se a novas condições de mercado. Demonstra autonomia e aprendizado.
    
    Nota: Esta ferramenta permite que traders evoluam e se adaptem, não ficando presos
    à estratégia inicial.
    """
    return Account.get(name).change_strategy(strategy)


@mcp.tool()
async def get_date_time() -> str:
    """
    Retorna a data e hora atual.
    
    Objetivo: Fornecer contexto temporal para o trader agent, permitindo que ele saiba
    a data/hora atual para tomar decisões baseadas em timing (ex: horário de mercado,
    datas importantes, etc.).
    
    Retorna: String formatada "YYYY-MM-DD HH:MM:SS"
        Exemplo: "2024-11-28 16:30:45"
    
    Uso pelo agente: Verificar se mercados estão abertos, contexto temporal para decisões,
    ou para incluir em relatórios.
    
    Nota: Embora seja possível incluir data/hora nas instruções do agente, esta ferramenta
    permite que o agente busque a data atual quando necessário durante a execução.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================================
# RECURSOS (RESOURCES) - Dados que agentes podem ler
# ============================================================================

@mcp.resource("accounts://accounts_server/{name}")
async def read_account_resource(name: str) -> str:
    """
    Recurso MCP que fornece dados completos da conta de um trader.
    
    Objetivo: Expor informações completas da conta (saldo, holdings, transações, P&L)
    como um RECURSO MCP, que pode ser lido e incorporado nas instruções dos agentes.
    
    URI do recurso: "accounts://accounts_server/{name}"
        Exemplo: "accounts://accounts_server/Ed"
    
    Parâmetros:
        name: Nome do trader (ex: "Ed", "Warren")
    
    Retorna: String JSON com dados completos da conta:
        {
            "name": "ed",
            "balance": 10000.0,
            "holdings": {"AAPL": 10, "TSLA": 5},
            "transactions": [...],
            "total_portfolio_value": 15000.0,
            "total_profit_loss": 5000.0,
            "portfolio_value_time_series": [...]
        }
    
    Diferença de Tools:
        - Resource: Dados para LEITURA (usado nas instruções do agente)
        - Tool: Ações para EXECUÇÃO (chamadas durante runtime)
    
    Uso: Incorporado nas instruções do trader agent via accounts_client.read_accounts_resource()
    para dar contexto completo sobre o estado atual da conta.
    
    Relacionamento: Este recurso é lido pelo accounts_client.py e incorporado nas
    instruções do trader no notebook 4_lab4.ipynb.
    """
    account = Account.get(name.lower())
    return account.report()

@mcp.resource("accounts://strategy/{name}")
async def read_strategy_resource(name: str) -> str:
    """
    Recurso MCP que fornece a estratégia de investimento de um trader.
    
    Objetivo: Expor a estratégia de investimento como um RECURSO MCP, permitindo que
    seja incorporada nas instruções dos agentes para definir comportamento e personalidade.
    
    URI do recurso: "accounts://strategy/{name}"
        Exemplo: "accounts://strategy/Ed"
    
    Parâmetros:
        name: Nome do trader (ex: "Ed", "Warren")
    
    Retorna: String com a descrição da estratégia de investimento.
        Exemplo: "You are a day trader that aggressively buys and sells shares based on news and market conditions."
    
    Uso: Incorporado nas instruções do trader agent via accounts_client.read_strategy_resource()
    para definir como o trader deve se comportar e tomar decisões.
    
    Relacionamento: Este recurso é lido pelo accounts_client.py e incorporado nas
    instruções do trader no notebook 4_lab4.ipynb, permitindo que cada trader tenha
    uma personalidade e estratégia única.
    """
    account = Account.get(name.lower())
    return account.get_strategy()


# ============================================================================
# EXECUÇÃO DO SERVIDOR
# ============================================================================

if __name__ == "__main__":
    """
    Executa o servidor MCP quando o arquivo é chamado diretamente.
    
    Objetivo: Permitir executar o servidor MCP standalone para testes ou uso direto.
    
    Transport: stdio (standard input/output)
        - Comunicação via stdin/stdout
        - Padrão para servidores MCP locais
        - Permite integração com MCPServerStdio do OpenAI Agents SDK
    
    Uso:
        python accounts_server.py
        ou
        uv run accounts_server.py
    
    Quando usado pelo MCPServerStdio:
        O servidor é executado automaticamente via stdio quando configurado em
        mcp_params.py ou no notebook.
    """
    mcp.run(transport='stdio')