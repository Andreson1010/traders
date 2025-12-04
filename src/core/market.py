"""
Módulo de obtenção de dados de mercado usando Polygon.io API.

Este módulo fornece funções para obter preços de ações e status do mercado,
com suporte para diferentes planos da API Polygon (gratuito, pago, tempo real)
e sistema de cache para otimizar chamadas à API.

Objetivo: Fornecer interface unificada para obter preços de ações, abstraindo
detalhes da API Polygon e implementando cache para reduzir chamadas e custos.

Características:
- Suporte a múltiplos planos Polygon (gratuito, pago, tempo real)
- Sistema de cache usando database.py para evitar chamadas excessivas
- Fallback para valores aleatórios se API falhar
- Verificação de status do mercado (aberto/fechado)
- Otimização com LRU cache para melhor performance

Relacionamento:
- Usado por accounts.py para obter preços ao comprar/vender ações
- Usa database.py para cache de dados de mercado
- Integrado com market_server.py para expor via MCP
"""

from polygon import RESTClient
from dotenv import load_dotenv
import os
from datetime import datetime
import random
from src.core.database import write_market, read_market
from functools import lru_cache
from datetime import timezone

load_dotenv(override=True)

# Configuração da API Polygon
polygon_api_key = os.getenv("POLYGON_API_KEY")
polygon_plan = os.getenv("POLYGON_PLAN")

# Flags para determinar qual método usar baseado no plano
is_paid_polygon = polygon_plan == "paid"  # Plano pago: acesso a dados em tempo real
is_realtime_polygon = polygon_plan == "realtime"  # Plano tempo real: dados mais atualizados


# ============================================================================
# FUNÇÕES DE STATUS DO MERCADO
# ============================================================================

def is_market_open() -> bool:
    """
    Verifica se o mercado de ações está aberto no momento.
    
    Objetivo: Determinar se o mercado está operacional, útil para traders decidirem
    se podem executar trades ou se devem aguardar abertura do mercado.
    
    Retorna:
        - True se mercado estiver aberto
        - False se mercado estiver fechado (finais de semana, feriados, após horário)
    
    Processo:
        1. Cria cliente REST da Polygon
        2. Consulta status do mercado via API
        3. Retorna se mercado == "open"
    
    Uso: Pode ser usado por traders para verificar se podem executar trades ou
    para incluir contexto nas instruções do agente.
    
    Nota: Requer chamada à API a cada verificação. Para otimização, poderia ser
    cachead por alguns minutos.
    """
    client = RESTClient(polygon_api_key)
    market_status = client.get_market_status()
    return market_status.market == "open"


# ============================================================================
# FUNÇÕES DE OBTENÇÃO DE PREÇOS - PLANO GRATUITO (EOD - End of Day)
# ============================================================================

def get_all_share_prices_polygon_eod() -> dict[str, float]:
    """
    Obtém preços de fechamento (EOD - End of Day) de todas as ações negociadas.
    
    Objetivo: Buscar preços de fechamento do último dia útil para todas as ações
    de uma vez, otimizando para plano gratuito que tem limites de chamadas.
    
    Processo:
        1. Usa SPY (S&P 500 ETF) como "probe" para determinar última data de fechamento
        2. Converte timestamp para data UTC (corrigido por estudante Reema R.)
        3. Busca dados agregados diários de todas as ações para essa data
        4. Retorna dicionário {ticker: preço_de_fechamento}
    
    Retorna: Dicionário com todos os tickers e seus preços de fechamento:
        {"AAPL": 150.25, "TSLA": 245.80, "MSFT": 380.50, ...}
    
    Características:
        - adjusted=True: Preços ajustados para splits e dividendos
        - include_otc=False: Exclui ações de balcão (OTC)
        - Útil para plano gratuito: Uma chamada retorna todos os preços
    
    Uso: Chamado por get_market_for_prior_date() quando dados não estão em cache.
    
    Nota: Crédito ao estudante Reema R. por corrigir o problema de timezone.
    """
    client = RESTClient(polygon_api_key)

    # Usa SPY como referência para determinar última data de fechamento
    probe = client.get_previous_close_agg("SPY")[0]
    last_close = datetime.fromtimestamp(probe.timestamp / 1000, tz=timezone.utc).date()

    # Busca dados agregados de todas as ações para a última data de fechamento
    results = client.get_grouped_daily_aggs(last_close, adjusted=True, include_otc=False)
    return {result.ticker: result.close for result in results}


@lru_cache(maxsize=2)
def get_market_for_prior_date(today):
    """
    Obtém dados de mercado para uma data específica, usando cache quando possível.
    
    Objetivo: Implementar sistema de cache inteligente que primeiro verifica banco
    de dados local antes de fazer chamada à API, economizando chamadas e melhorando
    performance.
    
    Parâmetros:
        today: Data no formato string "YYYY-MM-DD" (ex: "2024-11-28")
    
    Processo:
        1. Tenta ler dados do cache (database.py)
        2. Se não encontrar, busca da API Polygon
        3. Salva no cache para uso futuro
        4. Retorna dados (do cache ou recém-buscados)
    
    Decorador @lru_cache:
        - maxsize=2: Mantém apenas 2 datas em cache na memória
        - Acelera chamadas repetidas na mesma execução
        - Complementa cache do banco de dados
    
    Estratégia de cache:
        - Cache em memória (LRU): Para mesma execução
        - Cache em banco (database.py): Para execuções futuras
        - API Polygon: Apenas se não houver cache
    
    Uso: Chamado por get_share_price_polygon_eod() para obter dados de mercado
    com otimização de cache.
    
    Benefícios:
        - Reduz chamadas à API (importante no plano gratuito)
        - Melhora performance (cache local é mais rápido)
        - Funciona offline (usa cache se API estiver indisponível)
    """
    market_data = read_market(today)
    if not market_data:
        market_data = get_all_share_prices_polygon_eod()
        write_market(today, market_data)
    return market_data


def get_share_price_polygon_eod(symbol) -> float:
    """
    Obtém preço de uma ação específica usando dados EOD (End of Day) do plano gratuito.
    
    Objetivo: Fornecer preço de fechamento de uma ação específica, otimizado para
    plano gratuito que usa dados do final do dia anterior.
    
    Parâmetros:
        symbol: Ticker da ação (ex: "AAPL", "TSLA", "MSFT")
    
    Processo:
        1. Obtém data atual
        2. Busca dados de mercado para essa data (com cache)
        3. Retorna preço da ação específica ou 0.0 se não encontrada
    
    Retorna:
        - Preço de fechamento da ação (float)
        - 0.0 se símbolo não for encontrado (ação inválida ou não negociada)
    
    Características:
        - Usa cache: Evita chamadas repetidas à API
        - Dados EOD: Preços do final do último dia útil
        - Adequado para plano gratuito: Economiza chamadas à API
    
    Uso: Chamado por get_share_price_polygon() quando não está em plano pago.
    
    Relacionamento: Usa get_market_for_prior_date() que implementa cache inteligente.
    """
    today = datetime.now().date().strftime("%Y-%m-%d")
    market_data = get_market_for_prior_date(today)
    return market_data.get(symbol, 0.0)


# ============================================================================
# FUNÇÕES DE OBTENÇÃO DE PREÇOS - PLANO PAGO (MIN - Minuto a minuto)
# ============================================================================

