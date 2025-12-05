"""
Configuração compartilhada para testes (fixtures, mocks, etc.).
"""
import pytest
import sqlite3
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Adiciona o diretório raiz do projeto ao path para imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def temp_db():
    """
    Cria um banco de dados temporário para testes.
    
    Retorna o caminho do arquivo temporário.
    O banco é deletado após o teste.
    """
    # Cria arquivo temporário
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Cria tabelas necessárias
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS accounts (name TEXT PRIMARY KEY, account TEXT)')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                datetime DATETIME,
                type TEXT,
                message TEXT
            )
        ''')
        cursor.execute('CREATE TABLE IF NOT EXISTS market (date TEXT PRIMARY KEY, data TEXT)')
        conn.commit()
    
    yield db_path
    
    # Limpa após o teste
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def mock_database_module(temp_db):
    """
    Mock do módulo database.py para usar banco temporário.
    
    Substitui a constante DB por um caminho temporário.
    """
    with patch('src.core.database.DB', temp_db):
        # Também precisa recriar as tabelas no módulo mockado
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS accounts (name TEXT PRIMARY KEY, account TEXT)')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    datetime DATETIME,
                    type TEXT,
                    message TEXT
                )
            ''')
            cursor.execute('CREATE TABLE IF NOT EXISTS market (date TEXT PRIMARY KEY, data TEXT)')
            conn.commit()
        yield


@pytest.fixture
def mock_get_share_price():
    """
    Mock da função get_share_price para retornar preços fixos.
    
    Útil para testes que não dependem de API externa.
    """
    with patch('src.core.market.get_share_price') as mock:
        # Preços padrão para ações comuns
        mock.return_value = 150.0  # Preço padrão
        yield mock


@pytest.fixture
def sample_account_data():
    """
    Dados de exemplo para uma conta de trader.
    """
    return {
        "name": "test_trader",
        "balance": 10000.0,
        "strategy": "Test strategy",
        "holdings": {"AAPL": 10, "TSLA": 5},
        "transactions": [],
        "portfolio_value_time_series": []
    }


@pytest.fixture
def mock_polygon_api():
    """
    Mock da API Polygon para testes.
    """
    with patch('src.core.market.RESTClient') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        # Mock para get_previous_close_agg
        mock_probe = MagicMock()
        mock_probe.timestamp = 1700000000000  # Timestamp em milissegundos
        mock_instance.get_previous_close_agg.return_value = [mock_probe]
        
        # Mock para get_grouped_daily_aggs
        mock_result = MagicMock()
        mock_result.ticker = "AAPL"
        mock_result.close = 150.0
        mock_instance.get_grouped_daily_aggs.return_value = [mock_result]
        
        # Mock para get_snapshot_ticker
        mock_snapshot = MagicMock()
        mock_snapshot.min.close = 150.0
        mock_snapshot.prev_day.close = 149.0
        mock_instance.get_snapshot_ticker.return_value = mock_snapshot
        
        # Mock para get_market_status
        mock_status = MagicMock()
        mock_status.market = "open"
        mock_instance.get_market_status.return_value = mock_status
        
        yield mock_instance


@pytest.fixture
def mock_env_vars():
    """
    Mock de variáveis de ambiente para testes.
    """
    env_vars = {
        "POLYGON_API_KEY": "test_key",
        "POLYGON_PLAN": "free",
        "OPENAI_API_KEY": "test_openai_key",
        "DEEPSEEK_API_KEY": "test_deepseek_key",
        "GOOGLE_API_KEY": "test_google_key",
        "GROK_API_KEY": "test_grok_key",
        "OPENROUTER_API_KEY": "test_openrouter_key",
        "BRAVE_API_KEY": "test_brave_key",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars

