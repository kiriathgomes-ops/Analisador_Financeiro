# Arquitetura do Núcleo V2 (Core)

O V2 foi construído utilizando o padrão de **Clean Architecture** (Arquitetura Limpa). O objetivo é separar a lógica de negócios (como o robô pensa e decide) da infraestrutura (de onde os dados vêm). 

A estrutura se divide em 3 camadas principais: **Contracts**, **Services** e **Engines**, orquestradas pelo **Orchestrator**.

---

## 1. Contracts (Contratos de Dados)
**Local:** `v2/core/contracts/`

Os *Contracts* são as "caixas" padronizadas de dados (usando `@dataclass`). Eles garantem que os motores recebam as informações no formato exato, com os tipos corretos (float, bool, list), evitando erros de `None` ou formatação.

| Arquivo | Papel / Responsabilidade |
| :--- | :--- |
| **`market_context.py`** | Define o `MarketContext` (foto do mercado). Contém os `AtivoSnapshot` (preço e variação) de WIN, WDO, VIX, S&P, DXY, etc., além de indicadores compostos. |
| **`prediction_context.py`** | Define o `PredictionContext`. É a tradução do output do **NOVO_MOTOR** (gap, cenário, faixa provável e score de abertura). |
| **`vision_context.py`** | Define o `VisionContext`. Contém os dados estruturais do SMC (BOS, CHOCH, Order Blocks, FVGs, alvos e stop sugeridos). |
| **`news_context.py`** | Define o `NewsContext`. Armazena o impacto das notícias do dia, classificações de risco e alertas (ex: notícia 3 estrelas às 09:00). |
| **`win_session.py`** | Define o `WinSession`. Um contrato profundo usado especificamente pelo Motor de Cenários de Abertura, agrupando metadados, preços de referência, distâncias, gap, pivôs e contexto macro. |
| **`decision_context.py`** | Define o `DecisionContext`. É o output final da mesa. Contém o veredito (COMPRA/VENDA), confiança, entrada, stop, alvos e os motivos/riscos. |

---

## 2. Services (Serviços de Infraestrutura)
**Local:** `v2/core/services/`

Os *Services* são os "garçons" do sistema. Eles não tomam decisões matemáticas. A função deles é ir até a pasta `Coletas/` (ou APIs), ler os arquivos JSON/CSV brutos, limpar os dados e transformá-los em um *Contract*.

| Arquivo | Papel / Responsabilidade |
| :--- | :--- |
| **`market_service.py`** | Lê `DadosAtivosUnificados.json` e `Metricas_Calculadas.json`. Monta o `MarketContext`. Possui fallbacks caso o WIN_FUT venha zerado. |
| **`prediction_service.py`** | Instancia o `NOVO_MOTOR_PREVISAO_ABERTURA`. Extrai as probabilidades de cenário e o score direcional, e monta o `PredictionContext`. |
| **`vision_service.py`** | Lê o `AnaliseGraficaSMC_Regras.json` (Motor SMC). Monta o `VisionContext` com os dados reais da estrutura de preço. |
| **`news_service.py`** | Lê o `Noticias_Impacto_Dia.json`. Monta o `NewsContext` com os alertas de volatilidade e o calendário. |
| **`leilao_service.py`** | Lê o arquivo CSV do OCR (`preco_teorico_win_fluxo.csv`). Filtra *outliers* (preços absurdos) e calcula o preço do leilão usando a mediana para evitar ruídos. |
| **`win_session_builder.py`** | Lê todos os JSONs simultaneamente e monta o `WinSession`. É a "fonte da verdade" para o motor de cenários de abertura. |
| **`session_history.py`** | Pega o `WinSession` e serializa para salvar em `Coletas/Historico_Aberturas/`. Cria o histórico diário para backtests futuros. |
| **`vision_ai_service.py`** | Conecta na API da Groq (Llama Vision / Qwen). Lê imagens de gráficos e usa IA para identificar OBs e FVGs visuais. |

---

## 3. Engines (Motores de Decisão)
**Local:** `v2/core/engines/`

Os *Engines* são os "chefs". Eles recebem os *Contracts* dos *Services* e aplicam a matemática, as regras de negócio e a ponderação.

| Arquivo | Papel / Responsabilidade |
| :--- | :--- |
| **`confluence_engine.py`** | O motor de votação. Pega o `MarketContext`, `PredictionContext`, `NewsContext` e `VisionContext` e aplica os pesos (ex: Predição 2.5x, Visão 1.8x) para gerar um voto final e uma % de confluência. |
| **`decision_engine.py`** | O estruturador de trade. Recebe o voto da confluência e os pivôs. Calcula a **Entrada, Stop Loss e Alvos**. **Nota:** Foi blindado para nunca inventar entradas se os pivôs reais não existirem. |
| **`opening_scenario_engine.py`** | O analista de abertura. Usa o `WinSession` para prever comportamentos (romper e continuar, testar e rejeitar, falso rompimento) com base no gap e na distância do ajuste. |
| **`v2_orchestrator.py`** | O **Maestro**. Coordena todos os *Services* e *Engines*. Aplica as regras de veto (Pepita >= 85% e Stale > 15min). Consolida o payload final e salva o `Decisao_V2.json`. |

---

## 4. Configurações Centralizadas
**Local:** `v2/config.py`

| Arquivo | Papel / Responsabilidade |
| :--- | :--- |
| **`config.py`** | Evita "números mágicos". Centraliza os pesos do `ConfluenceEngine` (`PESOS_CONFLUENCE`) e os limiares de distância do `OpeningScenarioEngine` (ex: `SCENARIO_LIMIAR_PROXIMO`). |

---

## 🔄 O Fluxo de Dados (Resumo)

1. O **Orchestrator** inicia o ciclo.
2. Ele chama os **Services** (Market, Prediction, News, Vision).
3. Os **Services** leem a pasta `Coletas/` e devolvem **Contracts** padronizados.
4. O **Orchestrator** envia os Contracts para o **ConfluenceEngine**, que gera um voto (ex: COMPRA 75%).
5. O **Orchestrator** aplica as regras de veto (Pepita/Stale). Se passar, envia para o **DecisionEngine**.
6. O **DecisionEngine** busca os pivôs reais e SMC para calcular Entrada, Stop e Alvo.
7. O **Orchestrator** empacota tudo em um `DecisionContext` e salva no disco (`Decisao_V2.json`).