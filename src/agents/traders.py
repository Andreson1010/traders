"""
Módulo Traders - Definição e Implementação dos Traders Autônomos

OBJETIVO DO MÓDULO:
Este módulo define a classe Trader e funções auxiliares que criam e executam traders autônomos.
Cada trader é um agente de IA que toma decisões de investimento baseadas em pesquisa, análise
de mercado e sua estratégia pessoal.

COMO SE CONECTA COM O PROJETO:
1. Importado em trading_floor.py: Cria e executa os 4 traders periodicamente
2. Usa servidores MCP: Configurados em mcp_params.py para acesso a contas, mercado, pesquisa
3. Integra com accounts.py: Cada trader gerencia sua própria conta via Accounts Server MCP
4. Usa templates: Instruções e mensagens definidas em templates.py
5. Tracing: Eventos capturados por tracers.py e exibidos na UI

ARQUITETURA:
- Trader: Classe principal que encapsula um agente de IA trader
- Researcher: Agente auxiliar que pesquisa informações para o trader
- Servidores MCP: Fornecem ferramentas (accounts, market, search, memory)
- Modelos de IA: Suporte para múltiplos provedores (OpenAI, DeepSeek, Grok, Gemini, OpenRouter)

FLUXO DE EXECUÇÃO:
1. trading_floor.py cria instância Trader("Warren", "Patience", "gpt-4o-mini")
2. trading_floor.py chama trader.run()
3. Trader.run() → run_with_trace() → run_with_mcp_servers()
4. run_with_mcp_servers() inicia servidores MCP e chama run_agent()
5. run_agent() cria agente, obtém dados da conta e executa ciclo de trading
6. Agente usa Researcher para pesquisar, depois decide comprar/vender
7. Agente usa Accounts Server para executar trades
8. Eventos são capturados via tracing e salvos no banco de dados
9. UI (app.py) lê do banco e exibe em tempo real
"""

from contextlib import AsyncExitStack
from src.core.accounts_client import read_accounts_resource, read_strategy_resource
from src.utils.tracers import make_trace_id
from agents import Agent, Tool, Runner, OpenAIChatCompletionsModel, trace
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
import json
from agents.mcp import MCPServerStdio
from src.utils.templates import (
    researcher_instructions,
    trader_instructions,
    trade_message,
    rebalance_message,
    research_tool,
)
from src.utils.mcp_params import trader_mcp_server_params, researcher_mcp_server_params

# Carrega variáveis de ambiente do arquivo .env
# override=True garante que valores do .env sobrescrevem variáveis já existentes
# Necessário para carregar chaves de API de diferentes provedores
load_dotenv(override=True)

# ============================================================================
# CONFIGURAÇÃO DE CHAVES DE API E CLIENTES
# ============================================================================
# Objetivo: Carregar chaves de API e criar clientes para diferentes provedores de IA
#
# Por que múltiplos provedores?
# - Permite usar diferentes modelos de IA para diferentes traders
# - Alguns modelos são melhores para certas tarefas
# - Distribui custos entre diferentes provedores
# - Permite experimentação com modelos novos
#
# Provedores suportados:
# - OpenAI: Modelos padrão (gpt-4o-mini, gpt-4, etc.)
# - DeepSeek: Modelos econômicos e eficientes
# - Grok (xAI): Modelos da X/Twitter
# - Gemini (Google): Modelos do Google
# - OpenRouter: Gateway unificado para acessar múltiplos modelos

# Carrega chaves de API de variáveis de ambiente
# Essas chaves devem estar configuradas no arquivo .env
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")
grok_api_key = os.getenv("GROK_API_KEY")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

# URLs base das APIs de cada provedor
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
GROK_BASE_URL = "https://api.x.ai/v1"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Número máximo de turnos de conversa que o agente pode fazer
# Limita o número de interações para evitar loops infinitos e controlar custos
MAX_TURNS = 30

