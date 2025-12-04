# 🏛️ Autonomous Traders - Trading Floor Simulation

Sistema completo de simulação de trading floor com 4 traders autônomos, cada um com sua própria estratégia de investimento inspirada em grandes nomes do mercado financeiro.

## 📋 Sobre o Projeto

Este projeto demonstra o poder de **agentes autônomos** usando **Model Context Protocol (MCP)** para criar um sistema de trading simulado onde múltiplos traders tomam decisões independentes baseadas em pesquisa de mercado, análise de dados e suas estratégias pessoais.

### Características Principais

- **4 Traders Autônomos**: Warren, George, Ray e Cathie
- **Estratégias Únicas**: Cada trader inspirado em grandes investidores
- **Interface Visual**: UI em tempo real para monitorar traders
- **Tracing Customizado**: Captura e exibe pensamentos dos traders
- **Múltiplos Modelos**: Suporte para diferentes modelos de IA (opcional)
- **6 Servidores MCP**: Integração com 44 ferramentas e 2 recursos

## 🏗️ Estrutura do Projeto

```
traders/
├── src/
│   ├── core/           # Lógica de negócios e servidores MCP
│   ├── agents/         # Agentes traders e orquestração
│   ├── ui/             # Interface de usuário (Gradio)
│   └── utils/          # Utilitários (tracing, templates, config)
├── config/             # Arquivos de configuração
├── data/               # Dados persistentes (banco, memória)
└── docs/               # Documentação adicional
```

## 🚀 Instalação

### Pré-requisitos

- Python 3.8+
- Node.js e npm (para servidores MCP JavaScript)
- Chaves de API:
  - OpenAI API Key
  - Polygon API Key (opcional, para dados de mercado)
  - Brave API Key (para pesquisa web)
  - DeepSeek, OpenRouter, Google, Grok (opcional, para múltiplos modelos)

### Passos

1. **Clone o repositório** (ou navegue até a pasta)

2. **Instale as dependências**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure as variáveis de ambiente**

   Copie `config/.env.example` para `.env` na raiz do projeto e preencha:
   
   ```env
   # Obrigatórias
   OPENAI_API_KEY=your_openai_key
   BRAVE_API_KEY=your_brave_key
   
   # Opcionais
   POLYGON_API_KEY=your_polygon_key
   POLYGON_PLAN=free  # ou "paid" ou "realtime"
   
   # Para múltiplos modelos (opcional)
   USE_MANY_MODELS=False
   DEEPSEEK_API_KEY=your_key
   OPENROUTER_API_KEY=your_key
   GOOGLE_API_KEY=your_key
   GROK_API_KEY=your_key
   
   # Configurações de execução
   RUN_EVERY_N_MINUTES=60
   RUN_EVEN_WHEN_MARKET_IS_CLOSED=False
   ```

4. **Reset traders (opcional)**

   Para começar do zero:
   ```bash
   python -m src.agents.reset
   ```

## 🎯 Como Usar

### Opção 1: Interface de Usuário

```bash
cd traders
python -m src.ui.app
```

Acesse: `http://localhost:7860`

### Opção 2: Trading Floor (Motor)

```bash
cd traders
python -m src.agents.trading_floor
```

Isso iniciará o loop principal que executa os traders periodicamente.

### Opção 3: Ambos Simultaneamente

**Terminal 1** (UI):
```bash
python -m src.ui.app
```

**Terminal 2** (Trading Floor):
```bash
python -m src.agents.trading_floor
```

## 👥 Os Quatro Traders

### Warren (Warren Buffett)
- **Estratégia**: Investidor de valor, longo prazo
- **Modelo**: GPT 4.1 Mini (ou gpt-4o-mini)
- **Características**: Paciência, análise fundamental, foco em valor intrínseco

### George (George Soros)
- **Estratégia**: Trader macro agressivo, contrarian
- **Modelo**: DeepSeek V3 (ou gpt-4o-mini)
- **Características**: Apostas ousadas, timing decisivo, eventos macroeconômicos

### Ray (Ray Dalio)
- **Estratégia**: Sistemático, baseado em princípios, diversificação
- **Modelo**: Gemini 2.5 Flash (ou gpt-4o-mini)
- **Características**: Risk parity, indicadores macro, preservação de capital

### Cathie (Cathie Wood)
- **Estratégia**: Inovação disruptiva, Crypto ETFs
- **Modelo**: Grok 3 Mini (ou gpt-4o-mini)
- **Características**: Alta volatilidade, posições ousadas, tecnologia disruptiva

## 🔧 Arquitetura

### Servidores MCP

