"""
Módulo Trading Floor - Motor principal do sistema de trading autônomo.

OBJETIVO DO MÓDULO:
Este módulo é o coração do sistema de trading autônomo. Ele orquestra a execução
periódica de múltiplos traders, criando um "trading floor" simulado onde cada trader
opera de forma independente seguindo sua estratégia de investimento.

COMO SE CONECTA COM O PROJETO:
1. Ponto de entrada principal: Executado via `python -m src.agents.trading_floor`
   ou através do script `start_trading_floor.sh`

2. Cria e gerencia 4 traders autônomos:
   - Warren (Patience) - Estratégia de valor, longo prazo
   - George (Bold) - Trader macro agressivo
   - Ray (Systematic) - Sistemático, baseado em princípios
   - Cathie (Crypto) - Inovação disruptiva

3. Loop de execução:
   - Executa todos os traders a cada N minutos (configurável)
   - Verifica se o mercado está aberto antes de executar
   - Captura e registra todos os eventos via LogTracer
   - Roda indefinidamente até ser interrompido
   
   COMO É INTERROMPIDO:
   - Ctrl+C no terminal: Envia sinal SIGINT, interrompe o loop
   - Fechar terminal: Encerra o processo
   - kill/killall: Envia sinal SIGTERM ou SIGKILL
   - O asyncio.run() captura KeyboardInterrupt automaticamente

4. Integração com outros módulos:
   - traders.py: Cria instâncias de Trader
   - tracers.py: Captura eventos para logging
   - market.py: Verifica status do mercado
   - accounts.py: Cada trader gerencia sua própria conta

FLUXO DE EXECUÇÃO:
1. Carrega configurações do .env
2. Define nomes e modelos dos traders
3. Cria instâncias dos 4 traders
4. Inicia loop infinito:
   a. Verifica se mercado está aberto (ou se deve executar mesmo fechado)
   b. Executa todos os traders em paralelo (asyncio.gather)
   c. Aguarda N minutos antes da próxima execução
   d. Repete

USO:
    # Executar diretamente
    python -m src.agents.trading_floor
    
    # Ou via script
    ./start_trading_floor.sh
"""

from src.agents.traders import Trader
from typing import List
import asyncio
from src.utils.tracers import LogTracer
from agents import add_trace_processor
from src.core.market import is_market_open
from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente do arquivo .env
# override=True garante que valores do .env sobrescrevem variáveis já existentes
load_dotenv(override=True)

# ============================================================================
# CONFIGURAÇÕES DO SISTEMA (carregadas do .env)
# ============================================================================

# Intervalo entre execuções dos traders (em minutos)
# Padrão: 60 minutos (1 hora)
# Exemplo: RUN_EVERY_N_MINUTES=30 para executar a cada 30 minutos
RUN_EVERY_N_MINUTES = int(os.getenv("RUN_EVERY_N_MINUTES", "30"))

# Se True, executa traders mesmo quando mercado está fechado
# Útil para testes e desenvolvimento
# Padrão: False (só executa quando mercado está aberto)
RUN_EVEN_WHEN_MARKET_IS_CLOSED = (
    os.getenv("RUN_EVEN_WHEN_MARKET_IS_CLOSED", "false").strip().lower() == "true"
)

# Se True, cada trader usa um modelo de IA diferente
# Se False, todos usam o mesmo modelo (gpt-4o-mini)
# Padrão: False
USE_MANY_MODELS = os.getenv("USE_MANY_MODELS", "false").strip().lower() == "true"

# ============================================================================
# CONFIGURAÇÃO DOS TRADERS
# ============================================================================

# Nomes dos 4 traders (inspirados em grandes investidores)
names = ["Warren", "George", "Ray", "Cathie"]

# Sobrenomes/identidades dos traders (descrevem suas estratégias)
lastnames = ["Patience", "Bold", "Systematic", "Crypto"]

