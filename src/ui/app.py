import gradio as gr
from src.ui.util import css, js, Color
import pandas as pd
from src.agents.trading_floor import names, lastnames, short_model_names
import plotly.express as px
from src.core.accounts import Account
from src.core.database import read_log

mapper = {
    "trace": Color.WHITE,
    "agent": Color.CYAN,
    "function": Color.GREEN,
    "generation": Color.YELLOW,
    "response": Color.MAGENTA,
    "account": Color.RED,
}


class Trader:
    def __init__(self, name: str, lastname: str, model_name: str):
        self.name = name
        self.lastname = lastname
        self.model_name = model_name
        self.account = Account.get(name)

    def reload(self):
        self.account = Account.get(self.name)

    def get_title(self) -> str:
        return f"<div style='text-align: center;font-size:34px;'>{self.name}<span style='color:#ccc;font-size:24px;'> ({self.model_name}) - {self.lastname}</span></div>"

    def get_strategy(self) -> str:
        return self.account.get_strategy()

    def get_portfolio_value_df(self) -> pd.DataFrame:
        df = pd.DataFrame(self.account.portfolio_value_time_series, columns=["datetime", "value"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        return df

    def get_portfolio_value_chart(self):
        df = self.get_portfolio_value_df()
        fig = px.line(df, x="datetime", y="value")
        margin = dict(l=40, r=20, t=20, b=40)
        fig.update_layout(
            height=300,
            margin=margin,
            xaxis_title=None,
            yaxis_title=None,
            paper_bgcolor="#bbb",
            plot_bgcolor="#dde",
        )
        fig.update_xaxes(tickformat="%m/%d", tickangle=45, tickfont=dict(size=8))
        fig.update_yaxes(tickfont=dict(size=8), tickformat=",.0f")
        return fig

    def get_holdings_df(self) -> pd.DataFrame:
        """Convert holdings to DataFrame for display"""
        holdings = self.account.get_holdings()
        if not holdings:
            return pd.DataFrame(columns=["Symbol", "Quantity"])

        df = pd.DataFrame(
            [{"Symbol": symbol, "Quantity": quantity} for symbol, quantity in holdings.items()]
        )
        return df

    def get_transactions_df(self) -> pd.DataFrame:
        """Convert transactions to DataFrame for display"""
        transactions = self.account.list_transactions()
        if not transactions:
            return pd.DataFrame(columns=["Timestamp", "Symbol", "Quantity", "Price", "Rationale"])

        return pd.DataFrame(transactions)

    def get_portfolio_value(self) -> str:
        """Calculate total portfolio value based on current prices"""
        portfolio_value = self.account.calculate_portfolio_value() or 0.0
        pnl = self.account.calculate_profit_loss(portfolio_value) or 0.0
        color = "green" if pnl >= 0 else "red"
        emoji = "⬆" if pnl >= 0 else "⬇"
        return f"<div style='text-align: center;background-color:{color};'><span style='font-size:32px'>${portfolio_value:,.0f}</span><span style='font-size:24px'>&nbsp;&nbsp;&nbsp;{emoji}&nbsp;${pnl:,.0f}</span></div>"

    def get_logs(self, previous=None) -> str:
        logs = read_log(self.name, last_n=13)
        response = ""
        for log in logs:
            timestamp, type, message = log
            color = mapper.get(type, Color.WHITE).value
            response += f"<span style='color:{color}'>{timestamp} : [{type}] {message}</span><br/>"
        response = f"<div style='height:250px; overflow-y:auto;'>{response}</div>"
        if response != previous:
            return response
        return gr.update()


class TraderView:
    def __init__(self, trader: Trader):
        self.trader = trader
        self.portfolio_value = None
        self.chart = None
        self.holdings_table = None
        self.transactions_table = None

    def make_ui(self):
        with gr.Column():
            gr.HTML(self.trader.get_title())
            with gr.Row():
                self.portfolio_value = gr.HTML(self.trader.get_portfolio_value)
            with gr.Row():
                self.chart = gr.Plot(
                    self.trader.get_portfolio_value_chart, container=True, show_label=False
                )
            with gr.Row(variant="panel"):
                self.log = gr.HTML(self.trader.get_logs)
            with gr.Row():
                self.holdings_table = gr.Dataframe(
                    value=self.trader.get_holdings_df,
                    label="Holdings",
                    headers=["Symbol", "Quantity"],
                    row_count=(5, "dynamic"),
                    col_count=2,
                    max_height=300,
                    elem_classes=["dataframe-fix-small"],
                )
            with gr.Row():
                self.transactions_table = gr.Dataframe(
                    value=self.trader.get_transactions_df,
                    label="Recent Transactions",
                    headers=["Timestamp", "Symbol", "Quantity", "Price", "Rationale"],
                    row_count=(5, "dynamic"),
                    col_count=5,
                    max_height=300,
                    elem_classes=["dataframe-fix"],
                )

        timer = gr.Timer(value=120)
        timer.tick(
            fn=self.refresh,
            inputs=[],
            outputs=[
                self.portfolio_value,
                self.chart,
                self.holdings_table,
                self.transactions_table,
            ],
            show_progress="hidden",
            queue=False,
        )
        log_timer = gr.Timer(value=0.5)
        log_timer.tick(
            fn=self.trader.get_logs,
            inputs=[self.log],
            outputs=[self.log],
            show_progress="hidden",
            queue=False,
        )

    def refresh(self):
        self.trader.reload()
        return (
            self.trader.get_portfolio_value(),
            self.trader.get_portfolio_value_chart(),
            self.trader.get_holdings_df(),
            self.trader.get_transactions_df(),
        )


# Main UI construction
def create_ui():
    """Create the main Gradio UI for the trading simulation"""

    traders = [
        Trader(trader_name, lastname, model_name)
        for trader_name, lastname, model_name in zip(names, lastnames, short_model_names)
    ]
    trader_views = [TraderView(trader) for trader in traders]

    with gr.Blocks(
        title="Traders", css=css, js=js, theme=gr.themes.Default(primary_hue="sky"), fill_width=True
    ) as ui:
        with gr.Row():
            for trader_view in trader_views:
                trader_view.make_ui()

    return ui


if __name__ == "__main__":
    ui = create_ui()
    
    # Configuração de acesso:
    # - server_name="0.0.0.0": Permite acesso na rede local (além de localhost)
    # - share=True: Cria link público temporário (acessível de qualquer lugar)
    # - share=False: Apenas acesso local/rede local
    #
    # Para permitir acesso externo via link público:
    # - share=True cria link como: https://xxxxx.gradio.live
    # - Link expira quando você fecha o app
    # - Qualquer pessoa com o link pode acessar
    #
    # Para apenas rede local (sem link público):
    # - share=False e server_name="0.0.0.0"
    # - Compartilhe seu IP local: http://SEU_IP:7860
    #
    # Para apenas acesso local (padrão):
    # - share=False e server_name="127.0.0.1"
    # - Apenas você pode acessar: http://127.0.0.1:7860
    
    # Configuração padrão: link público habilitado
    # Mude share=False se não quiser link público
    share_public_link = True  # True = link público, False = apenas rede local/localhost
    
    # Porta padrão do servidor
    # Se a porta estiver ocupada, Gradio tentará automaticamente portas próximas
    # Ou defina server_port=None para Gradio escolher automaticamente
    default_port = 7860
    
    try:
        ui.launch(
            inbrowser=True,  # Tenta abrir navegador automaticamente
            server_name="0.0.0.0",  # Permite acesso na rede local
            server_port=default_port,  # Porta padrão (Gradio tentará outras se ocupada)
            share=share_public_link  # True = cria link público, False = apenas rede local
        )
    except OSError as e:
        # Se a porta estiver ocupada, tenta sem especificar porta (Gradio escolhe automaticamente)
        if "port" in str(e).lower() or "7860" in str(e):
            print(f"Porta {default_port} está ocupada. Tentando porta automática...")
            try:
                ui.launch(
                    inbrowser=True,
                    server_name="0.0.0.0",
                    server_port=None,  # Gradio escolhe porta livre automaticamente
                    share=share_public_link
                )
            except Exception as e2:
                print(f"Could not open browser automatically: {e2}")
                if share_public_link:
                    print("App iniciado com link público. O link será exibido acima.")
                    print("Compartilhe o link para permitir acesso externo.")
                ui.launch(
                    inbrowser=False,
                    server_name="0.0.0.0",
                    server_port=None,  # Gradio escolhe porta livre automaticamente
                    share=share_public_link
                )
        else:
            raise
    except Exception as e:
        # Se falhar ao abrir navegador (comum no WSL), inicia sem abrir automaticamente
        print(f"Could not open browser automatically: {e}")
        if share_public_link:
            print("App iniciado com link público. O link será exibido acima.")
            print("Compartilhe o link para permitir acesso externo.")
        else:
            print("Please open http://0.0.0.0:7860 in your browser manually")
            print("Or use your local IP address if accessing from another device on the network")
        try:
            ui.launch(
                inbrowser=False,  # Não tenta abrir navegador
                server_name="0.0.0.0",  # Permite acesso na rede local
                server_port=default_port,
                share=share_public_link  # True = cria link público, False = apenas rede local
            )
        except OSError:
            # Se porta ainda estiver ocupada, usa porta automática
            print(f"Porta {default_port} ainda ocupada. Usando porta automática...")
            ui.launch(
                inbrowser=False,
                server_name="0.0.0.0",
                server_port=None,  # Gradio escolhe porta livre automaticamente
                share=share_public_link
            )
