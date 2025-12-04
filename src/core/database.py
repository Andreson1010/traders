"""
Módulo de persistência de dados usando SQLite para o projeto Autonomous Traders.

Este módulo gerencia três tipos de dados:
1. Contas de traders: Saldo, holdings, transações, estratégias
2. Logs de operações: Histórico de ações dos traders para auditoria
3. Dados de mercado: Cache de preços de ações para otimização

Objetivo: Fornecer persistência simples e eficiente usando SQLite, permitindo que
dados de contas sejam mantidos entre execuções do sistema e logs sejam registrados
para análise e debugging.

Arquitetura:
- SQLite: Banco de dados local, sem necessidade de servidor separado
- JSON: Dados complexos (contas, market data) são serializados como JSON
- Context Manager: Uso de 'with' garante fechamento automático de conexões
"""

import sqlite3
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

# Nome do arquivo do banco de dados SQLite
# Criado no diretório atual quando o módulo é importado pela primeira vez
DB = "accounts.db"


# ============================================================================
# INICIALIZAÇÃO DO BANCO DE DADOS
# ============================================================================

# Executado quando o módulo é importado - cria tabelas se não existirem
with sqlite3.connect(DB) as conn:
    cursor = conn.cursor()
    
    # Tabela de contas: armazena dados completos de cada trader
    # - name: Nome do trader (chave primária, lowercase)
    # - account: Dados da conta serializados como JSON
    cursor.execute('CREATE TABLE IF NOT EXISTS accounts (name TEXT PRIMARY KEY, account TEXT)')
    
    # Tabela de logs: histórico de operações para auditoria e debugging
    # - id: ID auto-incrementado
    # - name: Nome do trader associado ao log
    # - datetime: Data e hora da operação
    # - type: Tipo de log (ex: "account", "notification", "trade")
    # - message: Mensagem descritiva da operação
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            datetime DATETIME,
            type TEXT,
            message TEXT
        )
    ''')
    
    # Tabela de mercado: cache de dados de mercado por data
    # - date: Data no formato string (chave primária)
    # - data: Dados de mercado serializados como JSON (preços, etc.)
    # Usado para cache de preços e evitar chamadas excessivas à API
    cursor.execute('CREATE TABLE IF NOT EXISTS market (date TEXT PRIMARY KEY, data TEXT)')
    conn.commit()


# ============================================================================
# FUNÇÕES DE GERENCIAMENTO DE CONTAS
# ============================================================================

def write_account(name, account_dict):
    """
    Salva ou atualiza os dados de uma conta de trader no banco de dados.
    
    Objetivo: Persistir estado completo da conta (saldo, holdings, transações, estratégia)
    para que seja mantido entre execuções do sistema. Chamado automaticamente por
    Account.save() sempre que a conta é modificada.
    
    Parâmetros:
        name: Nome do trader (ex: "Ed", "Warren")
        account_dict: Dicionário Python com todos os dados da conta:
            {
                "name": "ed",
                "balance": 10000.0,
                "strategy": "day trader...",
                "holdings": {"AAPL": 10},
                "transactions": [...],
                "portfolio_value_time_series": [...]
            }
    
    Processo:
        1. Serializa o dicionário para JSON
        2. Converte nome para lowercase (normalização)
        3. Insere ou atualiza registro na tabela accounts
        4. Usa ON CONFLICT para atualizar se conta já existe (UPSERT)
    
    Uso: Chamado automaticamente por Account.save() após qualquer modificação
    (compra, venda, mudança de estratégia, etc.).
    
    Relacionamento: Usado por accounts.py para persistir estado das contas.
    """
    json_data = json.dumps(account_dict)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO accounts (name, account)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET account=excluded.account
        ''', (name.lower(), json_data))
        conn.commit()

def read_account(name):
    """
    Lê os dados de uma conta de trader do banco de dados.
    
    Objetivo: Recuperar estado completo da conta salvo anteriormente, permitindo
    que traders mantenham seus dados entre execuções do sistema.
    
    Parâmetros:
        name: Nome do trader (ex: "Ed", "Warren")
    
    Retorna:
        - Dicionário Python com dados da conta se encontrada
        - None se a conta não existir no banco
    
    Processo:
        1. Busca registro na tabela accounts pelo nome (lowercase)
        2. Se encontrado, deserializa JSON para dicionário Python
        3. Retorna dicionário pronto para uso
    
    Uso: Chamado por Account.get() para carregar conta existente ou criar nova
    se não existir.
    
    Relacionamento: Usado por accounts.py no método Account.get() para carregar
    contas do banco de dados.
    """
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT account FROM accounts WHERE name = ?', (name.lower(),))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None


# ============================================================================
# FUNÇÕES DE LOGGING
# ============================================================================
    
