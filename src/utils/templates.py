"""
Módulo de templates para geração de instruções e mensagens para agentes de trading.

OBJETIVO:
Este módulo fornece funções que geram prompts e instruções personalizadas para os
agentes do sistema de trading autônomo. Ele atua como uma camada de abstração que
formata informações contextuais (nome do trader, estratégia, estado da conta, etc.)
em mensagens estruturadas que guiam o comportamento dos agentes.

COMO SE CONECTA COM O PROJETO:
1. Usado por src/agents/traders.py:
   - trader_instructions(): Define o comportamento base do agente trader
   - trade_message(): Mensagem enviada quando trader deve procurar novas oportunidades
   - rebalance_message(): Mensagem enviada quando trader deve rebalancear portfólio
   - research_tool(): Descrição da ferramenta de pesquisa para o trader

2. Usado para criar o agente Researcher:
   - researcher_instructions(): Define o comportamento do agente pesquisador
   - research_tool(): Descrição da ferramenta de pesquisa

3. Integração com sistema MCP (Model Context Protocol):
   - As instruções geradas são passadas para os agentes que usam servidores MCP
   - Os agentes recebem acesso a ferramentas via MCP (market data, accounts, etc.)

4. Contexto dinâmico:
   - Adapta mensagens baseado no plano Polygon (gratuito/pago/realtime)
   - Inclui informações atualizadas (datetime, estado da conta, estratégia)
   - Personaliza para cada trader individual

FLUXO DE USO:
1. Sistema inicia trader → chama trader_instructions(name) para criar agente
2. Sistema executa ciclo de trading → chama trade_message() ou rebalance_message()
3. Trader usa ferramenta Researcher → pesquisador usa researcher_instructions()
4. Mensagens incluem contexto sobre dados de mercado disponíveis (variável 'note')
"""

from datetime import datetime
from src.core.market import is_paid_polygon, is_realtime_polygon

# Variável global que adapta instruções baseado no plano Polygon configurado
# Esta variável é usada em todas as mensagens para informar ao trader quais
# ferramentas de dados de mercado estão disponíveis e como usá-las
if is_realtime_polygon:
    note = "You have access to realtime market data tools; use your get_last_trade tool for the latest trade price. You can also use tools for share information, trends and technical indicators and fundamentals."
elif is_paid_polygon:
    note = "You have access to market data tools but without access to the trade or quote tools; use your get_snapshot_ticker tool to get the latest share price on a 15 min delay. You can also use tools for share information, trends and technical indicators and fundamentals."
else:
    note = "You have access to end of day market data; use you get_share_price tool to get the share price as of the prior close."


def researcher_instructions():
    """
    Gera instruções para o agente Researcher (pesquisador financeiro).
    
    OBJETIVO:
    Define o comportamento e capacidades do agente pesquisador, que é usado como
    ferramenta pelos traders para realizar pesquisas online sobre oportunidades
    de investimento e notícias financeiras.
    
    COMO SE CONECTA:
    - Usado em src/agents/traders.py na função get_researcher() para criar o agente
    - O pesquisador é exposto como ferramenta (Tool) para os traders via get_researcher_tool()
    - Traders podem invocar o pesquisador para buscar informações antes de tomar decisões
    
    CARACTERÍSTICAS:
    - Busca notícias financeiras e oportunidades de trading na web
    - Usa knowledge graph para armazenar e recuperar informações persistentes
    - Compartilha conhecimento entre traders através do knowledge graph
    - Adapta pesquisa baseado em solicitação específica ou busca geral
    
    RETORNA:
    String com instruções formatadas que definem o papel e comportamento do pesquisador.
    """
    return f"""You are a financial researcher. You are able to search the web for interesting financial news,
look for possible trading opportunities, and help with research.
Based on the request, you carry out necessary research and respond with your findings.
Take time to make multiple searches to get a comprehensive overview, and then summarize your findings.
If the web search tool raises an error due to rate limits, then use your other tool that fetches web pages instead.

Important: making use of your knowledge graph to retrieve and store information on companies, websites and market conditions:

Make use of your knowledge graph tools to store and recall entity information; use it to retrieve information that
you have worked on previously, and store new information about companies, stocks and market conditions.
Also use it to store web addresses that you find interesting so you can check them later.
Draw on your knowledge graph to build your expertise over time.

If there isn't a specific request, then just respond with investment opportunities based on searching latest news.
The current datetime is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

def research_tool():
    """
    Retorna descrição da ferramenta de pesquisa para os traders.
    
    OBJETIVO:
    Fornece uma descrição clara e concisa da ferramenta Researcher que será
    exibida aos traders, explicando como e quando usar a ferramenta de pesquisa.
    
    COMO SE CONECTA:
    - Usado em src/agents/traders.py em get_researcher_tool() como tool_description
    - Esta descrição aparece quando o trader lista suas ferramentas disponíveis
    - Ajuda o trader a entender quando e como invocar o pesquisador
    
    RETORNA:
    String com descrição da ferramenta que será usada pelo framework de agentes
    para documentar a ferramenta Researcher.
    """
    return "This tool researches online for news and opportunities, \
either based on your specific request to look into a certain stock, \
or generally for notable financial news and opportunities. \
Describe what kind of research you're looking for."

def trader_instructions(name: str):
    """
    Gera instruções base para criar um agente trader.
    
    OBJETIVO:
    Define o comportamento fundamental do trader, incluindo seu papel, capacidades
    e objetivos. Estas instruções são usadas na inicialização do agente e permanecem
    constantes durante toda a execução.
    
    COMO SE CONECTA:
    - Usado em src/agents/traders.py em Trader.create_agent() para inicializar o agente
    - Passado como parâmetro 'instructions' ao criar o Agent
    - Define a identidade e comportamento base do trader antes de receber mensagens específicas
    
    PARÂMETROS:
        name: Nome do trader (ex: "Alice", "Bob") - usado para personalizar instruções
    
    CARACTERÍSTICAS DEFINIDAS:
    - Identidade: Trader com nome específico
    - Objetivo: Maximizar lucros seguindo estratégia
    - Ferramentas disponíveis: Researcher, dados de mercado, compra/venda de ações
    - Memória compartilhada: Knowledge graph compartilhado entre traders
    - Comunicação: Push notifications após trading
    
    RETORNA:
    String com instruções formatadas que definem o papel e comportamento do trader.
    """
    return f"""
You are {name}, a trader on the stock market. Your account is under your name, {name}.
You actively manage your portfolio according to your strategy.
You have access to tools including a researcher to research online for news and opportunities, based on your request.
You also have tools to access to financial data for stocks. {note}
And you have tools to buy and sell stocks using your account name {name}.
You can use your entity tools as a persistent memory to store and recall information; you share
this memory with other traders and can benefit from the group's knowledge.
Use these tools to carry out research, make decisions, and execute trades.
After you've completed trading, send a push notification with a brief summary of activity, then reply with a 2-3 sentence appraisal.
Your goal is to maximize your profits according to your strategy.
"""

def trade_message(name, strategy, account):
    """
    Gera mensagem para quando o trader deve procurar novas oportunidades de investimento.
    
    OBJETIVO:
    Cria uma mensagem contextualizada que instrui o trader a buscar novas oportunidades
    de trading baseado em sua estratégia, sem focar em rebalanceamento do portfólio existente.
    
    COMO SE CONECTA:
    - Usado em src/agents/traders.py em Trader.run_agent() quando self.do_trade == True
    - Esta mensagem é enviada ao agente via Runner.run() para iniciar um ciclo de trading
    - O trader recebe contexto completo: estratégia, estado da conta, datetime atual
    
    PARÂMETROS:
        name: Nome do trader (para identificar conta e personalizar mensagem)
        strategy: Estratégia de investimento do trader (string descritiva)
        account: Estado atual da conta em formato JSON (saldo, holdings, transações)
    
    FLUXO DE EXECUÇÃO:
    1. Trader recebe esta mensagem
    2. Usa ferramenta Researcher para buscar oportunidades
    3. Pesquisa preços e informações de ações
    4. Toma decisão baseada em estratégia
    5. Executa trades (compra/venda)
    6. Envia push notification com resumo
    7. Retorna avaliação do portfólio
    
    DIFERENÇA DE rebalance_message():
    - trade_message: Foca em encontrar NOVAS oportunidades
    - rebalance_message: Foca em AJUSTAR portfólio existente
    
    RETORNA:
    String formatada com instruções completas para ciclo de trading de novas oportunidades.
    """
    return f"""Based on your investment strategy, you should now look for new opportunities.