1. **Accounts Server**: Gerencia contas dos traders
2. **Push Server**: Envia notificações
3. **Market Server**: Fornece dados de mercado
4. **Fetch Server**: Busca páginas web
5. **Brave Search Server**: Pesquisa na web
6. **Memory Server**: Memória persistente (libSQL)

### Componentes Principais

- **`trading_floor.py`**: Loop principal que orquestra execução
- **`traders.py`**: Classe Trader que encapsula lógica
- **`tracers.py`**: Sistema de tracing customizado
- **`app.py`**: Interface de usuário Gradio
- **`reset.py`**: Inicialização de estratégias

## 📊 Funcionalidades

### Interface de Usuário

- **4 Colunas**: Uma para cada trader
- **Gráficos**: Valor do portfólio ao longo do tempo
- **Logs em Tempo Real**: Pensamentos e ações dos traders
- **Holdings**: Ações atualmente possuídas
- **Performance**: P&L e métricas

### Sistema de Tracing

- **Captura automática**: Todos os eventos dos traders
- **Armazenamento**: Banco de dados SQLite
- **Visualização**: Exibido na UI em tempo real
- **Extensível**: Pode ser conectado a LangSmith, Weights & Biases, etc.

### Autonomia dos Traders

- **Evolução de estratégia**: Podem mudar estratégia ao longo do tempo
- **Decisões independentes**: Cada trader toma suas próprias decisões
- **Memória persistente**: Aprendem com experiências passadas

## ⚙️ Configurações

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `RUN_EVERY_N_MINUTES` | 60 | Frequência de execução (minutos) |
| `RUN_EVEN_WHEN_MARKET_IS_CLOSED` | False | Executar mesmo com mercado fechado |
| `USE_MANY_MODELS` | False | Usar diferentes modelos para cada trader |
| `POLYGON_PLAN` | free | Plano Polygon (free/paid/realtime) |

### Planos Polygon

- **free**: Dados EOD (End of Day) - cache otimizado
- **paid**: Dados em tempo real com delay de 15min
- **realtime**: Dados em tempo real completos

## 📁 Estrutura de Arquivos

```
src/
├── core/
│   ├── accounts.py              # Lógica de contas
│   ├── accounts_server.py        # Servidor MCP de contas
│   ├── accounts_client.py        # Cliente MCP de contas
│   ├── database.py               # Persistência SQLite
│   ├── market.py                 # Obtenção de preços
│   ├── market_server.py          # Servidor MCP de mercado
│   └── push_server.py            # Servidor MCP de notificações
├── agents/
│   ├── traders.py                # Classe Trader
│   ├── trading_floor.py          # Loop principal
│   └── reset.py                  # Inicialização
├── ui/
│   ├── app.py                    # Interface Gradio
│   └── util.py                   # Utilitários UI
└── utils/
    ├── tracers.py                 # Tracing customizado
    ├── templates.py               # Templates de prompts
    └── mcp_params.py             # Configuração MCP
```

## 🐛 Troubleshooting

### Erro de importação

Se houver erros de importação, certifique-se de executar da raiz do projeto:
```bash
cd traders
python -m src.agents.trading_floor
```

### Banco de dados não encontrado

O banco `accounts.db` será criado automaticamente na primeira execução.

### Servidores MCP não iniciam

- Verifique se Node.js está instalado: `node --version`
- Verifique se `npx` está disponível: `npx --version`
- Para WSL, veja `SETUP-node.md` no projeto principal

### API Keys não funcionam

- Verifique se `.env` está na raiz do projeto `traders/`
- Use `load_dotenv(override=True)` se necessário
- Verifique se chaves estão corretas no dashboard das APIs

## 📝 Notas Importantes

⚠️ **AVISO**: Este é um projeto **experimental e educacional**. 

- ❌ **NÃO use para trading real**
- ❌ **NÃO invista dinheiro real baseado nisso**
- ✅ **Use apenas para aprendizado e demonstração**

## 🤝 Contribuindo

Este projeto faz parte de um curso educacional. Sinta-se à vontade para:

1. Adicionar novos servidores MCP
2. Criar novos traders com estratégias diferentes
3. Melhorar a UI
4. Adicionar funcionalidades

## 📚 Documentação Adicional

- Veja `docs/` para documentação detalhada
- Consulte os notebooks `4_lab4.ipynb` e `5_lab5.ipynb` para contexto
- Veja explicações em `/docs/mcp_lab5_explicacao.md`

## 📄 Licença

Este projeto faz parte de um conjunto maior de exemplos de uso de MCP. Consulte a licença do projeto principal.

---

**Desenvolvido com ❤️ usando FastAPI, MCP, OpenAI Agents SDK e Gradio**