def get_share_price_polygon_min(symbol) -> float:
    """
    Obtém preço atual de uma ação usando dados em tempo real do plano pago.
    
    Objetivo: Fornecer preço mais atualizado possível de uma ação, usando dados
    minuto a minuto disponíveis apenas em planos pagos da Polygon.
    
    Parâmetros:
        symbol: Ticker da ação (ex: "AAPL", "TSLA", "MSFT")
    
    Processo:
        1. Obtém snapshot atual da ação via API
        2. Tenta usar preço do minuto atual (result.min.close)
        3. Se não disponível, usa preço do dia anterior (result.prev_day.close)
        4. Retorna preço mais atualizado disponível
    
    Retorna:
        - Preço do minuto atual se mercado estiver aberto
        - Preço de fechamento do dia anterior se mercado fechado
        - 0.0 se ação não encontrada
    
    Características:
        - Dados em tempo real: Atualizado minuto a minuto
        - Fallback inteligente: Usa dia anterior se necessário
        - Requer plano pago: Acesso a dados em tempo real
    
    Uso: Chamado por get_share_price_polygon() quando está em plano pago.
    
    Vantagem sobre EOD: Preços mais atualizados, útil para day trading.
    """
    client = RESTClient(polygon_api_key)
    result = client.get_snapshot_ticker("stocks", symbol)
    return result.min.close or result.prev_day.close


# ============================================================================
# FUNÇÕES DE INTERFACE UNIFICADA
# ============================================================================

def get_share_price_polygon(symbol) -> float:
    """
    Obtém preço de ação usando método apropriado baseado no plano Polygon.
    
    Objetivo: Abstrair diferenças entre planos, escolhendo automaticamente o
    método mais adequado (EOD para gratuito, tempo real para pago).
    
    Parâmetros:
        symbol: Ticker da ação (ex: "AAPL", "TSLA", "MSFT")
    
    Lógica de decisão:
        - Plano pago (paid/realtime): Usa get_share_price_polygon_min() (tempo real)
        - Plano gratuito: Usa get_share_price_polygon_eod() (fechamento do dia)
    
    Retorna: Preço da ação (float)
    
    Uso: Chamado por get_share_price() como camada intermediária que escolhe
    o método baseado no plano configurado.
    
    Benefício: Código que usa get_share_price() não precisa saber qual plano está
    sendo usado - a função escolhe automaticamente o melhor método disponível.
    """
    if is_paid_polygon:
        return get_share_price_polygon_min(symbol)
    else:
        return get_share_price_polygon_eod(symbol)


def get_share_price(symbol) -> float:
    """
    Função principal para obter preço de uma ação com fallback robusto.
    
    Objetivo: Fornecer interface unificada e resiliente para obter preços de ações,
    com tratamento de erros e fallback para valores aleatórios se API falhar.
    Esta é a função que deve ser chamada pelo resto do código.
    
    Parâmetros:
        symbol: Ticker da ação (ex: "AAPL", "TSLA", "MSFT")
    
    Processo:
        1. Verifica se há chave de API configurada
        2. Tenta obter preço via Polygon (método apropriado ao plano)
        3. Se falhar (API offline, erro de rede, etc.), usa valor aleatório
        4. Retorna preço ou valor aleatório como fallback
    
    Retorno:
        - Preço real da ação se API funcionar
        - Valor aleatório entre $1-100 se API falhar (permite continuar simulação)
    
    Tratamento de erros:
        - Captura qualquer exceção da API
        - Imprime mensagem de erro para debugging
        - Retorna valor aleatório para não quebrar simulação
    
    Uso: Chamado por accounts.py em buy_shares() e sell_shares() para obter
    preços de ações antes de executar trades.
    
    Estratégia de fallback:
        - Valor aleatório permite que simulação continue mesmo se API falhar
        - Útil para desenvolvimento e testes sem API configurada
        - Em produção, erros devem ser monitorados
    
    Exemplo de uso:
        price = get_share_price("AAPL")  # Retorna preço real ou aleatório
        total_cost = price * quantity    # Usado para calcular custo de compra
    """
    if polygon_api_key:
        try:
            return get_share_price_polygon(symbol)
        except Exception as e:
            print(f"Was not able to use the polygon API due to {e}; using a random number")
    return float(random.randint(1, 100))
