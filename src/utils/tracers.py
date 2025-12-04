"""
Módulo de Tracing Customizado para o projeto Autonomous Traders.

OBJETIVO DO MÓDULO:
-------------------
Este módulo implementa um sistema de tracing customizado que captura e armazena todos os eventos
de execução dos traders autônomos. Diferente do tracing padrão do OpenAI SDK (que apenas exibe
na plataforma OpenAI), este sistema:

1. **Captura eventos em tempo real**: Intercepta todos os traces e spans gerados pelos agentes
2. **Armazena localmente**: Salva logs no banco de dados SQLite para persistência
3. **Permite visualização na UI**: Os logs são exibidos na interface Gradio em tempo real
4. **Facilita debugging**: Permite entender o que cada trader está pensando e fazendo

CONTEXTO NO PROJETO:
--------------------
- O SDK de agentes da OpenAI fornece um sistema de tracing extensível via TracingProcessor
- Este módulo aproveita essa extensibilidade para criar um sistema próprio de logging
- Os logs capturados são exibidos na UI (app.py) permitindo monitorar os traders em tempo real
- Cada trader tem seus próprios logs identificados pelo nome (Warren, George, Ray, Cathie)

ARQUITETURA:
-----------
- LogTracer: Subclasse de TracingProcessor que implementa os callbacks de eventos
- make_trace_id: Gera IDs únicos de trace que incluem o nome do trader
- write_log: Função do database.py que persiste os logs no SQLite

FLUXO:
------
1. Trading Floor registra LogTracer via add_trace_processor()
2. Quando um trader executa, o SDK gera traces e spans
3. LogTracer intercepta esses eventos (on_trace_start, on_span_start, etc.)
4. Extrai informações relevantes (nome do trader, tipo, mensagem)
5. Salva no banco via write_log()
6. UI lê os logs do banco e exibe em tempo real
"""

from agents import TracingProcessor, Trace, Span
from src.core.database import write_log
import secrets
import string

# Caracteres alfanuméricos para gerar sufixos aleatórios nos trace IDs
ALPHANUM = string.ascii_lowercase + string.digits 


def make_trace_id(tag: str) -> str:
    """
    Gera um ID único de trace no formato 'trace_<tag><random>'.
    
    OBJETIVO:
    ---------
    Criar IDs de trace que incluem o nome do trader (tag) e um sufixo aleatório,
    permitindo que o LogTracer identifique qual trader está executando.
    
    O formato permite que get_name() extraia o nome do trader do trace_id.
    
    PROCESSO:
    ---------
    1. Adiciona "0" ao tag para marcar o fim do nome
    2. Calcula quantos caracteres aleatórios são necessários para completar 32 chars
    3. Gera sufixo aleatório com caracteres alfanuméricos
    4. Retorna no formato: trace_<tag>0<random>
    
    EXEMPLO:
    --------
    make_trace_id("warren") -> "trace_warren0a1b2c3d4e5f6g7h8i9j0k1l2m3n4"
    
    Parâmetros:
        tag: Nome do trader (ex: "warren", "george")
    
    Retorna:
        String no formato 'trace_<tag>0<random>' com 32 caracteres após 'trace_'
    """
    tag += "0"  # Marca o fim do nome do trader
    pad_len = 32 - len(tag)  # Calcula quantos caracteres aleatórios são necessários
    random_suffix = ''.join(secrets.choice(ALPHANUM) for _ in range(pad_len))
    return f"trace_{tag}{random_suffix}"