# Seleção de modelos de IA baseado na configuração USE_MANY_MODELS
if USE_MANY_MODELS:
    # Cada trader usa um modelo diferente (requer chaves de API específicas)
    model_names = [
        "gpt-4.1-mini",                        # Warren usa GPT-4.1 Mini (OpenAI)
        "deepseek-chat",                       # George usa DeepSeek Chat
        "gemini-2.5-flash-preview-04-17",      # Ray usa Gemini 2.5 Flash (Google)
        "grok-3-mini-beta",                    # Cathie usa Grok 3 Mini (xAI)
    ]
    # Nomes curtos para exibição na UI
    short_model_names = ["GPT 4.1 Mini", "DeepSeek V3", "Gemini 2.5 Flash", "Grok 3 Mini"]
else:
    # Todos os traders usam o mesmo modelo (mais simples, só precisa OPENAI_API_KEY)
    model_names = ["gpt-4o-mini"] * 4  # Cria lista com 4 cópias do mesmo modelo
    short_model_names = ["GPT 4o mini"] * 4


def create_traders() -> List[Trader]:
    """
    Cria instâncias dos 4 traders do sistema.
    
    OBJETIVO:
    Factory function que instancia todos os traders com suas configurações
    (nome, sobrenome/identidade, modelo de IA).
    
    PROCESSO:
    1. Itera sobre as listas de nomes, sobrenomes e modelos simultaneamente
    2. Para cada combinação, cria uma instância de Trader
    3. Retorna lista com os 4 traders prontos para uso
    
    RETORNA:
    Lista de 4 instâncias de Trader:
    - Trader("Warren", "Patience", "gpt-4.1-mini" ou "gpt-4o-mini")
    - Trader("George", "Bold", "deepseek-chat" ou "gpt-4o-mini")
    - Trader("Ray", "Systematic", "gemini-2.5-flash..." ou "gpt-4o-mini")
    - Trader("Cathie", "Crypto", "grok-3-mini-beta" ou "gpt-4o-mini")
    
    NOTA:
    Cada trader carrega automaticamente sua conta do banco de dados
    (ou cria uma nova se não existir) ao ser instanciado.
    """
    traders = []
    # zip() combina as 3 listas: (Warren, Patience, modelo1), (George, Bold, modelo2), etc.
    for name, lastname, model_name in zip(names, lastnames, model_names):
        # Cria instância do trader com suas configurações
        traders.append(Trader(name, lastname, model_name))
    return traders


async def run_every_n_minutes():
    """
    Loop principal de execução do trading floor.
    
    OBJETIVO:
    Orquestra a execução periódica de todos os traders em um loop infinito,
    respeitando o intervalo configurado e o status do mercado.
    
    PROCESSO:
    1. Configura sistema de tracing para capturar eventos
    2. Cria instâncias dos 4 traders
    3. Entra em loop infinito:
       a. Verifica se deve executar (mercado aberto ou RUN_EVEN_WHEN_MARKET_IS_CLOSED=True)
       b. Se sim, executa todos os traders em paralelo usando asyncio.gather()
       c. Se não, imprime mensagem e pula esta execução
       d. Aguarda N minutos antes da próxima iteração
    
    CARACTERÍSTICAS:
    - Execução assíncrona: Todos os traders rodam em paralelo (não sequencial)
    - Não bloqueante: Usa asyncio para permitir execução concorrente
    - Resiliente: Continua rodando mesmo se um trader falhar
    - Configurável: Intervalo e comportamento controlados por variáveis de ambiente
    
    TRACING:
    LogTracer captura todos os eventos (trades, pesquisas, decisões) e salva
    no banco de dados para visualização na UI em tempo real.
    
    EXECUÇÃO PARALELA:
    asyncio.gather() executa todos os traders simultaneamente, não sequencialmente.
    Isso significa que os 4 traders podem estar pesquisando e trading ao mesmo tempo,
    tornando o sistema mais eficiente e realista.
    """
    # Adiciona processador de tracing para capturar eventos dos traders
    # LogTracer salva eventos no banco de dados para visualização na UI
    add_trace_processor(LogTracer())
    
    # Cria instâncias dos 4 traders com suas configurações
    traders = create_traders()
    
    # Loop infinito que executa os traders periodicamente
    # 
    # INTERRUPÇÃO DO LOOP:
    # O loop pode ser interrompido de várias formas:
    # 1. Ctrl+C (KeyboardInterrupt): Envia sinal SIGINT
    #    - O asyncio.run() captura KeyboardInterrupt automaticamente
    #    - O loop é encerrado de forma limpa
    # 2. Fechar terminal: Encerra o processo
    # 3. kill <PID>: Envia sinal SIGTERM (pode ser capturado)
    # 4. kill -9 <PID>: Envia sinal SIGKILL (força encerramento imediato)
    #
    # NOTA: O código atual não implementa tratamento de sinais para shutdown graceful.
    # Se necessário, pode-se adicionar signal handlers para limpar recursos antes de sair.
    while True:
        # Verifica se deve executar: mercado aberto OU configuração permite executar fechado
        if RUN_EVEN_WHEN_MARKET_IS_CLOSED or is_market_open():
            # Executa todos os traders em paralelo (não sequencial)
            # asyncio.gather() permite que os 4 traders operem simultaneamente
            # Cada trader.run() executa um ciclo completo: pesquisa → decisão → trade
            await asyncio.gather(*[trader.run() for trader in traders])
        else:
            # Mercado fechado e configuração não permite executar
            print("Market is closed, skipping run")
        
        # Aguarda o intervalo configurado antes da próxima execução
        # RUN_EVERY_N_MINUTES está em minutos, então multiplica por 60 para segundos
        # 
        # IMPORTANTE: Durante o sleep, o loop pode ser interrompido a qualquer momento
        # com Ctrl+C. O asyncio.sleep() é cancelável e levanta CancelledError se
        # o event loop for cancelado.
        await asyncio.sleep(RUN_EVERY_N_MINUTES * 60)


