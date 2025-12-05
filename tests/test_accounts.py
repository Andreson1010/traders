"""
Testes unitários para o módulo src/core/accounts.py
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from src.core.accounts import Account, Transaction, INITIAL_BALANCE, SPREAD


class TestTransaction:
    """Testes para a classe Transaction."""
    
    def test_transaction_creation(self):
        """Testa criação de uma transação."""
        transaction = Transaction(
            symbol="AAPL",
            quantity=10,
            price=150.0,
            timestamp="2024-01-01 10:00:00",
            rationale="Test purchase"
        )
        assert transaction.symbol == "AAPL"
        assert transaction.quantity == 10
        assert transaction.price == 150.0
        assert transaction.rationale == "Test purchase"
    
    def test_transaction_total(self):
        """Testa cálculo do total da transação."""
        transaction = Transaction(
            symbol="AAPL",
            quantity=10,
            price=150.0,
            timestamp="2024-01-01 10:00:00",
            rationale="Test"
        )
        assert transaction.total() == 1500.0
    
    def test_transaction_repr(self):
        """Testa representação string da transação."""
        transaction = Transaction(
            symbol="AAPL",
            quantity=10,
            price=150.0,
            timestamp="2024-01-01 10:00:00",
            rationale="Test"
        )
        repr_str = repr(transaction)
        assert "10 shares" in repr_str
        assert "AAPL" in repr_str
        assert "150.0" in repr_str


class TestAccount:
    """Testes para a classe Account."""
    
    @patch('src.core.database.read_account')
    @patch('src.core.database.write_account')
    def test_account_get_new(self, mock_write, mock_read):
        """Testa criação de nova conta quando não existe."""
        mock_read.return_value = None
        
        account = Account.get("NewTrader")
        
        assert account.name == "newtrader"
        assert account.balance == INITIAL_BALANCE
        assert account.strategy == ""
        assert account.holdings == {}
        assert account.transactions == []
        mock_write.assert_called_once()
    
    @patch('src.core.database.read_account')
    @patch('src.core.database.write_account')
    def test_account_get_existing(self, mock_write, mock_read):
        """Testa carregamento de conta existente."""
        existing_data = {
            "name": "existing",
            "balance": 5000.0,
            "strategy": "Existing strategy",
            "holdings": {"AAPL": 5},
            "transactions": [],
            "portfolio_value_time_series": []
        }
        mock_read.return_value = existing_data
        
        account = Account.get("Existing")
        
        assert account.name == "existing"
        assert account.balance == 5000.0
        assert account.strategy == "Existing strategy"
        assert account.holdings == {"AAPL": 5}
        mock_write.assert_not_called()
    
    @patch('src.core.database.write_account')
    def test_account_save(self, mock_write):
        """Testa salvamento de conta."""
        account = Account(
            name="test",
            balance=10000.0,
            strategy="Test",
            holdings={},
            transactions=[],
            portfolio_value_time_series=[]
        )
        account.save()
        mock_write.assert_called_once()
    
    @patch('src.core.database.write_account')
    def test_account_reset(self, mock_write):
        """Testa reset de conta."""
        account = Account(
            name="test",
            balance=5000.0,
            strategy="Old strategy",
            holdings={"AAPL": 10},
            transactions=[Transaction(
                symbol="AAPL",
                quantity=10,
                price=150.0,
                timestamp="2024-01-01 10:00:00",
                rationale="Test"
            )],
            portfolio_value_time_series=[("2024-01-01", 10000.0)]
        )
        
        account.reset("New strategy")
        
        assert account.balance == INITIAL_BALANCE
        assert account.strategy == "New strategy"
        assert account.holdings == {}
        assert account.transactions == []
        assert account.portfolio_value_time_series == []
        mock_write.assert_called()
    
    @patch('src.core.database.write_account')
    def test_account_deposit(self, mock_write):
        """Testa depósito de fundos."""
        account = Account(
            name="test",
            balance=1000.0,
            strategy="",
            holdings={},
            transactions=[],
            portfolio_value_time_series=[]
        )
        
        account.deposit(500.0)
        
        assert account.balance == 1500.0
        mock_write.assert_called()
    
    @patch('src.core.database.write_account')
    def test_account_deposit_invalid(self, mock_write):
        """Testa depósito com valor inválido."""
        account = Account(
            name="test",
            balance=1000.0,
            strategy="",
            holdings={},
            transactions=[],
            portfolio_value_time_series=[]
        )
        
        with pytest.raises(ValueError, match="Deposit amount must be positive"):
            account.deposit(-100.0)
        
        with pytest.raises(ValueError, match="Deposit amount must be positive"):
            account.deposit(0.0)
    
    @patch('src.core.database.write_account')
    def test_account_withdraw(self, mock_write):
        """Testa saque de fundos."""
        account = Account(
            name="test",
            balance=1000.0,
            strategy="",
            holdings={},
            transactions=[],
            portfolio_value_time_series=[]
        )
        
        account.withdraw(300.0)
        
        assert account.balance == 700.0
        mock_write.assert_called()
    
    @patch('src.core.database.write_account')
    def test_account_withdraw_insufficient_funds(self, mock_write):
        """Testa saque com fundos insuficientes."""
        account = Account(
            name="test",
            balance=100.0,
            strategy="",
            holdings={},
            transactions=[],
            portfolio_value_time_series=[]
        )
        
        with pytest.raises(ValueError, match="Insufficient funds"):
            account.withdraw(200.0)
    
    @patch('src.core.market.get_share_price')
    @patch('src.core.database.write_account')
    @patch('src.core.database.write_log')
    def test_account_buy_shares(self, mock_log, mock_write, mock_price):
        """Testa compra de ações."""
        mock_price.return_value = 150.0
        
        account = Account(
            name="test",
            balance=10000.0,
            strategy="",
            holdings={},
            transactions=[],
            portfolio_value_time_series=[]
        )
        
        result = account.buy_shares("AAPL", 10, "Test purchase")
        
        # Verifica que o preço foi aplicado com spread
        expected_price = 150.0 * (1 + SPREAD)
        expected_cost = expected_price * 10
        
        assert account.balance == 10000.0 - expected_cost
        assert account.holdings["AAPL"] == 10
        assert len(account.transactions) == 1
        assert account.transactions[0].symbol == "AAPL"
        assert account.transactions[0].quantity == 10
        assert "Completed" in result
        mock_write.assert_called()
        mock_log.assert_called()
    
    @patch('src.core.market.get_share_price')
    @patch('src.core.database.write_account')
    def test_account_buy_shares_insufficient_funds(self, mock_write, mock_price):
        """Testa compra com fundos insuficientes."""
        mock_price.return_value = 150.0
        
        account = Account(
            name="test",
            balance=100.0,
            strategy="",
            holdings={},
            transactions=[],
            portfolio_value_time_series=[]
        )
        
        with pytest.raises(ValueError, match="Insufficient funds"):
            account.buy_shares("AAPL", 10, "Test")
    
    @patch('src.core.market.get_share_price')
    @patch('src.core.database.write_account')
    def test_account_buy_shares_invalid_symbol(self, mock_write, mock_price):
        """Testa compra com símbolo inválido."""
        mock_price.return_value = 0.0
        
        account = Account(
            name="test",
            balance=10000.0,
            strategy="",
            holdings={},
            transactions=[],
            portfolio_value_time_series=[]
        )
        
        with pytest.raises(ValueError, match="Unrecognized symbol"):
            account.buy_shares("INVALID", 10, "Test")
    
    @patch('src.core.market.get_share_price')
    @patch('src.core.database.write_account')
    @patch('src.core.database.write_log')
    def test_account_sell_shares(self, mock_log, mock_write, mock_price):
        """Testa venda de ações."""
        mock_price.return_value = 150.0
        
        account = Account(
            name="test",
            balance=1000.0,
            strategy="",
            holdings={"AAPL": 10},
            transactions=[],
            portfolio_value_time_series=[]
        )
        
        result = account.sell_shares("AAPL", 5, "Test sale")
        
        # Verifica que o preço foi aplicado com spread de venda
        expected_price = 150.0 * (1 - SPREAD)
        expected_proceeds = expected_price * 5
        
        assert account.balance == 1000.0 + expected_proceeds
        assert account.holdings["AAPL"] == 5
        assert len(account.transactions) == 1
        assert account.transactions[0].quantity == -5  # Negativo para venda
        assert "Completed" in result
        mock_write.assert_called()
        mock_log.assert_called()
    
    @patch('src.core.market.get_share_price')
    @patch('src.core.database.write_account')
    def test_account_sell_shares_insufficient_holdings(self, mock_write, mock_price):
        """Testa venda com ações insuficientes."""
        mock_price.return_value = 150.0
        
        account = Account(
            name="test",
            balance=1000.0,
            strategy="",
            holdings={"AAPL": 5},
            transactions=[],
            portfolio_value_time_series=[]
        )
        
        with pytest.raises(ValueError, match="Not enough shares held"):
            account.sell_shares("AAPL", 10, "Test")
    
    @patch('src.core.market.get_share_price')
    @patch('src.core.database.write_account')
    def test_account_sell_shares_remove_from_holdings(self, mock_write, mock_price):
        """Testa que ações são removidas de holdings quando quantidade chega a zero."""
        mock_price.return_value = 150.0
        
        account = Account(
            name="test",
            balance=1000.0,
            strategy="",
            holdings={"AAPL": 5},
            transactions=[],
            portfolio_value_time_series=[]
        )
        
        account.sell_shares("AAPL", 5, "Test")
        
        assert "AAPL" not in account.holdings
    
    @patch('src.core.market.get_share_price')
    def test_account_calculate_portfolio_value(self, mock_price):
        """Testa cálculo do valor do portfólio."""
        mock_price.return_value = 150.0
        
        account = Account(
            name="test",
            balance=1000.0,
            strategy="",
            holdings={"AAPL": 10, "TSLA": 5},
            transactions=[],
            portfolio_value_time_series=[]
        )
        
        # Valor esperado: 1000 (saldo) + (150 * 10) + (150 * 5) = 3250.0
        portfolio_value = account.calculate_portfolio_value()
        assert portfolio_value == 3250.0
    
    def test_account_calculate_profit_loss(self):
        """Testa cálculo de P&L."""
        account = Account(
            name="test",
            balance=1000.0,
            strategy="",
            holdings={"AAPL": 10},
            transactions=[
                Transaction(
                    symbol="AAPL",
                    quantity=10,
                    price=150.0,
                    timestamp="2024-01-01 10:00:00",
                    rationale="Test"
                )
            ],
            portfolio_value_time_series=[]
        )
        
        # Portfolio value seria 1000 (saldo) + (150 * 10) = 2500
        # Initial spend = 150 * 10 = 1500
        # P&L = 2500 - 1500 - 1000 = 0 (sem lucro/prejuízo)
        with patch.object(account, 'calculate_portfolio_value', return_value=2500.0):
            pnl = account.calculate_profit_loss(2500.0)
            assert pnl == 0.0
    
    def test_account_get_holdings(self):
        """Testa obtenção de holdings."""
        account = Account(
            name="test",
            balance=1000.0,
            strategy="",
            holdings={"AAPL": 10, "TSLA": 5},
            transactions=[],
            portfolio_value_time_series=[]
        )
        
        holdings = account.get_holdings()
        assert holdings == {"AAPL": 10, "TSLA": 5}
    
    @patch('src.core.market.get_share_price')
    @patch('src.core.database.write_account')
    @patch('src.core.database.write_log')
    def test_account_report(self, mock_log, mock_write, mock_price):
        """Testa geração de relatório da conta."""
        mock_price.return_value = 150.0
        
        account = Account(
            name="test",
            balance=1000.0,
            strategy="Test strategy",
            holdings={"AAPL": 10},
            transactions=[],
            portfolio_value_time_series=[]
        )
        
        report = account.report()
        
        assert "test" in report
        assert "1000.0" in report
        assert "Test strategy" in report
        assert "total_portfolio_value" in report
        assert "total_profit_loss" in report
        mock_write.assert_called()
        mock_log.assert_called()
    
    @patch('src.core.database.write_account')
    @patch('src.core.database.write_log')
    def test_account_get_strategy(self, mock_log, mock_write):
        """Testa obtenção de estratégia."""
        account = Account(
            name="test",
            balance=1000.0,
            strategy="My strategy",
            holdings={},
            transactions=[],
            portfolio_value_time_series=[]
        )
        
        strategy = account.get_strategy()
        assert strategy == "My strategy"
        mock_log.assert_called()
    
    @patch('src.core.database.write_account')
    @patch('src.core.database.write_log')
    def test_account_change_strategy(self, mock_log, mock_write):
        """Testa mudança de estratégia."""
        account = Account(
            name="test",
            balance=1000.0,
            strategy="Old strategy",
            holdings={},
            transactions=[],
            portfolio_value_time_series=[]
        )
        
        result = account.change_strategy("New strategy")
        
        assert account.strategy == "New strategy"
        assert result == "Changed strategy"
        mock_write.assert_called()
        mock_log.assert_called()
    
    def test_account_list_transactions(self):
        """Testa listagem de transações."""
        transaction = Transaction(
            symbol="AAPL",
            quantity=10,
            price=150.0,
            timestamp="2024-01-01 10:00:00",
            rationale="Test"
        )
        
        account = Account(
            name="test",
            balance=1000.0,
            strategy="",
            holdings={},
            transactions=[transaction],
            portfolio_value_time_series=[]
        )
        
        transactions = account.list_transactions()
        assert len(transactions) == 1
        assert transactions[0]["symbol"] == "AAPL"
        assert transactions[0]["quantity"] == 10