class LogTracer(TracingProcessor):
    """
    Processador de tracing customizado que captura eventos dos agentes e os salva no banco.
    
    OBJETIVO DA CLASSE:
    ------------------
    Implementar um sistema de logging customizado que:
    1. Intercepta todos os eventos de tracing do SDK de agentes da OpenAI
    2. Extrai informações relevantes (nome do trader, tipo de evento, mensagem)
    3. Persiste os logs no banco de dados SQLite
    4. Permite que a UI exiba os "pensamentos" dos traders em tempo real
    
    CONTEXTO:
    ---------
    - Herda de TracingProcessor (classe base do SDK de agentes)
    - Registrado via add_trace_processor() no trading_floor.py
    - Cada evento (trace start/end, span start/end) é capturado e processado
    - Os logs são associados ao trader através do trace_id que contém o nome
    
    USO NO PROJETO:
    ---------------
    - Trading Floor registra: add_trace_processor(LogTracer())
    - Quando traders executam, eventos são automaticamente capturados
    - UI lê logs do banco e exibe na coluna de cada trader
    - Permite ver o que cada trader está pensando e fazendo em tempo real
    """

    def get_name(self, trace_or_span: Trace | Span) -> str | None:
        """
        Extrai o nome do trader do trace_id.
        
        OBJETIVO:
        ---------
        Identificar qual trader está executando a partir do trace_id.
        O trace_id é gerado por make_trace_id() no formato 'trace_<nome>0<random>'.
        
        PROCESSO:
        ---------
        1. Extrai a parte após 'trace_' do trace_id
        2. Procura pelo marcador '0' que indica o fim do nome
        3. Retorna o nome do trader (ex: "warren", "george")
        4. Retorna None se não conseguir identificar
        
        EXEMPLO:
        --------
        trace_id = "trace_warren0a1b2c3..." -> retorna "warren"
        trace_id = "trace_george0x9y8z7..." -> retorna "george"
        
        Parâmetros:
            trace_or_span: Objeto Trace ou Span do SDK de agentes
        
        Retorna:
            Nome do trader (str) ou None se não conseguir identificar
        """
        trace_id = trace_or_span.trace_id
        name = trace_id.split("_")[1]  # Pega a parte após 'trace_'
        if '0' in name:
            return name.split("0")[0]  # Retorna tudo antes do '0' (nome do trader)
        else:
            return None

    def on_trace_start(self, trace) -> None:
        """
        Callback chamado quando um trace inicia.
        
        OBJETIVO:
        ---------
        Capturar o início de uma execução de trader (ex: "warren-trading", "george-rebalancing").
        Salva um log indicando que o trader começou sua execução.
        
        PROCESSO:
        ---------
        1. Extrai o nome do trader do trace_id
        2. Se conseguir identificar, salva log no banco
        3. Log inclui o nome do trace (ex: "Started: warren-trading")
        
        CONTEXTO:
        ---------
        - Chamado automaticamente pelo SDK quando um trace inicia
        - Um trace representa uma execução completa de um trader
        - O trace.name indica o tipo de execução (trading ou rebalancing)
        
        Parâmetros:
            trace: Objeto Trace do SDK de agentes
        """
        name = self.get_name(trace)
        if name:
            write_log(name, "trace", f"Started: {trace.name}")

    def on_trace_end(self, trace) -> None:
        """
        Callback chamado quando um trace termina.
        
        OBJETIVO:
        ---------
        Capturar o fim de uma execução de trader, indicando que o trader completou
        seu ciclo de trading ou rebalancing.
        
        PROCESSO:
        ---------
        1. Extrai o nome do trader do trace_id
        2. Se conseguir identificar, salva log no banco
        3. Log inclui o nome do trace (ex: "Ended: warren-trading")
        
        CONTEXTO:
        ---------
        - Chamado automaticamente pelo SDK quando um trace termina
        - Marca o fim de uma execução completa do trader
        - Útil para saber quando um trader terminou de processar
        
        Parâmetros:
            trace: Objeto Trace do SDK de agentes
        """
        name = self.get_name(trace)
        if name:
            write_log(name, "trace", f"Ended: {trace.name}")

    def on_span_start(self, span) -> None:
        """
        Callback chamado quando um span inicia (chamada de ferramenta, geração, etc.).
        
        OBJETIVO:
        ---------
        Capturar o início de ações específicas dentro de uma execução de trader:
        - Chamadas de ferramentas (buy_shares, sell_shares, pesquisar, etc.)
        - Gerações de texto do modelo
        - Chamadas a servidores MCP
        - Erros que ocorrem
        
        Este é o método mais importante para entender o que o trader está fazendo.
        
        PROCESSO:
        ---------
        1. Extrai o nome do trader do span
        2. Identifica o tipo do span (agent, function, generation, etc.)
        3. Constrói mensagem descritiva com informações do span:
           - Tipo (agent, function, generation, response, etc.)
           - Nome da ferramenta/função (se aplicável)
           - Servidor MCP usado (se aplicável)
           - Erro (se houver)
        4. Salva log no banco com tipo e mensagem
        
        TIPOS DE SPAN:
        -------------
        - "agent": Decisões e raciocínio do agente
        - "function": Chamadas de ferramentas (buy_shares, pesquisar, etc.)
        - "generation": Geração de texto pelo modelo
        - "response": Respostas do modelo
        - "mcp": Chamadas a servidores MCP
        
        EXEMPLO DE LOGS:
        ----------------
        - "Started function buy_shares" (trader chamou ferramenta de compra)
        - "Started agent" (trader está pensando)
        - "Started generation" (modelo está gerando resposta)
        - "Started function Researcher" (trader chamou pesquisador)
        
        Parâmetros:
            span: Objeto Span do SDK de agentes
        """
        name = self.get_name(span)
        type = span.span_data.type if span.span_data else "span"
        if name:
            message = "Started"
            if span.span_data:
                if span.span_data.type:
                    message += f" {span.span_data.type}"
                if hasattr(span.span_data, "name") and span.span_data.name:
                    message += f" {span.span_data.name}"
                if hasattr(span.span_data, "server") and span.span_data.server:
                    message += f" {span.span_data.server}"
            if span.error:
                message += f" {span.error}"
            write_log(name, type, message)

    def on_span_end(self, span) -> None:
        """
        Callback chamado quando um span termina.
        
        OBJETIVO:
        ---------
        Capturar o fim de ações específicas dentro de uma execução de trader.
        Complementa on_span_start() para ter início e fim de cada ação.
        
        PROCESSO:
        ---------
        1. Extrai o nome do trader do span
        2. Identifica o tipo do span
        3. Constrói mensagem descritiva similar a on_span_start()
        4. Salva log no banco
        
        CONTEXTO:
        ---------
        - Chamado automaticamente quando uma ação completa
        - Útil para rastrear duração de operações
        - Pode indicar erros se span.error estiver presente
        
        EXEMPLO DE LOGS:
        ----------------
        - "Ended function buy_shares" (compra concluída)
        - "Ended agent" (trader terminou de pensar)
        - "Ended generation" (modelo terminou de gerar)
        
        Parâmetros:
            span: Objeto Span do SDK de agentes
        """
        name = self.get_name(span)
        type = span.span_data.type if span.span_data else "span"
        if name:
            message = "Ended"
            if span.span_data:
                if span.span_data.type:
                    message += f" {span.span_data.type}"
                if hasattr(span.span_data, "name") and span.span_data.name:
                    message += f" {span.span_data.name}"
                if hasattr(span.span_data, "server") and span.span_data.server:
                    message += f" {span.span_data.server}"
            if span.error:
                message += f" {span.error}"
            write_log(name, type, message)

    def force_flush(self) -> None:
        """
        Força o flush de logs pendentes.
        
        OBJETIVO:
        ---------
        Método requerido pela interface TracingProcessor. No nosso caso,
        os logs são escritos diretamente no banco via write_log(), então
        não há necessidade de buffer ou flush.
        
        IMPLEMENTAÇÃO:
        --------------
        Método vazio pois não há buffer para fazer flush.
        """
        pass

    def shutdown(self) -> None:
        """
        Chamado quando o sistema está sendo desligado.
        
        OBJETIVO:
        ---------
        Método requerido pela interface TracingProcessor. Permite fazer
        limpeza final antes do sistema encerrar.
        
        IMPLEMENTAÇÃO:
        --------------
        Método vazio pois não há recursos que precisem ser liberados.
        Os logs já estão persistidos no banco de dados.
        """
        pass