if __name__ == "__main__":
    """
    Ponto de entrada principal quando o módulo é executado diretamente.
    
    EXECUÇÃO:
    - Via linha de comando: python -m src.agents.trading_floor
    - Via script: ./start_trading_floor.sh
    
    PROCESSO:
    1. Imprime mensagem informativa com intervalo configurado
    2. Inicia o loop assíncrono principal usando asyncio.run()
    3. O loop roda indefinidamente até ser interrompido (Ctrl+C)
    
    NOTA:
    Este é o "motor" do sistema. Ele deve rodar continuamente em background
    enquanto a UI (app.py) pode rodar em outro terminal para visualização.
    """
    # Mensagem informativa sobre o intervalo de execução
    print(f"Starting scheduler to run every {RUN_EVERY_N_MINUTES} minutes")
    
    # Inicia o loop assíncrono principal
    # asyncio.run() cria um novo event loop e executa a função até completar
    # Como run_every_n_minutes() tem um loop infinito, isso roda indefinidamente
    #
    # COMO INTERROMPER:
    # 1. Ctrl+C: Pressione Ctrl+C no terminal onde o processo está rodando
    #    - Isso envia um sinal SIGINT (KeyboardInterrupt)
    #    - O asyncio.run() captura e encerra o loop de forma limpa
    #    - Você verá "KeyboardInterrupt" ou mensagem de encerramento
    #
    # 2. Fechar terminal: Fechar a janela do terminal encerra o processo
    #
    # 3. kill <PID>: Encontre o PID do processo e envie sinal
    #    - ps aux | grep trading_floor  # Encontra o PID
    #    - kill <PID>                    # Envia SIGTERM (graceful)
    #    - kill -9 <PID>                  # Força encerramento (SIGKILL)
    #
    # 4. killall: Encerra todos os processos com o nome
    #    - killall python  # CUIDADO: Encerra TODOS os processos Python!
    #
    # NOTA: Se o processo estiver rodando em background (com & ou nohup),
    # você precisará usar kill/killall para encerrá-lo.
    try:
        asyncio.run(run_every_n_minutes())
    except KeyboardInterrupt:
        # Captura Ctrl+C e encerra de forma limpa
        print("\n\nTrading floor interrompido pelo usuário (Ctrl+C)")
        print("Encerrando execução...")
