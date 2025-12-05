"""
Testes unitários para o módulo src/core/market.py
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from src.core.market import (
    is_market_open,
    get_share_price,
    get_share_price_polygon,
    get_share_price_polygon_eod,
    get_share_price_polygon_min,
    get_all_share_prices_polygon_eod,
    get_market_for_prior_date
)


class TestMarketStatus:
    """Testes para verificação de status do mercado."""
    
    @patch('src.core.market.RESTClient')
    def test_is_market_open_true(self, mock_client_class):
        """Testa quando mercado está aberto."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_status = MagicMock()
        mock_status.market = "open"
        mock_client.get_market_status.return_value = mock_status
        
        result = is_market_open()
        assert result is True
    
    @patch('src.core.market.RESTClient')
    def test_is_market_open_false(self, mock_client_class):
        """Testa quando mercado está fechado."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_status = MagicMock()
        mock_status.market = "closed"
        mock_client.get_market_status.return_value = mock_status
        
        result = is_market_open()
        assert result is False


class TestSharePriceEOD:
    """Testes para obtenção de preços EOD (End of Day)."""
    
    @patch('src.core.market.RESTClient')
    def test_get_all_share_prices_polygon_eod(self, mock_client_class):
        """Testa obtenção de todos os preços EOD."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock do probe (SPY)
        mock_probe = MagicMock()
        mock_probe.timestamp = 1700000000000  # Timestamp em milissegundos
        mock_client.get_previous_close_agg.return_value = [mock_probe]
        
        # Mock dos resultados agregados
        mock_result1 = MagicMock()
        mock_result1.ticker = "AAPL"
        mock_result1.close = 150.0
        
        mock_result2 = MagicMock()
        mock_result2.ticker = "TSLA"
        mock_result2.close = 200.0
        
        mock_client.get_grouped_daily_aggs.return_value = [mock_result1, mock_result2]
        
        result = get_all_share_prices_polygon_eod()
        
        assert result["AAPL"] == 150.0
        assert result["TSLA"] == 200.0
    
    @patch('src.core.market.read_market')
    @patch('src.core.market.write_market')
    @patch('src.core.market.get_all_share_prices_polygon_eod')
    def test_get_market_for_prior_date_cached(self, mock_get_all, mock_write, mock_read):
        """Testa que usa cache quando disponível."""
        cached_data = {"AAPL": 150.0, "TSLA": 200.0}
        mock_read.return_value = cached_data
        
        today = "2024-01-01"
        result = get_market_for_prior_date(today)
        
        assert result == cached_data
        mock_get_all.assert_not_called()
        mock_write.assert_not_called()
    
    @patch('src.core.market.read_market')
    @patch('src.core.market.write_market')
    @patch('src.core.market.get_all_share_prices_polygon_eod')
    def test_get_market_for_prior_date_fetch(self, mock_get_all, mock_write, mock_read):
        """Testa que busca da API quando não há cache."""
        # Limpa o cache LRU antes do teste
        get_market_for_prior_date.cache_clear()
        
        mock_read.return_value = None
        api_data = {"AAPL": 150.0, "TSLA": 200.0}
        mock_get_all.return_value = api_data
        
        today = "2024-01-01"
        result = get_market_for_prior_date(today)
        
        assert result == api_data
        mock_get_all.assert_called_once()
        mock_write.assert_called_once_with(today, api_data)
    
    @patch('src.core.market.get_market_for_prior_date')
    def test_get_share_price_polygon_eod(self, mock_get_market):
        """Testa obtenção de preço EOD de ação específica."""
        market_data = {"AAPL": 150.0, "TSLA": 200.0}
        mock_get_market.return_value = market_data
        
        price = get_share_price_polygon_eod("AAPL")
        assert price == 150.0
        
        price = get_share_price_polygon_eod("TSLA")
        assert price == 200.0
        
        # Símbolo não encontrado retorna 0.0
        price = get_share_price_polygon_eod("INVALID")
        assert price == 0.0


class TestSharePriceMin:
    """Testes para obtenção de preços minuto a minuto."""
    
    @patch('src.core.market.RESTClient')
    def test_get_share_price_polygon_min_with_min(self, mock_client_class):
        """Testa obtenção de preço quando minuto atual está disponível."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_snapshot = MagicMock()
        mock_snapshot.min.close = 150.0
        mock_snapshot.prev_day.close = 149.0
        mock_client.get_snapshot_ticker.return_value = mock_snapshot
        
        price = get_share_price_polygon_min("AAPL")
        assert price == 150.0
    
    @patch('src.core.market.RESTClient')
    def test_get_share_price_polygon_min_fallback(self, mock_client_class):
        """Testa fallback para preço do dia anterior quando minuto não disponível."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_snapshot = MagicMock()
        mock_snapshot.min.close = None
        mock_snapshot.prev_day.close = 149.0
        mock_client.get_snapshot_ticker.return_value = mock_snapshot
        
        price = get_share_price_polygon_min("AAPL")
        assert price == 149.0


class TestSharePricePolygon:
    """Testes para função unificada de preços."""
    
    @patch('src.core.market.is_paid_polygon', True)
    @patch('src.core.market.get_share_price_polygon_min')
    def test_get_share_price_polygon_paid(self, mock_min):
        """Testa que usa método minuto quando plano é pago."""
        mock_min.return_value = 150.0
        
        price = get_share_price_polygon("AAPL")
        assert price == 150.0
        mock_min.assert_called_once_with("AAPL")
    
    @patch('src.core.market.is_paid_polygon', False)
    @patch('src.core.market.get_share_price_polygon_eod')
    def test_get_share_price_polygon_free(self, mock_eod):
        """Testa que usa método EOD quando plano é gratuito."""
        mock_eod.return_value = 150.0
        
        price = get_share_price_polygon("AAPL")
        assert price == 150.0
        mock_eod.assert_called_once_with("AAPL")


class TestGetSharePrice:
    """Testes para função principal get_share_price."""
    
    @patch('src.core.market.polygon_api_key', "test_key")
    @patch('src.core.market.get_share_price_polygon')
    def test_get_share_price_with_api_key(self, mock_polygon):
        """Testa obtenção de preço quando API key está configurada."""
        mock_polygon.return_value = 150.0
        
        price = get_share_price("AAPL")
        assert price == 150.0
        mock_polygon.assert_called_once_with("AAPL")
    
    @patch('src.core.market.polygon_api_key', "test_key")
    @patch('src.core.market.get_share_price_polygon')
    def test_get_share_price_api_error(self, mock_polygon):
        """Testa fallback para valor aleatório quando API falha."""
        mock_polygon.side_effect = Exception("API Error")
        
        price = get_share_price("AAPL")
        
        # Deve retornar valor aleatório entre 1 e 100
        assert 1 <= price <= 100
    
    @patch('src.core.market.polygon_api_key', None)
    def test_get_share_price_no_api_key(self):
        """Testa que retorna valor aleatório quando não há API key."""
        price = get_share_price("AAPL")
        
        # Deve retornar valor aleatório entre 1 e 100
        assert 1 <= price <= 100

