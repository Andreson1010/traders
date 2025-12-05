"""
Testes unitários para o módulo src/core/database.py
"""
import pytest
import json
import sqlite3
from unittest.mock import patch
from src.core.database import (
    write_account,
    read_account,
    write_log,
    read_log,
    write_market,
    read_market
)


class TestAccountFunctions:
    """Testes para funções de gerenciamento de contas."""
    
    def test_write_account_new(self, temp_db):
        """Testa escrita de nova conta."""
        with patch('src.core.database.DB', temp_db):
            account_data = {
                "name": "test_trader",
                "balance": 10000.0,
                "strategy": "Test strategy",
                "holdings": {"AAPL": 10},
                "transactions": [],
                "portfolio_value_time_series": []
            }
            
            write_account("test_trader", account_data)
            
            # Verifica que foi salvo
            with sqlite3.connect(temp_db) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT account FROM accounts WHERE name = ?', ("test_trader",))
                row = cursor.fetchone()
                assert row is not None
                saved_data = json.loads(row[0])
                assert saved_data["name"] == "test_trader"
                assert saved_data["balance"] == 10000.0
    
    def test_write_account_update(self, temp_db):
        """Testa atualização de conta existente."""
        with patch('src.core.database.DB', temp_db):
            # Cria conta inicial
            initial_data = {
                "name": "test_trader",
                "balance": 10000.0,
                "strategy": "Old strategy",
                "holdings": {},
                "transactions": [],
                "portfolio_value_time_series": []
            }
            write_account("test_trader", initial_data)
            
            # Atualiza conta
            updated_data = {
                "name": "test_trader",
                "balance": 5000.0,
                "strategy": "New strategy",
                "holdings": {"AAPL": 10},
                "transactions": [],
                "portfolio_value_time_series": []
            }
            write_account("test_trader", updated_data)
            
            # Verifica atualização
            with sqlite3.connect(temp_db) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT account FROM accounts WHERE name = ?', ("test_trader",))
                row = cursor.fetchone()
                saved_data = json.loads(row[0])
                assert saved_data["balance"] == 5000.0
                assert saved_data["strategy"] == "New strategy"
                assert saved_data["holdings"] == {"AAPL": 10}
    
    def test_read_account_existing(self, temp_db):
        """Testa leitura de conta existente."""
        with patch('src.core.database.DB', temp_db):
            account_data = {
                "name": "test_trader",
                "balance": 10000.0,
                "strategy": "Test strategy",
                "holdings": {"AAPL": 10},
                "transactions": [],
                "portfolio_value_time_series": []
            }
            write_account("test_trader", account_data)
            
            result = read_account("test_trader")
            
            assert result is not None
            assert result["name"] == "test_trader"
            assert result["balance"] == 10000.0
            assert result["holdings"] == {"AAPL": 10}
    
    def test_read_account_nonexistent(self, temp_db):
        """Testa leitura de conta que não existe."""
        with patch('src.core.database.DB', temp_db):
            result = read_account("nonexistent")
            assert result is None
    
    def test_read_account_case_insensitive(self, temp_db):
        """Testa que leitura é case-insensitive."""
        with patch('src.core.database.DB', temp_db):
            account_data = {
                "name": "test_trader",
                "balance": 10000.0,
                "strategy": "",
                "holdings": {},
                "transactions": [],
                "portfolio_value_time_series": []
            }
            write_account("Test_Trader", account_data)
            
            # Deve encontrar mesmo com case diferente
            result = read_account("test_trader")
            assert result is not None
            assert result["name"] == "test_trader"


class TestLogFunctions:
    """Testes para funções de logging."""
    
    def test_write_log(self, temp_db):
        """Testa escrita de log."""
        with patch('src.core.database.DB', temp_db):
            write_log("test_trader", "account", "Test message")
            
            # Verifica que foi salvo
            with sqlite3.connect(temp_db) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT name, type, message FROM logs WHERE name = ?',
                    ("test_trader",)
                )
                row = cursor.fetchone()
                assert row is not None
                assert row[0] == "test_trader"
                assert row[1] == "account"
                assert row[2] == "Test message"
    
    def test_read_log(self, temp_db):
        """Testa leitura de logs."""
        with patch('src.core.database.DB', temp_db):
            # Escreve múltiplos logs
            write_log("test_trader", "account", "First message")
            write_log("test_trader", "account", "Second message")
            write_log("test_trader", "trace", "Third message")
            
            logs = list(read_log("test_trader", last_n=2))
            
            assert len(logs) == 2
            # Logs são retornados do mais antigo ao mais recente
            assert logs[0][2] == "First message" or logs[0][2] == "Second message"
    
    def test_read_log_nonexistent(self, temp_db):
        """Testa leitura de logs de trader inexistente."""
        with patch('src.core.database.DB', temp_db):
            logs = list(read_log("nonexistent", last_n=10))
            assert len(logs) == 0
    
    def test_read_log_case_insensitive(self, temp_db):
        """Testa que logs são case-insensitive."""
        with patch('src.core.database.DB', temp_db):
            write_log("Test_Trader", "account", "Test message")
            
            logs = list(read_log("test_trader", last_n=10))
            assert len(logs) == 1
            assert logs[0][2] == "Test message"


class TestMarketFunctions:
    """Testes para funções de cache de mercado."""
    
    def test_write_market(self, temp_db):
        """Testa escrita de dados de mercado."""
        with patch('src.core.database.DB', temp_db):
            market_data = {
                "AAPL": 150.0,
                "TSLA": 200.0,
                "MSFT": 300.0
            }
            
            write_market("2024-01-01", market_data)
            
            # Verifica que foi salvo
            with sqlite3.connect(temp_db) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT data FROM market WHERE date = ?', ("2024-01-01",))
                row = cursor.fetchone()
                assert row is not None
                saved_data = json.loads(row[0])
                assert saved_data["AAPL"] == 150.0
                assert saved_data["TSLA"] == 200.0
    
    def test_write_market_update(self, temp_db):
        """Testa atualização de dados de mercado."""
        with patch('src.core.database.DB', temp_db):
            initial_data = {"AAPL": 150.0}
            write_market("2024-01-01", initial_data)
            
            updated_data = {"AAPL": 160.0, "TSLA": 200.0}
            write_market("2024-01-01", updated_data)
            
            # Verifica atualização
            result = read_market("2024-01-01")
            assert result["AAPL"] == 160.0
            assert result["TSLA"] == 200.0
    
    def test_read_market_existing(self, temp_db):
        """Testa leitura de dados de mercado existentes."""
        with patch('src.core.database.DB', temp_db):
            market_data = {
                "AAPL": 150.0,
                "TSLA": 200.0
            }
            write_market("2024-01-01", market_data)
            
            result = read_market("2024-01-01")
            
            assert result is not None
            assert result["AAPL"] == 150.0
            assert result["TSLA"] == 200.0
    
    def test_read_market_nonexistent(self, temp_db):
        """Testa leitura de dados de mercado inexistentes."""
        with patch('src.core.database.DB', temp_db):
            result = read_market("2024-01-01")
            assert result is None

