"""
Módulo de Configuração de Parâmetros MCP (Model Context Protocol)

OBJETIVO DO MÓDULO:
Este módulo centraliza toda a configuração dos servidores MCP usados pelos traders autônomos.
Ele define quais servidores MCP cada trader e pesquisador (researcher) deve usar, e como
esses servidores devem ser executados.

COMO SE CONECTA COM O PROJETO:
1. Importado em traders.py: Usado para configurar os servidores MCP de cada trader
2. Define servidores para Traders: Accounts, Push Notification, Market Data
3. Define servidores para Researchers: Fetch, Brave Search, Memory
4. Configura PYTHONPATH: Permite que servidores Python locais importem módulos 'src'

ARQUITETURA:
- Traders usam servidores MCP para: gerenciar contas, receber notificações, obter dados de mercado
- Researchers usam servidores MCP para: buscar informações na web, pesquisar, armazenar memória
- Cada trader tem seu próprio pesquisador com memória isolada
"""

import os
from dotenv import load_dotenv
from src.core.market import is_paid_polygon, is_realtime_polygon

# Carrega variáveis de ambiente do arquivo .env
# override=True garante que valores do .env sobrescrevem variáveis já existentes
# Isso é importante para garantir que as chaves de API sejam carregadas corretamente
load_dotenv(override=True)

# ============================================================================
# CONFIGURAÇÃO DO PYTHONPATH
# ============================================================================
# Objetivo: Configurar PYTHONPATH para que servidores MCP Python locais possam
# importar módulos do projeto usando 'from src.core...'
#
# Por que é necessário:
# - Servidores MCP são executados como processos separados via 'uv run'
# - Esses processos não têm acesso automático aos módulos do projeto
# - PYTHONPATH precisa apontar para a raiz do projeto para imports funcionarem
#
# Como funciona:
# 1. Calcula o diretório raiz do projeto (3 níveis acima deste arquivo)
# 2. Adiciona ao PYTHONPATH, preservando qualquer PYTHONPATH existente
# 3. Servidores MCP Python recebem esse PYTHONPATH no ambiente

import pathlib
# Calcula caminho do diretório raiz do projeto
# __file__ = src/utils/mcp_params.py
# .parent = src/utils/
# .parent.parent = src/
# .parent.parent.parent = traders/ (raiz do projeto)
project_root = pathlib.Path(__file__).parent.parent.parent
project_root_str = str(project_root)

# Configura PYTHONPATH para que os servidores MCP possam importar módulos 'src'
# Preserva PYTHONPATH existente se houver (pode ser configurado externamente)
existing_pythonpath = os.environ.get("PYTHONPATH", "")
if existing_pythonpath:
    # Se já existe PYTHONPATH, adiciona o projeto no início
    # Ordem importa: Python procura nos diretórios na ordem do PATH
    pythonpath = f"{project_root_str}:{existing_pythonpath}"
else:
    # Se não existe, usa apenas o diretório raiz do projeto
    pythonpath = project_root_str

# ============================================================================
# CONFIGURAÇÃO DE CHAVES DE API
# ============================================================================
# Objetivo: Carregar chaves de API necessárias para servidores MCP externos
#
# Brave Search API:
# - Usado pelo servidor Brave Search para pesquisas na web
# - Cada trader usa pesquisas para tomar decisões de investimento
#
# Polygon API:
# - Usado para dados de mercado (quando plano pago ou realtime)
# - Permite acesso a dados históricos e em tempo real de ações

# Chave da API Brave Search (para pesquisas web)
# Usada pelo servidor @modelcontextprotocol/server-brave-search
brave_env = {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")}

# Chave da API Polygon (para dados de mercado)
# Usada quando o plano Polygon é pago ou realtime
polygon_api_key = os.getenv("POLYGON_API_KEY")

# ============================================================================
# AMBIENTE BASE PARA SERVIDORES MCP PYTHON LOCAIS
# ============================================================================
# Objetivo: Criar ambiente padrão para servidores MCP Python desenvolvidos localmente
#
# Servidores Python locais (accounts_server, push_server, market_server):
# - São executados via 'uv run' como processos separados
# - Precisam de PYTHONPATH para importar módulos 'from src.core...'
# - Este ambiente é copiado para cada servidor (usando .copy())
#
# Por que copiar (.copy()):
# - Cada servidor pode precisar de variáveis de ambiente adicionais
# - Copiar evita modificar o ambiente base acidentalmente
# - Permite customização individual por servidor

# Ambiente base para servidores MCP Python locais
# Inclui PYTHONPATH para permitir imports 'from src.core...'
mcp_python_env = {"PYTHONPATH": pythonpath}

# ============================================================================
# SERVIDOR MCP DE DADOS DE MERCADO (Market Data)
# ============================================================================
# Objetivo: Configurar servidor MCP que fornece dados de mercado para os traders
#
# Dois modos de operação:
# 1. Servidor externo (Polygon oficial): Quando plano é pago ou realtime
# 2. Servidor local (market_server.py): Quando plano é gratuito (usa dados simulados)
#
# Como funciona no projeto:
# - Traders precisam de dados de mercado para tomar decisões de investimento
# - Servidor fornece informações sobre preços, volumes, histórico de ações
# - Cada trader consulta este servidor antes de fazer trades
#
# Integração:
# - Usado por todos os 4 traders (Warren, George, Ray, Cathie)
# - Parte da lista trader_mcp_server_params
# - Importado em traders.py para configurar agentes

# Verifica se deve usar servidor Polygon oficial ou servidor local
if is_paid_polygon or is_realtime_polygon:
    # MODO 1: Servidor Polygon oficial (plano pago ou realtime)
    # Objetivo: Usar servidor oficial da Polygon com dados reais e completos
    #
    # Como funciona:
    # - uvx: Executa pacote Python diretamente do GitHub
    # - Instala automaticamente se não estiver instalado
    # - Fornece acesso completo à API Polygon
    #
    # Vantagens:
    # - Dados reais e atualizados
    # - Acesso a mais funcionalidades da API
    # - Suporte oficial da Polygon
    market_mcp = {
        "command": "uvx",  # Executa pacote Python do GitHub
        "args": ["--from", "git+https://github.com/polygon-io/mcp_polygon@v0.1.0", "mcp_polygon"],
        "env": {"POLYGON_API_KEY": polygon_api_key},  # Chave de API necessária
    }
else:
    # MODO 2: Servidor local (plano gratuito)
    # Objetivo: Usar servidor desenvolvido localmente com dados simulados/limitados
    #
    # Como funciona:
    # - market_server.py: Servidor MCP desenvolvido no projeto
    # - Executado via 'uv run' com PYTHONPATH configurado
    # - Fornece dados simulados ou limitados (dependendo da implementação)
    #
    # Vantagens:
    # - Não requer plano pago
    # - Pode ser customizado para necessidades específicas
    # - Funciona offline (com dados simulados)
    #
    # Caminho absoluto garante que funciona independente do diretório de execução
    market_server_path = project_root / "src" / "core" / "market_server.py"
    
    # Adiciona PYTHONPATH ao ambiente para permitir imports 'from src.core...'
    # market_server.py precisa importar módulos do projeto
    market_env = mcp_python_env.copy()
    
    market_mcp = {
        "command": "uv",  # Usa uv para executar servidor Python local
        "args": ["run", str(market_server_path)],  # Executa market_server.py
        "env": market_env,  # Inclui PYTHONPATH para imports funcionarem
    }


# ============================================================================
# CONFIGURAÇÃO DE SERVIDORES MCP PARA TRADERS
# ============================================================================
# Objetivo: Definir lista completa de servidores MCP que cada trader usa
#
# Servidores incluídos:
# 1. Accounts Server: Gerencia contas e saldos dos traders
# 2. Push Notification Server: Envia notificações sobre trades e eventos
# 3. Market Server: Fornece dados de mercado (configurado acima)
#
# Como funciona no projeto:
# - Cada trader (Warren, George, Ray, Cathie) usa estes 3 servidores
# - Servidores são executados como processos separados
# - Traders se comunicam com servidores via protocolo MCP
#
# Integração:
# - Importado em traders.py: from src.utils.mcp_params import trader_mcp_server_params
# - Usado ao criar instâncias de Trader em traders.py
# - Cada trader recebe acesso a todas as ferramentas desses servidores
#
# Fluxo de uso:
# 1. Trader precisa verificar saldo → usa Accounts Server
# 2. Trader quer fazer trade → usa Accounts Server para debitar/créditar
# 3. Trader precisa de dados de mercado → usa Market Server
# 4. Sistema quer notificar sobre trade → usa Push Notification Server

# Caminhos absolutos para servidores MCP Python locais
# Usa caminhos absolutos para garantir funcionamento independente do diretório de execução
accounts_server_path = project_root / "src" / "core" / "accounts_server.py"
push_server_path = project_root / "src" / "core" / "push_server.py"

# Lista completa de servidores MCP para traders
# Esta lista é importada em traders.py e usada ao criar agentes Trader
# Cada servidor é executado como processo separado e fornece ferramentas via MCP
trader_mcp_server_params = [
    # 1. Accounts Server: Gerencia contas e operações financeiras
    # Objetivo: Permitir que traders gerenciem suas contas, saldos e histórico de trades
    #
    # Funcionalidades fornecidas:
    # - Ver saldo da conta
    # - Fazer trades (comprar/vender ações)
    # - Ver histórico de trades
    # - Ver posições atuais
    #
    # Como é usado:
    # - Trader consulta saldo antes de fazer trade
    # - Trader executa trade através deste servidor
    # - Sistema registra todas as operações no banco de dados
    {
        "command": "uv",  # Executa servidor Python local via uv
        "args": ["run", str(accounts_server_path)],  # Executa accounts_server.py
        "env": mcp_python_env.copy(),  # Inclui PYTHONPATH para imports 'from src.core...'
    },
    
    # 2. Push Notification Server: Envia notificações sobre eventos
    # Objetivo: Notificar sobre trades executados, mudanças de mercado, etc.
    #
    # Funcionalidades fornecidas:
    # - Enviar notificações push
    # - Registrar eventos importantes
    #
    # Como é usado:
    # - Sistema notifica quando trader executa trade
    # - Notificações aparecem na UI em tempo real
    # - Permite monitoramento ativo do trading floor
    {
        "command": "uv",  # Executa servidor Python local via uv
        "args": ["run", str(push_server_path)],  # Executa push_server.py
        "env": mcp_python_env.copy(),  # Inclui PYTHONPATH para imports 'from src.core...'
    },
    
    # 3. Market Server: Fornece dados de mercado
    # Objetivo: Fornecer informações sobre preços, volumes e histórico de ações
    #
    # Configuração:
    # - Pode ser servidor externo (Polygon oficial) ou local (market_server.py)
    # - Definido acima baseado no plano Polygon (is_paid_polygon ou is_realtime_polygon)
    #
    # Funcionalidades fornecidas:
    # - Obter preços atuais de ações
    # - Ver histórico de preços
    # - Obter dados de volume
    #
    # Como é usado:
    # - Trader consulta preços antes de decidir comprar/vender
    # - Trader analisa histórico para tomar decisões
    # - Dados são essenciais para estratégias de investimento
    market_mcp,  # Configurado acima (servidor externo ou local)
]

# ============================================================================
# CONFIGURAÇÃO DE SERVIDORES MCP PARA RESEARCHERS (PESQUISADORES)
# ============================================================================
# Objetivo: Definir servidores MCP usados pelos pesquisadores (researchers) dos traders
#
# Diferença entre Traders e Researchers:
# - Traders: Agentes que tomam decisões de investimento e executam trades
# - Researchers: Agentes auxiliares que pesquisam informações para ajudar traders
#
# Arquitetura:
# - Cada trader tem seu próprio pesquisador (researcher)
# - Researcher pesquisa informações antes do trader tomar decisão
# - Researcher tem memória isolada (banco de dados único por trader)
#
# Servidores incluídos:
# 1. Fetch Server: Busca conteúdo de páginas web
# 2. Brave Search Server: Pesquisa na web usando Brave Search API
# 3. Memory Server: Armazena memória persistente (cada trader tem seu próprio banco)
#
# Como funciona no projeto:
# - Trader precisa pesquisar sobre uma ação → usa Researcher
# - Researcher usa Fetch para ler páginas web específicas
# - Researcher usa Brave Search para encontrar informações relevantes
# - Researcher salva informações importantes na Memory para uso futuro
# - Trader usa informações pesquisadas para tomar decisão de investimento
#
# Integração:
# - Importado em traders.py: from src.utils.mcp_params import researcher_mcp_server_params
# - Chamado ao criar Researcher para cada trader em traders.py
# - Cada trader (Warren, George, Ray, Cathie) tem seu próprio pesquisador com memória isolada


def researcher_mcp_server_params(name: str):
    """
    Retorna configuração dos servidores MCP para o pesquisador (researcher) de um trader.
    
    OBJETIVO:
    Configurar os servidores MCP que o pesquisador usa para buscar informações e armazenar
    memória. Cada trader tem seu próprio pesquisador com memória isolada.
    
    PARÂMETROS:
        name (str): Nome do trader (ex: "Warren", "George", "Ray", "Cathie")
                    Usado para criar banco de memória único por trader
                    Exemplo: "Warren" → data/memory/Warren.db
    
    RETORNA:
        list: Lista de dicionários, cada um configurando um servidor MCP
              Formato: [{"command": "...", "args": [...], "env": {...}}, ...]
    
    SERVIDORES RETORNADOS:
    1. Fetch Server (mcp-server-fetch):
       - Objetivo: Buscar conteúdo de páginas web específicas
       - Como funciona: Recebe URL, retorna conteúdo HTML/texto da página
       - Uso: Researcher busca páginas de notícias, análises, relatórios sobre ações
       - Execução: Via uvx (executa pacote Python do PyPI)
    
    2. Brave Search Server (@modelcontextprotocol/server-brave-search):
       - Objetivo: Pesquisar informações na web usando Brave Search API
       - Como funciona: Recebe query de pesquisa, retorna resultados relevantes
       - Uso: Researcher pesquisa sobre empresas, ações, tendências de mercado
       - Execução: Via npx (executa pacote Node.js do npm)
       - Requer: BRAVE_API_KEY no ambiente
    
    3. Memory Server (mcp-memory-libsql):
       - Objetivo: Armazenar memória persistente do pesquisador
       - Como funciona: Banco de dados libSQL (SQLite) que persiste entre execuções
       - Uso: Researcher salva informações importantes para consultar depois
       - Execução: Via npx (executa pacote Node.js do npm)
       - Isolamento: Cada trader tem seu próprio banco (Warren.db, George.db, etc.)
       - Localização: data/memory/{name}.db (caminho absoluto)
    
    EXEMPLO DE USO:
        # Em traders.py:
        researcher_servers = researcher_mcp_server_params("Warren")
        # Cria pesquisador para Warren com seus próprios servidores MCP
        # Warren terá seu próprio banco de memória em data/memory/Warren.db
    
    FLUXO DE TRABALHO:
        1. Trader precisa pesquisar sobre ação "AAPL"
        2. Researcher usa Brave Search para encontrar artigos relevantes
        3. Researcher usa Fetch para ler conteúdo de páginas importantes
        4. Researcher salva insights na Memory para consultas futuras
        5. Trader usa informações pesquisadas para decidir se compra/vende AAPL
    
    ISOLAMENTO DE MEMÓRIA:
        - Warren.db: Memória do pesquisador de Warren
        - George.db: Memória do pesquisador de George
        - Ray.db: Memória do pesquisador de Ray
        - Cathie.db: Memória do pesquisador de Cathie
        - Cada trader não vê memória dos outros (isolamento completo)
    """
    # Caminho absoluto para o banco de memória do trader
    # Usa caminho absoluto para garantir que funciona mesmo quando npx executa de outro diretório
    # Formato: /home/francisco/projects/agents/6_mcp/traders/data/memory/{name}.db
    # Exemplo: /home/francisco/projects/agents/6_mcp/traders/data/memory/Warren.db
    memory_db_path = project_root / "data" / "memory" / f"{name}.db"
    
    # URL do banco de dados no formato esperado pelo servidor libSQL
    # Formato: file:/caminho/absoluto/para/banco.db
    memory_db_url = f"file:{memory_db_path}"
    
    return [
        # 1. Fetch Server: Busca conteúdo de páginas web
        # Objetivo: Permitir que researcher leia conteúdo de URLs específicas
        #
        # Como funciona:
        # - Researcher recebe URL de artigo/notícia sobre ação
        # - Fetch Server baixa e retorna conteúdo da página
        # - Researcher analisa conteúdo para extrair informações relevantes
        #
        # Exemplo de uso:
        # - Researcher encontra artigo sobre Apple no Brave Search
        # - Usa Fetch para ler conteúdo completo do artigo
        # - Extrai informações sobre performance, análise, previsões
        {"command": "uvx", "args": ["mcp-server-fetch"]},
        
        # 2. Brave Search Server: Pesquisa na web
        # Objetivo: Permitir que researcher encontre informações relevantes na web
        #
        # Como funciona:
        # - Researcher faz query de pesquisa (ex: "Apple stock analysis 2024")
        # - Brave Search retorna resultados relevantes com URLs
        # - Researcher pode então usar Fetch para ler conteúdo das páginas
        #
        # Exemplo de uso:
        # - Trader quer pesquisar sobre ação "TSLA"
        # - Researcher pesquisa "Tesla stock news analysis"
        # - Recebe lista de artigos relevantes
        # - Usa Fetch para ler artigos mais importantes
        {
            "command": "npx",  # Executa pacote Node.js via npm
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],  # -y instala automaticamente
            "env": brave_env,  # Inclui BRAVE_API_KEY necessária para API
        },
        
        # 3. Memory Server: Memória persistente
        # Objetivo: Armazenar informações importantes para consultas futuras
        #
        # Como funciona:
        # - Researcher salva insights, fatos, análises na memória
        # - Em pesquisas futuras, pode consultar memória antes de buscar na web
        # - Cada trader tem seu próprio banco (isolamento completo)
        #
        # Exemplo de uso:
        # - Researcher descobre que Apple lançou novo produto
        # - Salva na memória: "Apple launched new product X on date Y"
        # - Em pesquisa futura sobre Apple, consulta memória primeiro
        # - Evita pesquisas redundantes e acelera processo
        #
        # Isolamento:
        # - Warren não vê memória de George, Ray ou Cathie
        # - Cada trader desenvolve sua própria base de conhecimento
        # - Permite estratégias diferentes baseadas em memórias diferentes
        {
            "command": "npx",  # Executa pacote Node.js via npm
            "args": ["-y", "mcp-memory-libsql"],  # -y instala automaticamente
            "env": {"LIBSQL_URL": memory_db_url},  # URL do banco de dados único do trader
        },
    ]