# Cria clientes assíncronos para cada provedor de IA
# Esses clientes são usados para fazer chamadas às APIs de cada provedor
# AsyncOpenAI permite chamadas não-bloqueantes (importante para performance)
openrouter_client = AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=openrouter_api_key)
deepseek_client = AsyncOpenAI(base_url=DEEPSEEK_BASE_URL, api_key=deepseek_api_key)
grok_client = AsyncOpenAI(base_url=GROK_BASE_URL, api_key=grok_api_key)
gemini_client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=google_api_key)


def get_model(model_name: str):
    """
    Seleciona o cliente de API apropriado baseado no nome do modelo.
    
    OBJETIVO:
    Retorna um objeto de modelo configurado com o cliente correto para o provedor de IA
    especificado. Isso permite que o sistema use diferentes modelos de diferentes provedores
    de forma transparente.
    
    COMO SE RELACIONA COM O PROJETO:
    - Usado ao criar agentes Trader e Researcher
    - Permite que cada trader use um modelo diferente (configurável em trading_floor.py)
    - Suporta experimentação com diferentes modelos de IA
    - Centraliza lógica de seleção de provedor
    
    LÓGICA DE SELEÇÃO:
    - Modelos com "/" no nome → OpenRouter (ex: "gpt-4.1-mini", "gemini-2.5-flash-preview")
    - Modelos com "deepseek" → Cliente DeepSeek direto
    - Modelos com "grok" → Cliente Grok direto
    - Modelos com "gemini" → Cliente Google/Gemini direto
    - Outros → Retorna o nome do modelo como está (usado para modelos padrão como "gpt-4o-mini")
    
    POR QUE OPENROUTER PARA MODELOS COM "/"?
    Alguns modelos têm nomes específicos que não correspondem diretamente a um provedor único.
    O OpenRouter atua como intermediário, permitindo acessar esses modelos através de uma
    API unificada compatível com OpenAI.
    
    PARÂMETROS:
        model_name (str): Nome do modelo (ex: "gpt-4o-mini", "deepseek-chat", "grok-beta")
    
    RETORNA:
        OpenAIChatCompletionsModel ou str: Objeto de modelo configurado ou nome do modelo
    
    EXEMPLO:
        model = get_model("gpt-4o-mini")  # Retorna "gpt-4o-mini" (usa OpenAI padrão)
        model = get_model("deepseek-chat")  # Retorna OpenAIChatCompletionsModel com deepseek_client
        model = get_model("gpt-4.1-mini")  # Retorna OpenAIChatCompletionsModel com openrouter_client
    """
    if "/" in model_name:
        # Modelos com "/" são acessados via OpenRouter (gateway unificado)
        # Exemplos: "gpt-4.1-mini", "gemini-2.5-flash-preview-04-17", "grok-3-mini-beta"
        # OpenRouter permite acessar modelos de múltiplos provedores através de uma API unificada
        return OpenAIChatCompletionsModel(model=model_name, openai_client=openrouter_client)
    elif "deepseek" in model_name:
        # Modelos DeepSeek: Acessados diretamente via API DeepSeek
        # Exemplo: "deepseek-chat", "deepseek-coder"
        return OpenAIChatCompletionsModel(model=model_name, openai_client=deepseek_client)
    elif "grok" in model_name:
        # Modelos Grok (xAI): Acessados diretamente via API xAI
        # Exemplo: "grok-beta", "grok-2"
        return OpenAIChatCompletionsModel(model=model_name, openai_client=grok_client)
    elif "gemini" in model_name:
        # Modelos Gemini (Google): Acessados via API Google com compatibilidade OpenAI
        # Exemplo: "gemini-pro", "gemini-2.5-flash-preview"
        return OpenAIChatCompletionsModel(model=model_name, openai_client=gemini_client)
    else:
        # Modelos padrão (ex: "gpt-4o-mini") usam cliente OpenAI padrão
        # O framework 'agents' detecta automaticamente e usa cliente OpenAI padrão
        # Retorna string para que o framework escolha o cliente apropriado
        return model_name


