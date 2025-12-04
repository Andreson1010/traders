"""
Módulo de gerenciamento de contas de trading para o projeto Autonomous Traders.

Este módulo implementa a lógica de negócios para contas de traders, incluindo:
- Gerenciamento de saldo e holdings
- Execução de compras e vendas de ações
- Cálculo de valor de portfólio e P&L
- Persistência de dados via database
- Rastreamento de transações e histórico
"""

from pydantic import BaseModel
import json
from dotenv import load_dotenv
from datetime import datetime
from src.core.market import get_share_price
from src.core.database import write_account, read_account, write_log

load_dotenv(override=True)

# Constantes de configuração
INITIAL_BALANCE = 10_000.0  # Saldo inicial para cada trader ($10,000)
SPREAD = 0.002  # Spread de 0.2% aplicado em compras (aumenta preço) e vendas (reduz preço)


class Transaction(BaseModel):
    """
    Representa uma transação de compra ou venda de ações.
    
    Objetivo: Modelar uma operação individual de trading com todos os detalhes necessários
    para auditoria e análise posterior.
    
    Atributos:
        symbol: Ticker da ação (ex: "AAPL", "TSLA")
        quantity: Quantidade de ações (positivo para compra, negativo para venda)
        price: Preço por ação no momento da transação (já com spread aplicado)
        timestamp: Data e hora da transação
        rationale: Justificativa da transação (fornecida pelo trader agent)
    """
    symbol: str
    quantity: int
    price: float
    timestamp: str
    rationale: str

    def total(self) -> float:
        """
        Calcula o valor total da transação.
        
        Objetivo: Multiplicar quantidade pelo preço para obter o custo/receita total.
        Retorna valor absoluto para facilitar cálculos de P&L.
        """
        return self.quantity * self.price
    
    def __repr__(self):
        """
        Representação legível da transação.
        
        Objetivo: Facilitar debugging e visualização de transações.
        """
        return f"{abs(self.quantity)} shares of {self.symbol} at {self.price} each."


