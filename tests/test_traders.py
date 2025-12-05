"""
Testes unitários para o módulo src/agents/traders.py
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.agents.traders import (
    Trader,
    get_model,
    get_researcher,
    get_researcher_tool
)


class TestGetModel:
    """Testes para função get_model."""
    
    def test_get_model_openrouter(self):
        """Testa seleção de modelo via OpenRouter."""
        from src.agents.traders import OpenAIChatCompletionsModel
        
        # Modelos com "/" no nome devem usar OpenRouter
        # Exemplo: "openai/gpt-4.1-mini" ou "anthropic/claude-3-opus"
        result = get_model("openai/gpt-4.1-mini")
        
        # Modelos com "/" devem retornar OpenAIChatCompletionsModel com openrouter_client
        assert isinstance(result, OpenAIChatCompletionsModel)
        assert result.model == "openai/gpt-4.1-mini"
    
    @patch('src.agents.traders.deepseek_client')
    def test_get_model_deepseek(self, mock_client):
        """Testa seleção de modelo DeepSeek."""
        from src.agents.traders import OpenAIChatCompletionsModel
        
        result = get_model("deepseek-chat")
        
        assert isinstance(result, OpenAIChatCompletionsModel)
    
    @patch('src.agents.traders.grok_client')
    def test_get_model_grok(self, mock_client):
        """Testa seleção de modelo Grok."""
        from src.agents.traders import OpenAIChatCompletionsModel
        
        result = get_model("grok-beta")
        
        assert isinstance(result, OpenAIChatCompletionsModel)
    
    @patch('src.agents.traders.gemini_client')
    def test_get_model_gemini(self, mock_client):
        """Testa seleção de modelo Gemini."""
        from src.agents.traders import OpenAIChatCompletionsModel
        
        result = get_model("gemini-pro")
        
        assert isinstance(result, OpenAIChatCompletionsModel)
    
    def test_get_model_default(self):
        """Testa retorno de nome do modelo para modelos padrão."""
        result = get_model("gpt-4o-mini")
        
        assert result == "gpt-4o-mini"


class TestGetResearcher:
    """Testes para função get_researcher."""
    
    @pytest.mark.asyncio
    @patch('src.agents.traders.get_model')
    @patch('src.agents.traders.Agent')
    async def test_get_researcher(self, mock_agent_class, mock_get_model):
        """Testa criação de pesquisador."""
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        
        mock_researcher = MagicMock()
        mock_agent_class.return_value = mock_researcher
        
        mcp_servers = []
        result = await get_researcher(mcp_servers, "gpt-4o-mini")
        
        mock_agent_class.assert_called_once()
        assert result == mock_researcher


class TestGetResearcherTool:
    """Testes para função get_researcher_tool."""
    
    @pytest.mark.asyncio
    @patch('src.agents.traders.get_researcher')
    @patch('src.agents.traders.research_tool')
    async def test_get_researcher_tool(self, mock_research_tool, mock_get_researcher):
        """Testa conversão de pesquisador em ferramenta."""
        mock_researcher = MagicMock()
        mock_tool = MagicMock()
        mock_researcher.as_tool.return_value = mock_tool
        mock_get_researcher.return_value = mock_researcher
        mock_research_tool.return_value = "Research tool description"
        
        mcp_servers = []
        result = await get_researcher_tool(mcp_servers, "gpt-4o-mini")
        
        assert result == mock_tool
        mock_researcher.as_tool.assert_called_once_with(
            tool_name="Researcher",
            tool_description="Research tool description"
        )


class TestTrader:
    """Testes para classe Trader."""
    
    def test_trader_init(self):
        """Testa inicialização de Trader."""
        trader = Trader("Warren", "Buffett", "gpt-4o-mini")
        
        assert trader.name == "Warren"
        assert trader.lastname == "Buffett"
        assert trader.model_name == "gpt-4o-mini"
        assert trader.agent is None
        assert trader.do_trade is True
    
    def test_trader_init_defaults(self):
        """Testa inicialização com valores padrão."""
        trader = Trader("George")
        
        assert trader.name == "George"
        assert trader.lastname == "Trader"
        assert trader.model_name == "gpt-4o-mini"
        assert trader.do_trade is True
    
    @pytest.mark.asyncio
    @patch('src.agents.traders.get_researcher_tool')
    @patch('src.agents.traders.get_model')
    @patch('src.agents.traders.Agent')
    async def test_create_agent(self, mock_agent_class, mock_get_model, mock_get_tool):
        """Testa criação de agente."""
        mock_tool = MagicMock()
        mock_get_tool.return_value = mock_tool
        
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        
        trader = Trader("Warren")
        trader_mcp_servers = []
        researcher_mcp_servers = []
        
        result = await trader.create_agent(trader_mcp_servers, researcher_mcp_servers)
        
        assert result == mock_agent
        assert trader.agent == mock_agent
        mock_agent_class.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.agents.traders.read_accounts_resource')
    async def test_get_account_report(self, mock_read_account):
        """Testa obtenção de relatório de conta."""
        account_data = {
            "name": "warren",
            "balance": 10000.0,
            "strategy": "Test strategy",
            "holdings": {"AAPL": 10},
            "transactions": [],
            "portfolio_value_time_series": []
        }
        mock_read_account.return_value = '{"name": "warren", "balance": 10000.0, "strategy": "Test strategy", "holdings": {"AAPL": 10}, "transactions": [], "portfolio_value_time_series": []}'
        
        trader = Trader("Warren")
        result = await trader.get_account_report()
        
        assert "warren" in result
        assert "10000.0" in result
        assert "portfolio_value_time_series" not in result  # Deve ser removido
    
    @pytest.mark.asyncio
    @patch('src.agents.traders.read_strategy_resource')
    @patch('src.agents.traders.read_accounts_resource')
    @patch('src.agents.traders.get_researcher_tool')
    @patch('src.agents.traders.get_model')
    @patch('src.agents.traders.Agent')
    @patch('src.agents.traders.Runner')
    async def test_run_agent(self, mock_runner, mock_agent_class, mock_get_model, 
                             mock_get_tool, mock_read_account, mock_read_strategy):
        """Testa execução do agente."""
        # Setup mocks
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        
        mock_tool = MagicMock()
        mock_get_tool.return_value = mock_tool
        
        mock_read_account.return_value = '{"name": "warren", "balance": 10000.0}'
        mock_read_strategy.return_value = "Test strategy"
        
        mock_run = AsyncMock()
        mock_runner.run = mock_run
        
        trader = Trader("Warren")
        trader.do_trade = True
        
        await trader.run_agent([], [])
        
        mock_run.assert_called_once()
        assert trader.agent is not None
    
    @pytest.mark.asyncio
    @patch('src.agents.traders.MCPServerStdio')
    @patch('src.agents.traders.trader_mcp_server_params', [{"command": "test", "args": []}])
    @patch('src.agents.traders.researcher_mcp_server_params')
    @patch('src.agents.traders.read_strategy_resource')
    @patch('src.agents.traders.read_accounts_resource')
    @patch('src.agents.traders.get_researcher_tool')
    @patch('src.agents.traders.get_model')
    @patch('src.agents.traders.Agent')
    @patch('src.agents.traders.Runner')
    async def test_run_with_mcp_servers(self, mock_runner, mock_agent_class, 
                                        mock_get_model, mock_get_tool, 
                                        mock_read_account, mock_read_strategy,
                                        mock_researcher_params, mock_mcp_server):
        """Testa execução com servidores MCP."""
        # Setup mocks
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        
        mock_tool = MagicMock()
        mock_get_tool.return_value = mock_tool
        
        mock_read_account.return_value = '{"name": "warren", "balance": 10000.0}'
        mock_read_strategy.return_value = "Test strategy"
        
        mock_run = AsyncMock()
        mock_runner.run = mock_run
        
        mock_researcher_params.return_value = []
        
        # Mock MCP servers como context manager assíncrono
        mock_server_instance = AsyncMock()
        mock_mcp_server.return_value.__aenter__ = AsyncMock(return_value=mock_server_instance)
        mock_mcp_server.return_value.__aexit__ = AsyncMock(return_value=None)
        
        trader = Trader("Warren")
        
        await trader.run_with_mcp_servers()
        
        # Verifica que servidores foram criados (MCPServerStdio foi chamado)
        assert mock_mcp_server.called
    
    @pytest.mark.asyncio
    @patch('src.agents.traders.make_trace_id')
    @patch('src.agents.traders.trace')
    @patch('src.agents.traders.Trader.run_with_mcp_servers')
    async def test_run_with_trace(self, mock_run_mcp, mock_trace, mock_trace_id):
        """Testa execução com tracing."""
        mock_trace_id.return_value = "trace_warren0test"
        
        mock_context = MagicMock()
        mock_trace.return_value.__enter__ = MagicMock(return_value=mock_context)
        mock_trace.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_run_mcp.return_value = AsyncMock()
        
        trader = Trader("Warren")
        trader.do_trade = True
        
        await trader.run_with_trace()
        
        mock_run_mcp.assert_called_once()
        mock_trace.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.agents.traders.Trader.run_with_trace')
    async def test_run_success(self, mock_run_trace):
        """Testa execução bem-sucedida."""
        mock_run_trace.return_value = AsyncMock()
        
        trader = Trader("Warren")
        initial_do_trade = trader.do_trade
        
        await trader.run()
        
        mock_run_trace.assert_called_once()
        # Verifica que do_trade foi alternado
        assert trader.do_trade != initial_do_trade
    
    @pytest.mark.asyncio
    @patch('src.agents.traders.Trader.run_with_trace')
    async def test_run_exception(self, mock_run_trace):
        """Testa tratamento de exceção durante execução."""
        mock_run_trace.side_effect = Exception("Test error")
        
        trader = Trader("Warren")
        initial_do_trade = trader.do_trade
        
        # Não deve lançar exceção
        await trader.run()
        
        # Verifica que do_trade ainda foi alternado mesmo com erro
        assert trader.do_trade != initial_do_trade