async def get_researcher(mcp_servers, model_name) -> Agent:
    """
    Cria um agente Researcher (pesquisador) que auxilia o trader.
    
    OBJETIVO:
    Cria um agente de IA especializado em pesquisar informações sobre ações, empresas e mercado.
    O researcher é usado como ferramenta pelo trader para obter informações antes de tomar
    decisões de investimento.
    
    COMO SE RELACIONA COM O PROJETO:
    - Usado pelo trader para pesquisar informações sobre ações
    - Tem acesso a servidores MCP de pesquisa (Fetch, Brave Search, Memory)
    - Cada trader tem seu próprio researcher com memória isolada
    - Researcher salva informações importantes na memória para consultas futuras
    
    SERVIDORES MCP DO RESEARCHER:
    - Fetch Server: Busca conteúdo de páginas web específicas
    - Brave Search Server: Pesquisa informações na web
    - Memory Server: Armazena memória persistente (banco único por trader)
    
    FLUXO DE USO:
    1. Trader precisa pesquisar sobre ação "AAPL"
    2. Trader chama ferramenta Researcher
    3. Researcher usa Brave Search para encontrar artigos
    4. Researcher usa Fetch para ler conteúdo das páginas
    5. Researcher salva insights na Memory
    6. Researcher retorna resumo para o trader
    7. Trader usa informações para decidir se compra/vende
    
    PARÂMETROS:
        mcp_servers: Lista de servidores MCP para o researcher (Fetch, Brave, Memory)
        model_name: Nome do modelo de IA a usar (ex: "gpt-4o-mini")
    
    RETORNA:
        Agent: Agente Researcher configurado e pronto para usar
    """
    researcher = Agent(
        name="Researcher",  # Nome do agente
        instructions=researcher_instructions(),  # Instruções que definem comportamento do researcher
        model=get_model(model_name),  # Modelo de IA a usar (pode ser diferente do trader)
        mcp_servers=mcp_servers,  # Servidores MCP que fornecem ferramentas de pesquisa
    )
    return researcher


async def get_researcher_tool(mcp_servers, model_name) -> Tool:
    """
    Converte o agente Researcher em uma ferramenta (Tool) que o trader pode usar.
    
    OBJETIVO:
    Transforma o Researcher em uma ferramenta que o trader pode chamar durante sua execução.
    Isso permite que o trader use o researcher como uma ferramenta, não como agente separado.
    
    COMO SE RELACIONA COM O PROJETO:
    - O trader recebe o Researcher como ferramenta disponível
    - Quando trader precisa pesquisar, chama a ferramenta Researcher
    - Researcher executa pesquisa e retorna resultados
    - Trader usa resultados para tomar decisão de investimento
    
    DIFERENÇA ENTRE AGENTE E FERRAMENTA:
    - Agente: Executa de forma autônoma, pode fazer múltiplas ações
    - Ferramenta: Executa quando chamada, retorna resultado específico
    
    Por que converter em ferramenta?
    - Permite que trader controle quando pesquisar
    - Researcher não executa autonomamente, apenas quando trader precisa
    - Mais eficiente: researcher só roda quando necessário
    
    PARÂMETROS:
        mcp_servers: Lista de servidores MCP para o researcher
        model_name: Nome do modelo de IA a usar
    
    RETORNA:
        Tool: Ferramenta Researcher que trader pode usar
    """
    # Cria o agente researcher
    researcher = await get_researcher(mcp_servers, model_name)
    
    # Converte o agente em ferramenta
    # tool_name: Nome da ferramenta que aparecerá para o trader
    # tool_description: Descrição do que a ferramenta faz (usado pelo modelo para decidir quando usar)
    return researcher.as_tool(tool_name="Researcher", tool_description=research_tool())