class Account(BaseModel):
    """
    Classe principal que representa uma conta de trader.
    
    Objetivo: Gerenciar todo o estado e operações de uma conta de trading, incluindo:
    - Saldo em dinheiro
    - Holdings (ações possuídas)
    - Histórico de transações
    - Estratégia de investimento
    - Cálculos de valor de portfólio e P&L
    
    Esta classe é usada pelo accounts_server.py para expor funcionalidades via MCP.
    """
    name: str
    balance: float
    strategy: str
    holdings: dict[str, int]  # {symbol: quantity} - ações possuídas
    transactions: list[Transaction]  # Histórico completo de transações
    portfolio_value_time_series: list[tuple[str, float]]  # [(timestamp, value), ...]

    @classmethod
    def get(cls, name: str):
        """
        Factory method para obter ou criar uma conta.
        
        Objetivo: 
        - Buscar conta existente no banco de dados
        - Criar nova conta com valores padrão se não existir
        - Garantir que sempre retorna uma instância válida
        
        Fluxo:
        1. Tenta ler do banco de dados
        2. Se não existir, cria com valores iniciais
        3. Salva no banco e retorna instância
        """
        fields = read_account(name.lower())
        if not fields:
            fields = {
                "name": name.lower(),
                "balance": INITIAL_BALANCE,
                "strategy": "",
                "holdings": {},
                "transactions": [],
                "portfolio_value_time_series": []
            }
            write_account(name, fields)
        return cls(**fields)
    
    
    def save(self):
        """
        Salva o estado atual da conta no banco de dados.
        
        Objetivo: Persistir mudanças (saldo, holdings, transações) para que
        sejam mantidas entre execuções do sistema.
        
        Chamado automaticamente após cada operação que modifica a conta.
        """
        write_account(self.name.lower(), self.model_dump())

    def reset(self, strategy: str):
        """
        Reseta a conta para estado inicial com nova estratégia.
        
        Objetivo: Permitir reiniciar um trader com nova estratégia, útil para:
        - Testar diferentes estratégias
        - Reiniciar simulações
        - Resetar após período de trading
        
        Ações:
        - Restaura saldo inicial ($10,000)
        - Limpa holdings e transações
        - Define nova estratégia
        - Salva estado resetado
        """
        self.balance = INITIAL_BALANCE
        self.strategy = strategy
        self.holdings = {}
        self.transactions = []
        self.portfolio_value_time_series = []
        self.save()

    def deposit(self, amount: float):
        """
        Deposita fundos na conta.
        
        Objetivo: Adicionar dinheiro à conta (útil para simulações ou ajustes).
        
        Validações:
        - Valor deve ser positivo
        - Atualiza saldo e persiste mudança
        """
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self.balance += amount
        print(f"Deposited ${amount}. New balance: ${self.balance}")
        self.save()

    def withdraw(self, amount: float):
        """
        Retira fundos da conta.
        
        Objetivo: Remover dinheiro da conta, garantindo que saldo não fique negativo.
        
        Validações:
        - Verifica se há fundos suficientes
        - Atualiza saldo e persiste mudança
        """
        if amount > self.balance:
            raise ValueError("Insufficient funds for withdrawal.")
        self.balance -= amount
        print(f"Withdraw ${amount}. New balance: ${self.balance}")
        self.save()

    def buy_shares(self, symbol: str, quantity: int, rationale: str) -> str:
        """
        Compra ações de uma empresa.
        
        Objetivo: Executar ordem de compra, que é a operação principal do trader agent.
        
        Processo:
        1. Obtém preço atual da ação via market.get_share_price()
        2. Aplica spread de compra (aumenta preço em 0.2%)
        3. Calcula custo total
        4. Valida se há fundos suficientes
        5. Atualiza holdings (adiciona ações)
        6. Registra transação com timestamp e rationale
        7. Deduz custo do saldo
        8. Salva estado e loga operação
        9. Retorna relatório atualizado
        
        Validações:
        - Fundos suficientes
        - Símbolo válido (preço != 0)
        
        Retorna: String com relatório completo da conta após a compra.
        """
        price = get_share_price(symbol)
        buy_price = price * (1 + SPREAD)  # Aplica spread de compra
        total_cost = buy_price * quantity
        
        if total_cost > self.balance:
            raise ValueError("Insufficient funds to buy shares.")
        elif price==0:
            raise ValueError(f"Unrecognized symbol {symbol}")
        
        # Update holdings
        self.holdings[symbol] = self.holdings.get(symbol, 0) + quantity
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Record transaction
        transaction = Transaction(symbol=symbol, quantity=quantity, price=buy_price, timestamp=timestamp, rationale=rationale)
        self.transactions.append(transaction)
        
        # Update balance
        self.balance -= total_cost
        self.save()
        write_log(self.name, "account", f"Bought {quantity} of {symbol}")
        return "Completed. Latest details:\n" + self.report()

    def sell_shares(self, symbol: str, quantity: int, rationale: str) -> str:
        """
        Vende ações de uma empresa.
        
        Objetivo: Executar ordem de venda, permitindo ao trader realizar lucros ou cortar perdas.
        
        Processo:
        1. Valida se há ações suficientes para vender
        2. Obtém preço atual da ação
        3. Aplica spread de venda (reduz preço em 0.2%)
        4. Calcula receita total
        5. Atualiza holdings (remove ações)
        6. Remove símbolo se quantidade chegar a zero
        7. Registra transação (quantidade negativa para identificar venda)
        8. Adiciona receita ao saldo
        9. Salva estado e loga operação
        10. Retorna relatório atualizado
        
        Validações:
        - Quantidade suficiente de ações possuídas
        
        Retorna: String com relatório completo da conta após a venda.
        """
        if self.holdings.get(symbol, 0) < quantity:
            raise ValueError(f"Cannot sell {quantity} shares of {symbol}. Not enough shares held.")
        
        price = get_share_price(symbol)
        sell_price = price * (1 - SPREAD)  # Aplica spread de venda
        total_proceeds = sell_price * quantity
        
        # Update holdings
        self.holdings[symbol] -= quantity
        
        # If shares are completely sold, remove from holdings
        if self.holdings[symbol] == 0:
            del self.holdings[symbol]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Record transaction
        transaction = Transaction(symbol=symbol, quantity=-quantity, price=sell_price, timestamp=timestamp, rationale=rationale)  # negative quantity for sell
        self.transactions.append(transaction)

        # Update balance
        self.balance += total_proceeds
        self.save()
        write_log(self.name, "account", f"Sold {quantity} of {symbol}")
        return "Completed. Latest details:\n" + self.report()

    def calculate_portfolio_value(self):
        """
        Calcula o valor total do portfólio.
        
        Objetivo: Determinar o valor atual de todos os ativos (dinheiro + ações).
        
        Cálculo:
        - Saldo em dinheiro
        - + (preço atual de cada ação × quantidade possuída)
        
        Retorna: Valor total do portfólio em dólares.
        """
        total_value = self.balance
        for symbol, quantity in self.holdings.items():
            total_value += get_share_price(symbol) * quantity
        return total_value

    def calculate_profit_loss(self, portfolio_value: float):
        """
        Calcula lucro ou prejuízo (P&L) desde o início.
        
        Objetivo: Determinar performance do trader comparando valor atual com investimento inicial.
        
        Cálculo:
        - Valor total do portfólio atual
        - - (soma de todas as transações de compra)
        - - saldo atual em dinheiro
        = P&L líquido
        
        Retorna: Valor positivo (lucro) ou negativo (prejuízo).
        """
        initial_spend = sum(transaction.total() for transaction in self.transactions)
        return portfolio_value - initial_spend - self.balance

    def get_holdings(self):
        """
        Retorna as ações atualmente possuídas.
        
        Objetivo: Fornecer snapshot atual dos holdings para o trader agent.
        
        Retorna: Dicionário {symbol: quantity} com todas as ações possuídas.
        """
        return self.holdings

    def get_profit_loss(self):
        """
        Retorna o P&L atual.
        
        Objetivo: Fornecer métrica de performance para o trader agent.
        
        Calcula o valor do portfólio primeiro e então o P&L.
        """
        portfolio_value = self.calculate_portfolio_value()
        return self.calculate_profit_loss(portfolio_value)

    def list_transactions(self):
        """
        Lista todas as transações realizadas.
        
        Objetivo: Fornecer histórico completo para análise e auditoria.
        
        Retorna: Lista de dicionários com todas as transações (formato JSON).
        """
        return [transaction.model_dump() for transaction in self.transactions]
    
    def report(self) -> str:
        """
        Gera relatório completo da conta em formato JSON.
        
        Objetivo: Fornecer snapshot completo do estado da conta, incluindo:
        - Todos os dados da conta
        - Valor total do portfólio
        - P&L calculado
        - Timestamp do relatório
        
        Processo:
        1. Calcula valor do portfólio
        2. Adiciona ponto à série temporal
        3. Calcula P&L
        4. Serializa tudo em JSON
        5. Loga a operação
        
        Retorna: String JSON com todos os dados da conta.
        Usado por: accounts_server.py para expor via recurso MCP.
        """
        portfolio_value = self.calculate_portfolio_value()
        self.portfolio_value_time_series.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), portfolio_value))
        self.save()
        pnl = self.calculate_profit_loss(portfolio_value)
        data = self.model_dump()
        data["total_portfolio_value"] = portfolio_value
        data["total_profit_loss"] = pnl
        write_log(self.name, "account", f"Retrieved account details")
        return json.dumps(data)
    
    def get_strategy(self) -> str:
        """
        Retorna a estratégia de investimento atual.
        
        Objetivo: Permitir que o trader agent leia sua estratégia (usado como recurso MCP).
        
        Retorna: String com a descrição da estratégia.
        """
        write_log(self.name, "account", f"Retrieved strategy")
        return self.strategy
    
    def change_strategy(self, strategy: str) -> str:
        """
        Permite ao trader alterar sua estratégia de investimento.
        
        Objetivo: Dar autonomia ao trader agent para evoluir sua estratégia baseado
        em aprendizado ou mudanças de mercado.
        
        Processo:
        1. Atualiza estratégia
        2. Salva no banco de dados
        3. Loga a mudança
        
        Retorna: Confirmação da mudança.
        """
        self.strategy = strategy
        self.save()
        write_log(self.name, "account", f"Changed strategy")
        return "Changed strategy"

# Example of usage:
if __name__ == "__main__":
    account = Account("John Doe")
    account.deposit(1000)
    account.buy_shares("AAPL", 5)
    account.sell_shares("AAPL", 2)
    print(f"Current Holdings: {account.get_holdings()}")
    print(f"Total Portfolio Value: {account.calculate_portfolio_value()}")
    print(f"Profit/Loss: {account.get_profit_loss()}")
    print(f"Transactions: {account.list_transactions()}")