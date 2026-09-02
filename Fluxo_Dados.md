Com base no código-fonte e nas configurações do projeto, aqui está o detalhamento completo dos ativos monitorados, dos dados coletados, da cadeia de produção/consumo (inputs e outputs) e da estrutura das páginas do aplicativo.

### 1. Quais dados são coletados e de quais ativos?

O sistema coleta dados de preço (Abertura, Máxima, Mínima, Fechamento/Último, Variação Percentual e Volume) e preços teóricos de leilão para os seguintes grupos de ativos:

* **Ativos B3 (Ações via MetaTrader 5):** VALE3, PETR4, ITUB4, BBAS3, BBDC4 e B3SA3.


* **Futuros B3 (via MetaTrader 5 e TradingView):** WIN (Mini Índice), WDO (Mini Dólar) e DI1 (Juros DI para 2027 e 2029).


* **ADRs Brasileiras (via Finnhub):** VALE_ADR (VALE), PETR_ADR (PBR), ITUB_ADR (ITUB), BBAS_ADR (BDORY), BBD_ADR (BBD), B3_ADR (BOLSY) e o ETF EWZ.


* **Índices e Futuros Globais (via TradingView Scanner):** S&P 500 E-mini (ES1!), Nasdaq 100 E-mini (NQ1!) e DXY (Índice Dólar).


* **Commodities e Câmbio (via TradingView Scanner):** Minério de Ferro em Singapura (FEF1! e FEF2!), Petróleo WTI (CL1!), Ouro (GOLD), USD/MXN e USD/BRL.


* **Taxa Oficial (via BACEN):** PTAX.


* **Eventos Macroeconômicos (via TradingView API):** Notícias do calendário econômico de médio e alto impacto (2 e 3 estrelas) para o Brasil e EUA.



---

### 2. Cadeia de Produção e Consumo de Dados (Scripts)

O fluxo de dados segue uma ordem estrita de dependência, detalhada pelo mapa do pipeline do sistema (`Gerar_Mapa_Fluxo.py`):

**Coleta e Extração Inicial:**

* **`Coletor.py`**: Consome dados das APIs (TradingView, Finnhub, MT5, BACEN) e gera os arquivos `Coleta_ram.json`, `Coleta_rom-0.json` e `DadosAtivosUnificados.json`.


* **`Coleta_Noticias_Calendario.py`**: Consome a API do TradingView e gera `Noticias_Calendario.json` e `Noticias_Calendario_0900.json`.



**Sanitização e Regras:**

* **`Validador.py`**: Consome o `Coleta_rom-0.json`, padroniza os tickers de 32 ativos e gera o `Dados_Validados.json`.


* **`Rodar_SMC_Regras.py`**: Consome os dados de preço do MT5 para detectar POC, VWAP e Order Blocks, gerando o `AnaliseGraficaSMC_Regras.json`.


* **`Analise_Noticias.py`**: Consome `Noticias_Calendario.json` e gera os alertas de risco em `Noticias_Impacto_Dia.json`.



**Calculadoras Matemáticas (Novos Cálculos):**

* **`Calculadora.py`**: Consome `Dados_Validados.json` para calcular spreads, inclinação da curva DI e indicadores compostos, gerando o `Metricas_Calculadas.json`.


* **`CalculadoraEstimativaAbertura.py`**: Consome `Dados_Validados.json` (e também os níveis institucionais do SMC) para calcular o Cost of Carry, variação teórica e pivôs clássicos, gerando o `EstimativaAbertura.json`.


* **`MapearTendencia15Min.py`**: Consome as memórias rotativas (`Coleta_rom-10.json`, `Coleta_rom-5.json`, `Coleta_rom-0.json`) para analisar variações sequenciais, gerando `Analise_Tendencias.json`.



**Motores de Decisão (Core Engines):**

* **`v2_rodar_decisao_completa.py` / `Engine_Vies.py**`: Consome os vários JSONs do pipeline (EstimativaAbertura, Metricas, Noticias e Ativos) para calcular o viés institucional e níveis operacionais, gerando as saídas `Decisao_V2.json` (e `Decisao_Core.json` na V1).



**Consolidação Final:**

* **`Gerar_Resultado_Operacional_Abertura.py`**: Compilador que consome `Metricas_Calculadas.json`, `EstimativaAbertura.json`, `Decisao_V2.json`, `DadosAtivosUnificados.json`, `Analise_Tendencias.json` e `Noticias_Calendario_0900.json`, consolidando tudo em `Resultado_Calculadora_Operacional_Abertura.json`.


* **`Gerar_Relatorio_Mensagem.py`**: Consome `EstimativaAbertura.json` e o ecossistema consolidado para formatar o texto humano no arquivo `Relatorio_Executivo.md`.



---

### 3. O que as Páginas (Frontend) Consomem e Apresentam

A interface visual do aplicativo é orquestrada pelo arquivo `app_home.py` (usando Streamlit), que separa a aplicação em três vertentes principais no menu:

**A. Bloco "Decisão V2 (oficial)"**

* **`1.1_dashboard_v2.py` (Dashboard V2):** Apresenta o painel principal consolidado da versão atualizada. Ele obrigatoriamente consome o arquivo mestre de inteligência direcional `Decisao_V2.json` gerado pelo orquestrador.


* **`1.2_comparador.py` (Comparador V1 × V2):** Apresenta a comparação de motores lógicos.


* **`1.3_analise_detalhada.py` (Análise Detalhada):** Explora a fundo as métricas da tomada de decisão.


* **`5.3_⚙️_Core_Engine.py`:** Apresenta o motor principal de cálculo por trás da Decisão V2.



**B. Bloco "Operacional"**
As páginas contidas na pasta principal `pages/` rodam em abas independentes e consomem partes específicas dos dados computados:

* **`3.2_⚡_Monitor_Abertura_Leilao_V3.2.py`:** Monitora ao vivo, consumindo os preços teóricos do book enviados do MT5.


* **`3.3_📊_Acoes_e_ADRs.py`:** Apresenta a comparação direta entre as coletas locais (VALE3, PETR4) e os ADRs lá fora.


* **`6.2_📅_Noticias.py`:** Consome o JSON `Noticias_Impacto_Dia.json` / `Noticias_Calendario.json` para apresentar o termômetro macro de risco.


* **`7.1_📊_SMC_Regras.py`:** Consome a tabela de dados em `AnaliseGraficaSMC_Regras.json` para expor o Order Flow e liquidez institucional.


* **`8.2_🔢_Calculadora.py`:** Apresenta e consome os spreads, curva de juros e deltas computados pela `Calculadora.py` e extraídos de `Metricas_Calculadas.json`.



**C. Bloco "Legado (somente referência)"**

* Páginas como **`1.2_🔮_Previsao_Inteligente_Abertura.py`** e **`2.0_📈_Previsao_Abertura_WINFUT.py`**, que exibem os painéis antigos baseados na V1 (consumindo prioritariamente `Decisao_Core.json`).