class Trader:
    """
    Classe que representa um Trader Autônomo.
    
    OBJETIVO DA CLASSE:
    Encapsula um agente de IA que toma decisões de investimento de forma autônoma.
    Cada trader tem sua própria conta, estratégia e pode usar diferentes modelos de IA.
    
    COMO SE RELACIONA COM O PROJETO:
    - Criado em trading_floor.py: trading_floor cria 4 instâncias (Warren, George, Ray, Cathie)
    - Executado periodicamente: trading_floor chama trader.run() a cada N minutos
    - Usa servidores MCP: Acessa contas, mercado, pesquisa através de servidores MCP
    - Integra com accounts.py: Gerencia conta através de Accounts Server MCP
    - Eventos capturados: Tracing salva eventos no banco para UI exibir
    
    ARQUITETURA:
    - Trader contém um Agent (agente de IA principal)
    - Agent tem acesso a ferramentas (Researcher, Accounts Server, Market Server)
    - Agent recebe instruções personalizadas baseadas no nome do trader
    - Agent executa ciclo: pesquisa → análise → decisão → trade
    
    CICLO DE EXECUÇÃO:
    1. Trader.run() é chamado
    2. Inicia servidores MCP (Accounts, Push, Market para trader; Fetch, Brave, Memory para researcher)
    3. Cria agente com instruções e ferramentas
    4. Obtém estado atual da conta e estratégia
    5. Envia mensagem para agente (trade ou rebalance)
    6. Agente executa: pesquisa → análise → decisão → executa trade
    7. Eventos são capturados via tracing
    8. Alterna entre modo trade e rebalance para próxima execução
    """
    
    def __init__(self, name: str, lastname="Trader", model_name="gpt-4o-mini"):
        """
        Inicializa uma instância de Trader.
        
        OBJETIVO:
        Cria um trader com nome, identidade/estratégia e modelo de IA específicos.
        
        PARÂMETROS:
            name (str): Nome do trader (ex: "Warren", "George", "Ray", "Cathie")
                        Usado para identificar conta, estratégia e memória do trader
            lastname (str): Identidade/estratégia do trader (ex: "Patience", "Bold", "Systematic", "Crypto")
                           Descreve a estratégia de investimento do trader
            model_name (str): Nome do modelo de IA a usar (ex: "gpt-4o-mini", "deepseek-chat")
                             Pode ser diferente para cada trader se USE_MANY_MODELS=True
        
        ATRIBUTOS:
            name: Nome do trader (usado para identificar conta no banco de dados)
            lastname: Identidade/estratégia do trader
            agent: Agente de IA (criado quando necessário, None inicialmente)
            model_name: Modelo de IA a usar
            do_trade: Flag que alterna entre modo trade (True) e rebalance (False)
        
        COMO SE RELACIONA COM O PROJETO:
        - name é usado para carregar conta do banco (Account.get(name))
        - name é usado para carregar estratégia (read_strategy_resource(name))
        - name é usado para criar memória isolada do researcher (researcher_mcp_server_params(name))
        - lastname aparece na UI para identificar estratégia do trader
        - model_name permite usar diferentes modelos para diferentes traders
        """
        self.name = name  # Nome do trader (ex: "Warren")
        self.lastname = lastname  # Identidade/estratégia (ex: "Patience")
        self.agent = None  # Agente de IA (criado quando necessário)
        self.model_name = model_name  # Modelo de IA a usar
        self.do_trade = True  # True = modo trade, False = modo rebalance (alterna a cada execução)

    async def create_agent(self, trader_mcp_servers, researcher_mcp_servers) -> Agent:
        """
        Cria o agente de IA principal do trader.
        
        OBJETIVO:
        Instancia o agente de IA que tomará decisões de investimento. O agente recebe
        instruções personalizadas, modelo de IA, ferramentas e acesso a servidores MCP.
        
        COMO SE RELACIONA COM O PROJETO:
        - Instruções personalizadas: trader_instructions(self.name) define comportamento único
          para cada trader (Warren = paciência, George = agressivo, etc.)
        - Researcher como ferramenta: Trader pode chamar Researcher quando precisa pesquisar
        - Servidores MCP do trader: Accounts, Push Notification, Market Data
        - Servidores MCP do researcher: Fetch, Brave Search, Memory (passados para criar Researcher)
        
        PROCESSO:
        1. Cria Researcher como ferramenta (usa researcher_mcp_servers)
        2. Cria Agent principal com:
           - Nome do trader
           - Instruções personalizadas (definem estratégia e comportamento)
           - Modelo de IA (pode ser diferente por trader)
           - Ferramentas: [Researcher] (trader pode pesquisar quando necessário)
           - Servidores MCP: trader_mcp_servers (Accounts, Push, Market)
        
        PARÂMETROS:
            trader_mcp_servers: Lista de servidores MCP para o trader (Accounts, Push, Market)
            researcher_mcp_servers: Lista de servidores MCP para o researcher (Fetch, Brave, Memory)
        
        RETORNA:
            Agent: Agente de IA configurado e pronto para executar
        
        FERRAMENTAS DISPONÍVEIS PARA O AGENTE:
        - Researcher: Pesquisa informações sobre ações e mercado
        - Accounts Server (via MCP): Ver saldo, fazer trades, ver histórico
        - Market Server (via MCP): Obter dados de mercado, preços, histórico
        - Push Notification Server (via MCP): Enviar notificações sobre trades
        """
        # Cria Researcher como ferramenta que o trader pode usar
        # Researcher tem acesso a Fetch, Brave Search e Memory
        tool = await get_researcher_tool(researcher_mcp_servers, self.model_name)
        
        # Cria agente principal do trader
        self.agent = Agent(
            name=self.name,  # Nome do trader (ex: "Warren")
            instructions=trader_instructions(self.name),  # Instruções personalizadas baseadas no nome
            model=get_model(self.model_name),  # Modelo de IA (pode variar por trader)
            tools=[tool],  # Lista de ferramentas: [Researcher]
            mcp_servers=trader_mcp_servers,  # Servidores MCP: Accounts, Push, Market
        )
        return self.agent

    async def get_account_report(self) -> str:
        """
        Obtém relatório da conta do trader em formato JSON.
        
        OBJETIVO:
        Recupera estado atual da conta do trader (saldo, holdings, transações) e retorna
        como JSON para ser incluído na mensagem enviada ao agente.
        
        COMO SE RELACIONA COM O PROJETO:
        - Usa accounts_client.py: read_accounts_resource() lê dados via Accounts Server MCP
        - Dados vêm do banco de dados: Accounts Server lê de accounts.db
        - Usado em run_agent(): Incluído na mensagem para o agente tomar decisões informadas
        - Remove portfolio_value_time_series: Dados históricos são muito grandes, não necessários
          para decisão imediata (agente não precisa de todo histórico, apenas estado atual)
        
        PROCESSO:
        1. Chama Accounts Server MCP para ler dados da conta
        2. Converte resposta (string JSON) para dicionário Python
        3. Remove portfolio_value_time_series (dados históricos grandes)
        4. Converte de volta para JSON (string)
        
        RETORNA:
            str: JSON com dados da conta (saldo, holdings, transações recentes, etc.)
        
        EXEMPLO DE DADOS RETORNADOS:
        {
            "name": "Warren",
            "balance": 100000.0,
            "holdings": {"AAPL": 10, "MSFT": 5},
            "transactions": [...],
            "strategy": "..."
        }
        """
        # Lê dados da conta via Accounts Server MCP
        # read_accounts_resource() faz chamada ao servidor MCP que lê do banco de dados
        account = await read_accounts_resource(self.name)
        
        # Converte string JSON para dicionário Python
        account_json = json.loads(account)
        
        # Remove portfolio_value_time_series (dados históricos grandes)
        # Não é necessário para decisão imediata e tornaria a mensagem muito grande
        account_json.pop("portfolio_value_time_series", None)
        
        # Converte de volta para JSON (string) para incluir na mensagem
        return json.dumps(account_json)

    async def run_agent(self, trader_mcp_servers, researcher_mcp_servers):
        """
        Executa o ciclo completo de trading do agente.
        
        OBJETIVO:
        Orquestra a execução de um ciclo completo de trading: cria agente, obtém dados,
        envia mensagem e executa o agente para tomar decisões e executar trades.
        
        COMO SE RELACIONA COM O PROJETO:
        - Chamado por run_with_mcp_servers() após servidores MCP estarem iniciados
        - Usa accounts_client.py: Para obter dados da conta e estratégia
        - Usa templates.py: Para criar mensagem apropriada (trade ou rebalance)
        - Usa framework agents: Runner.run() executa o agente
        - Agente usa servidores MCP: Para pesquisar, verificar mercado, executar trades
        
        PROCESSO:
        1. Cria agente com servidores MCP configurados
        2. Obtém estado atual da conta (saldo, holdings, etc.)
        3. Obtém estratégia do trader (definida em accounts.py)
        4. Cria mensagem apropriada (trade ou rebalance) com dados da conta e estratégia
        5. Executa agente com a mensagem
        6. Agente executa: pesquisa → análise → decisão → trade (via Accounts Server)
        
        MODOS DE OPERAÇÃO:
        - do_trade=True: Modo trading normal (pesquisa e faz trades)
        - do_trade=False: Modo rebalance (reavalia portfólio e rebalanceia)
        
        Alternância automática:
        - Após cada execução, do_trade alterna (True → False → True → ...)
        - Permite que trader faça trades em uma execução e rebalanceie na próxima
        
        PARÂMETROS:
            trader_mcp_servers: Servidores MCP para o trader (Accounts, Push, Market)
            researcher_mcp_servers: Servidores MCP para o researcher (Fetch, Brave, Memory)
        """
        # 1. Cria agente de IA com servidores MCP configurados
        # Agente tem acesso a: Researcher (ferramenta), Accounts Server, Market Server, Push Server
        self.agent = await self.create_agent(trader_mcp_servers, researcher_mcp_servers)
        
        # 2. Obtém estado atual da conta (saldo, holdings, transações)
        # Dados vêm do banco de dados via Accounts Server MCP
        account = await self.get_account_report()
        
        # 3. Obtém estratégia do trader (definida em accounts.py)
        # Estratégia descreve filosofia de investimento do trader
        strategy = await read_strategy_resource(self.name)
        
        # 4. Cria mensagem apropriada baseada no modo de operação
        # trade_message: Instrui agente a pesquisar e fazer trades
        # rebalance_message: Instrui agente a reavaliar e rebalancear portfólio
        message = (
            trade_message(self.name, strategy, account)  # Modo trade
            if self.do_trade
            else rebalance_message(self.name, strategy, account)  # Modo rebalance
        )
        
        # 5. Executa agente com a mensagem
        # Runner.run() inicia ciclo de conversa: agente recebe mensagem, decide ações,
        # usa ferramentas (Researcher, Accounts Server), toma decisões, executa trades
        # max_turns limita número de interações para evitar loops infinitos
        await Runner.run(self.agent, message, max_turns=MAX_TURNS)

    async def run_with_mcp_servers(self):
        """
        Inicia servidores MCP e executa o agente trader.
        
        OBJETIVO:
        Gerencia o ciclo de vida dos servidores MCP (inicia e fecha automaticamente)
        e executa o agente trader com acesso a esses servidores.
        
        COMO SE RELACIONA COM O PROJETO:
        - Usa mcp_params.py: trader_mcp_server_params e researcher_mcp_server_params
          definem quais servidores iniciar e como configurá-los
        - Servidores são processos separados: Cada servidor MCP roda como processo independente
        - AsyncExitStack garante limpeza: Servidores são fechados automaticamente ao terminar
        - Comunicação via stdio: Agente se comunica com servidores via entrada/saída padrão
        
        SERVIDORES MCP DO TRADER (trader_mcp_server_params):
        1. Accounts Server: Gerencia contas, saldos, trades
        2. Push Notification Server: Envia notificações sobre eventos
        3. Market Server: Fornece dados de mercado (preços, histórico)
        
        SERVIDORES MCP DO RESEARCHER (researcher_mcp_server_params):
        1. Fetch Server: Busca conteúdo de páginas web
        2. Brave Search Server: Pesquisa informações na web
        3. Memory Server: Armazena memória persistente (banco único por trader)
        
        PROCESSO:
        1. Inicia servidores MCP do trader (Accounts, Push, Market)
        2. Inicia servidores MCP do researcher (Fetch, Brave, Memory)
        3. Executa agente com acesso a todos os servidores
        4. Ao terminar, AsyncExitStack fecha todos os servidores automaticamente
        
        GESTÃO DE RECURSOS:
        - AsyncExitStack garante que servidores sejam fechados mesmo se houver erro
        - client_session_timeout_seconds=120: Timeout de 2 minutos para sessões MCP
        - Servidores são processos separados, gerenciados automaticamente pelo framework
        
        NOTA SOBRE AsyncExitStack:
        - Garante que recursos sejam liberados corretamente
        - Similar a "with" statement, mas para múltiplos recursos assíncronos
        - Se houver erro, todos os servidores são fechados automaticamente
        """
        # AsyncExitStack gerencia múltiplos context managers assíncronos
        # Garante que servidores sejam fechados automaticamente ao sair do bloco
        async with AsyncExitStack() as stack:
            # Inicia servidores MCP do trader
            # trader_mcp_server_params vem de mcp_params.py
            # Cada servidor é um processo separado executado via 'uv run' ou 'npx'
            trader_mcp_servers = [
                await stack.enter_async_context(
                    MCPServerStdio(params, client_session_timeout_seconds=120)
                )
                for params in trader_mcp_server_params
            ]
            
            # Inicia servidores MCP do researcher
            # researcher_mcp_server_params(self.name) cria servidores específicos para este trader
            # Cada trader tem seu próprio Memory Server (banco isolado)
            async with AsyncExitStack() as stack:
                researcher_mcp_servers = [
                    await stack.enter_async_context(
                        MCPServerStdio(params, client_session_timeout_seconds=120)
                    )
                    for params in researcher_mcp_server_params(self.name)
                ]
                
                # Executa agente com acesso a todos os servidores MCP
                # Agente pode usar ferramentas de todos os servidores iniciados
                await self.run_agent(trader_mcp_servers, researcher_mcp_servers)

    async def run_with_trace(self):
        """
        Executa trader com sistema de tracing ativado.
        
        OBJETIVO:
        Envolve a execução do trader com sistema de tracing para capturar todos os eventos
        (pesquisas, decisões, trades) e salvá-los no banco de dados para visualização na UI.
        
        COMO SE RELACIONA COM O PROJETO:
        - Usa tracers.py: make_trace_id() cria ID único para o trace
        - Usa framework agents: trace() captura eventos do agente
        - Eventos salvos no banco: LogTracer (em trading_floor.py) salva eventos em logs
        - UI lê eventos: app.py lê logs do banco e exibe em tempo real
        
        O QUE É CAPTURADO:
        - Todas as chamadas de ferramentas (Researcher, Accounts Server, etc.)
        - Mensagens do agente (raciocínio, decisões)
        - Respostas dos servidores MCP
        - Trades executados
        - Erros e exceções
        
        TRACE ID:
        - ID único por trader: Permite rastrear eventos de um trader específico
        - Formato: baseado no nome do trader (ex: "warren-trading-20241205-143022")
        - Usado para agrupar eventos relacionados na UI
        
        TRACE NAME:
        - Identifica tipo de execução: "trading" ou "rebalancing"
        - Útil para filtrar eventos na UI
        - Diferencia entre ciclos de trade e rebalance
        
        PROCESSO:
        1. Cria nome do trace baseado no modo (trading ou rebalancing)
        2. Gera ID único do trace
        3. Ativa tracing com trace()
        4. Executa trader (todos os eventos são capturados)
        5. Tracing salva eventos no banco automaticamente
        """
        # Cria nome do trace baseado no modo de operação
        # "Warren-trading" ou "Warren-rebalancing"
        trace_name = f"{self.name}-trading" if self.do_trade else f"{self.name}-rebalancing"
        
        # Gera ID único para este trace
        # Formato: "warren-20241205-143022" (nome-data-hora)
        trace_id = make_trace_id(f"{self.name.lower()}")
        
        # Ativa tracing: todos os eventos dentro deste bloco são capturados
        # Eventos são salvos no banco de dados via LogTracer (configurado em trading_floor.py)
        with trace(trace_name, trace_id=trace_id):
            await self.run_with_mcp_servers()

    async def run(self):
        """
        Método principal de execução do trader (ponto de entrada).
        
        OBJETIVO:
        Método principal chamado por trading_floor.py para executar um ciclo completo
        do trader. Gerencia erros e alterna modo de operação para próxima execução.
        
        COMO SE RELACIONA COM O PROJETO:
        - Chamado por trading_floor.py: trading_floor chama trader.run() para cada trader
        - Executado em paralelo: trading_floor usa asyncio.gather() para executar
          todos os traders simultaneamente
        - Resiliente a erros: Se um trader falhar, outros continuam executando
        - Alterna modo automaticamente: Prepara trader para próxima execução
        
        FLUXO DE EXECUÇÃO:
        1. trading_floor.py chama trader.run() para cada trader
        2. run() chama run_with_trace()
        3. run_with_trace() chama run_with_mcp_servers()
        4. run_with_mcp_servers() inicia servidores MCP e chama run_agent()
        5. run_agent() cria agente, obtém dados e executa ciclo de trading
        6. Agente pesquisa, analisa, decide e executa trades
        7. Eventos são capturados via tracing
        8. Ao terminar, alterna modo (trade ↔ rebalance)
        
        TRATAMENTO DE ERROS:
        - Try/except captura qualquer erro durante execução
        - Erro não interrompe outros traders (execução paralela)
        - Erro é impresso mas não propaga (trader continua funcionando)
        - Servidores MCP são fechados automaticamente mesmo em caso de erro
        
        ALTERNÂNCIA DE MODO:
        - do_trade alterna após cada execução (True ↔ False)
        - Permite que trader faça trades em uma execução e rebalanceie na próxima
        - Diversifica comportamento do trader ao longo do tempo
        
        EXEMPLO DE USO:
        # Em trading_floor.py:
        traders = [Trader("Warren", "Patience"), ...]
        await asyncio.gather(*[trader.run() for trader in traders])
        # Todos os traders executam em paralelo
        """
        try:
            # Executa trader com tracing ativado
            # Todos os eventos são capturados e salvos no banco de dados
            await self.run_with_trace()
        except Exception as e:
            # Captura erros para não interromper outros traders
            # Em execução paralela, erro em um trader não afeta os outros
            print(f"Error running trader {self.name}: {e}")
        
        # Alterna modo de operação para próxima execução
        # True → False (trade → rebalance) ou False → True (rebalance → trade)
        # Permite diversificar comportamento do trader
        self.do_trade = not self.do_trade