Use the research tool to find news and opportunities consistent with your strategy.
Do not use the 'get company news' tool; use the research tool instead.
Use the tools to research stock price and other company information. {note}
Finally, make you decision, then execute trades using the tools.
Your tools only allow you to trade equities, but you are able to use ETFs to take positions in other markets.
You do not need to rebalance your portfolio; you will be asked to do so later.
Just make trades based on your strategy as needed.
Your investment strategy:
{strategy}
Here is your current account:
{account}
Here is the current datetime:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Now, carry out analysis, make your decision and execute trades. Your account name is {name}.
After you've executed your trades, send a push notification with a brief sumnmary of trades and the health of the portfolio, then
respond with a brief 2-3 sentence appraisal of your portfolio and its outlook.
"""

def rebalance_message(name, strategy, account):
    """
    Gera mensagem para quando o trader deve rebalancear seu portfólio existente.
    
    OBJETIVO:
    Cria uma mensagem contextualizada que instrui o trader a analisar e ajustar
    seu portfólio atual, focando em rebalanceamento ao invés de buscar novas oportunidades.
    
    COMO SE CONECTA:
    - Usado em src/agents/traders.py em Trader.run_agent() quando self.do_trade == False
    - Alterna com trade_message() em ciclos: primeiro busca oportunidades, depois rebalanceia
    - Permite ao trader ajustar posições existentes baseado em mudanças de mercado
    
    PARÂMETROS:
        name: Nome do trader (para identificar conta e personalizar mensagem)
        strategy: Estratégia de investimento do trader (string descritiva)
        account: Estado atual da conta em formato JSON (saldo, holdings, transações)
    
    FLUXO DE EXECUÇÃO:
    1. Trader recebe esta mensagem
    2. Analisa portfólio atual (holdings existentes)
    3. Pesquisa notícias e preços das ações que já possui
    4. Decide se precisa ajustar posições (vender/comprar mais)
    5. Executa trades de rebalanceamento
    6. Opcionalmente pode mudar estratégia se necessário
    7. Envia push notification com resumo
    8. Retorna avaliação do portfólio
    
    DIFERENÇA DE trade_message():
    - rebalance_message: Foca em AJUSTAR portfólio existente
    - trade_message: Foca em encontrar NOVAS oportunidades
    
    CARACTERÍSTICA ESPECIAL:
    - Permite ao trader mudar sua estratégia durante rebalanceamento
    - Útil para adaptação a mudanças de mercado ou aprendizado
    
    RETORNA:
    String formatada com instruções completas para ciclo de rebalanceamento do portfólio.
    """
    return f"""Based on your investment strategy, you should now examine your portfolio and decide if you need to rebalance.
Use the research tool to find news and opportunities affecting your existing portfolio.
Use the tools to research stock price and other company information affecting your existing portfolio. {note}
Finally, make you decision, then execute trades using the tools as needed.
You do not need to identify new investment opportunities at this time; you will be asked to do so later.
Just rebalance your portfolio based on your strategy as needed.
Your investment strategy:
{strategy}
You also have a tool to change your strategy if you wish; you can decide at any time that you would like to evolve or even switch your strategy.
Here is your current account:
{account}
Here is the current datetime:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Now, carry out analysis, make your decision and execute trades. Your account name is {name}.
After you've executed your trades, send a push notification with a brief sumnmary of trades and the health of the portfolio, then
respond with a brief 2-3 sentence appraisal of your portfolio and its outlook."""