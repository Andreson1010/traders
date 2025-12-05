"""
Testes unitários para o módulo src/utils/tracers.py
"""
import pytest
from unittest.mock import patch, MagicMock
from src.utils.tracers import make_trace_id, LogTracer


class TestMakeTraceId:
    """Testes para função make_trace_id."""
    
    def test_make_trace_id_format(self):
        """Testa que o ID gerado tem formato correto."""
        trace_id = make_trace_id("warren")
        
        assert trace_id.startswith("trace_")
        assert "warren" in trace_id
        assert "0" in trace_id  # Marcador de fim do nome
    
    def test_make_trace_id_length(self):
        """Testa que o ID tem comprimento correto."""
        trace_id = make_trace_id("warren")
        
        # Deve ter "trace_" (6 chars) + 32 chars = 38 chars total
        assert len(trace_id) == 38
    
    def test_make_trace_id_uniqueness(self):
        """Testa que IDs gerados são únicos."""
        id1 = make_trace_id("warren")
        id2 = make_trace_id("warren")
        
        # Devem ser diferentes (sufixo aleatório)
        assert id1 != id2
    
    def test_make_trace_id_different_tags(self):
        """Testa que diferentes tags geram IDs diferentes."""
        id1 = make_trace_id("warren")
        id2 = make_trace_id("george")
        
        assert id1 != id2
        assert "warren" in id1
        assert "george" in id2


class TestLogTracer:
    """Testes para classe LogTracer."""
    
    def test_get_name_valid(self):
        """Testa extração de nome de trace_id válido."""
        tracer = LogTracer()
        
        trace = MagicMock()
        trace.trace_id = "trace_warren0a1b2c3d4e5f6g7h8i9j0k1l2m3n4"
        
        name = tracer.get_name(trace)
        assert name == "warren"
    
    def test_get_name_invalid(self):
        """Testa extração de nome de trace_id inválido."""
        tracer = LogTracer()
        
        trace = MagicMock()
        trace.trace_id = "trace_invalid_format"
        
        name = tracer.get_name(trace)
        assert name is None
    
    def test_get_name_with_span(self):
        """Testa que funciona com Span também."""
        tracer = LogTracer()
        
        span = MagicMock()
        span.trace_id = "trace_george0x9y8z7w6v5u4t3s2r1q0p9o8n7m6"
        
        name = tracer.get_name(span)
        assert name == "george"
    
    @patch('src.utils.tracers.write_log')
    def test_on_trace_start(self, mock_write_log):
        """Testa callback on_trace_start."""
        tracer = LogTracer()
        
        trace = MagicMock()
        trace.trace_id = "trace_warren0a1b2c3d4e5f6g7h8i9j0k1l2m3n4"
        trace.name = "warren-trading"
        
        tracer.on_trace_start(trace)
        
        mock_write_log.assert_called_once_with("warren", "trace", "Started: warren-trading")
    
    @patch('src.utils.tracers.write_log')
    def test_on_trace_start_invalid_id(self, mock_write_log):
        """Testa que não escreve log se trace_id for inválido."""
        tracer = LogTracer()
        
        trace = MagicMock()
        trace.trace_id = "invalid_format"
        trace.name = "test-trading"
        
        tracer.on_trace_start(trace)
        
        mock_write_log.assert_not_called()
    
    @patch('src.utils.tracers.write_log')
    def test_on_trace_end(self, mock_write_log):
        """Testa callback on_trace_end."""
        tracer = LogTracer()
        
        trace = MagicMock()
        trace.trace_id = "trace_george0x9y8z7w6v5u4t3s2r1q0p9o8n7m6"
        trace.name = "george-rebalancing"
        
        tracer.on_trace_end(trace)
        
        mock_write_log.assert_called_once_with("george", "trace", "Ended: george-rebalancing")
    
    @patch('src.utils.tracers.write_log')
    def test_on_span_start(self, mock_write_log):
        """Testa callback on_span_start."""
        tracer = LogTracer()
        
        span = MagicMock()
        span.trace_id = "trace_warren0a1b2c3d4e5f6g7h8i9j0k1l2m3n4"
        span.error = None
        
        span_data = MagicMock()
        span_data.type = "function"
        span_data.name = "buy_shares"
        # Garante que server não existe ou é None
        if hasattr(span_data, 'server'):
            del span_data.server
        span.span_data = span_data
        
        tracer.on_span_start(span)
        
        mock_write_log.assert_called_once_with("warren", "function", "Started function buy_shares")
    
    @patch('src.utils.tracers.write_log')
    def test_on_span_start_with_server(self, mock_write_log):
        """Testa on_span_start com servidor MCP."""
        tracer = LogTracer()
        
        span = MagicMock()
        span.trace_id = "trace_george0x9y8z7w6v5u4t3s2r1q0p9o8n7m6"
        span.error = None
        
        span_data = MagicMock()
        span_data.type = "mcp"
        span_data.name = "accounts_server"
        span_data.server = "accounts"
        span.span_data = span_data
        
        tracer.on_span_start(span)
        
        mock_write_log.assert_called_once_with("george", "mcp", "Started mcp accounts_server accounts")
    
    @patch('src.utils.tracers.write_log')
    def test_on_span_start_with_error(self, mock_write_log):
        """Testa on_span_start com erro."""
        tracer = LogTracer()
        
        span = MagicMock()
        span.trace_id = "trace_warren0a1b2c3d4e5f6g7h8i9j0k1l2m3n4"
        span.error = "ConnectionError"
        
        span_data = MagicMock()
        span_data.type = "function"
        span_data.name = "buy_shares"
        # Garante que server não existe ou é None
        if hasattr(span_data, 'server'):
            del span_data.server
        span.span_data = span_data
        
        tracer.on_span_start(span)
        
        mock_write_log.assert_called_once_with("warren", "function", "Started function buy_shares ConnectionError")
    
    @patch('src.utils.tracers.write_log')
    def test_on_span_start_no_span_data(self, mock_write_log):
        """Testa on_span_start sem span_data."""
        tracer = LogTracer()
        
        span = MagicMock()
        span.trace_id = "trace_warren0a1b2c3d4e5f6g7h8i9j0k1l2m3n4"
        span.span_data = None
        span.error = None
        
        tracer.on_span_start(span)
        
        mock_write_log.assert_called_once_with("warren", "span", "Started")
    
    @patch('src.utils.tracers.write_log')
    def test_on_span_end(self, mock_write_log):
        """Testa callback on_span_end."""
        tracer = LogTracer()
        
        span = MagicMock()
        span.trace_id = "trace_warren0a1b2c3d4e5f6g7h8i9j0k1l2m3n4"
        span.error = None
        
        span_data = MagicMock()
        span_data.type = "function"
        span_data.name = "sell_shares"
        # Garante que server não existe ou é None
        if hasattr(span_data, 'server'):
            del span_data.server
        span.span_data = span_data
        
        tracer.on_span_end(span)
        
        mock_write_log.assert_called_once_with("warren", "function", "Ended function sell_shares")
    
    def test_force_flush(self):
        """Testa que force_flush não faz nada (sem buffer)."""
        tracer = LogTracer()
        # Não deve lançar exceção
        tracer.force_flush()
    
    def test_shutdown(self):
        """Testa que shutdown não faz nada."""
        tracer = LogTracer()
        # Não deve lançar exceção
        tracer.shutdown()