def write_log(name: str, type: str, message: str):
    """
    Escreve uma entrada de log no banco de dados.
    
    Objetivo: Registrar todas as operações importantes do sistema para auditoria,
    debugging e análise de comportamento dos traders. Cada ação (compra, venda,
    mudança de estratégia) é registrada com timestamp.
    
    Parâmetros:
        name: Nome do trader associado ao log (ex: "Ed")
        type: Tipo de log (ex: "account", "notification", "trade")
        message: Mensagem descritiva da operação (ex: "Bought 10 of AAPL")
    
    Processo:
        1. Obtém timestamp atual usando datetime('now') do SQLite
        2. Normaliza nome para lowercase
        3. Insere registro na tabela logs
        4. Commit automático via context manager
    
    Uso: Chamado por accounts.py e accounts_server.py para registrar:
        - Operações de conta (buy_shares, sell_shares)
        - Mudanças de estratégia
        - Acessos a recursos
        - Notificações push
    
    Benefícios:
        - Auditoria completa de todas as operações
        - Debugging de problemas
        - Análise de comportamento dos traders
        - Rastreamento de histórico de ações
    """
    now = datetime.now().isoformat()
    
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO logs (name, datetime, type, message)
            VALUES (?, datetime('now'), ?, ?)
        ''', (name.lower(), type, message))
        conn.commit()

def read_log(name: str, last_n=10):
    """
    Lê as entradas de log mais recentes de um trader.
    
    Objetivo: Recuperar histórico de operações de um trader para análise,
    debugging ou exibição de atividade recente.
    
    Parâmetros:
        name: Nome do trader (ex: "Ed")
        last_n: Número de entradas mais recentes a retornar (padrão: 10)
    
    Retorna:
        Lista de tuplas (datetime, type, message) ordenadas do mais antigo
        para o mais recente (reversed para facilitar leitura cronológica).
    
    Processo:
        1. Busca logs do trader ordenados por data (mais recente primeiro)
        2. Limita a last_n entradas
        3. Inverte ordem para retornar do mais antigo ao mais recente
    
    Uso: Útil para:
        - Verificar últimas ações de um trader
        - Debugging de problemas
        - Análise de padrões de comportamento
        - Relatórios de atividade
    
    Exemplo de retorno:
        [
            ("2024-11-28 10:00:00", "account", "Bought 10 of AAPL"),
            ("2024-11-28 10:05:00", "account", "Sold 5 of AAPL"),
            ("2024-11-28 10:10:00", "account", "Retrieved account details")
        ]
    """
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT datetime, type, message FROM logs 
            WHERE name = ? 
            ORDER BY datetime DESC
            LIMIT ?
        ''', (name.lower(), last_n))
        
        return reversed(cursor.fetchall())


# ============================================================================
# FUNÇÕES DE CACHE DE DADOS DE MERCADO
# ============================================================================

def write_market(date: str, data: dict) -> None:
    """
    Salva dados de mercado no cache do banco de dados.
    
    Objetivo: Armazenar dados de mercado (preços de ações, etc.) por data para
    evitar chamadas excessivas à API externa (Polygon.io). Útil especialmente
    no plano gratuito que tem limites de taxa.
    
    Parâmetros:
        date: Data no formato string (ex: "2024-11-28")
        data: Dicionário Python com dados de mercado (preços, cotações, etc.)
    
    Processo:
        1. Serializa dicionário para JSON
        2. Insere ou atualiza registro na tabela market
        3. Usa ON CONFLICT para atualizar se data já existe (UPSERT)
    
    Uso: Chamado por market.py ou market_server.py para cachear dados de mercado
    após buscar da API. Permite reutilizar dados do dia anterior se API estiver
    indisponível ou para economizar chamadas.
    
    Benefícios:
        - Reduz chamadas à API externa
        - Funciona mesmo se API estiver offline
        - Economiza créditos da API (importante no plano gratuito)
        - Melhora performance (cache local é mais rápido)
    
    Relacionamento: Usado por market.py para implementar cache de preços.
    """
    data_json = json.dumps(data)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO market (date, data)
            VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET data=excluded.data
        ''', (date, data_json))
        conn.commit()

def read_market(date: str) -> dict | None:
    """
    Lê dados de mercado do cache do banco de dados.
    
    Objetivo: Recuperar dados de mercado previamente cacheados para uma data
    específica, evitando chamadas desnecessárias à API externa.
    
    Parâmetros:
        date: Data no formato string (ex: "2024-11-28")
    
    Retorna:
        - Dicionário Python com dados de mercado se encontrado no cache
        - None se não houver dados cacheados para essa data
    
    Processo:
        1. Busca registro na tabela market pela data
        2. Se encontrado, deserializa JSON para dicionário Python
        3. Retorna dicionário pronto para uso
    
    Uso: Chamado por market.py antes de fazer chamada à API. Se dados estiverem
    em cache, pode usar cache em vez de chamar API (especialmente útil para dados
    do dia anterior quando mercado está fechado).
    
    Estratégia de cache:
        - Dados do dia atual: Podem ser atualizados durante o dia
        - Dados de dias anteriores: Permanecem estáticos (mercado fechado)
        - Útil para plano gratuito: Reutiliza dados do dia anterior
    
    Relacionamento: Usado por market.py para implementar sistema de cache.
    """
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM market WHERE date = ?', (date,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None