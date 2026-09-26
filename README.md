# Analisador Financeiro

Sistema de analise financeira institucional para WIN/WDO na B3.

## Requisitos

- Python 3.14+
- MetaTrader 5 (Genial Investimentos)
- Tesseract OCR (sniper de leilao)

## Instalacao

    pip install -r requirements.txt

### Dependencias extras por feature

- streamlit-autorefresh - Pagina 7.1_SMC_Regras (auto-refresh 5min)
  Instalar: pip install streamlit-autorefresh

## Comandos principais

    python main_pipeline.py           # Pipeline completo
    python Agendador.py               # Agendador (5min em :04, :09...)
    streamlit run Home.py             # Dashboard Streamlit

    python Rodar_SMC_Regras.py        # SMC multi-TF manual (M1/M5/M15)
    python gerar_snapshot_mtf_ia.py   # Snapshot para colar em IA
    python win_abertura_sniper.py     # Sniper de leilao (08:50-09:05)
    python analisar_rompimento_10h.py # Snapshot ORB (10:00-10:15)

## Estrutura

    Coletas/                     # JSONs runtime
      cache/                     # Cache incremental de candles
      Historico_Aberturas/       # Sessoes gravadas
    v2/                          # Orquestrador V2
      core/engines/              # v2_orchestrator, decision_engine
    pages/                       # Streamlit pages
    Motor_SMC_Regras.py          # Motor SMC/ICT
    main_pipeline.py             # Orquestrador do pipeline
    config.py                    # Configuracao central

## Arquitetura

- Coleta: Coletor.py + Coletor_MT5_v2_2.py (brapi, Finnhub, TV, MT5)
- Validacao: Validador.py (sanitiza 34 ativos)
- Analise SMC: Motor_SMC_Regras.py (POC, VWAP, OB, FVG, liquidez)
- Estimativa: CalculadoraEstimativaAbertura.py
- Decisao: v2/core/engines/v2_orchestrator.py (SMC x NOVO_MOTOR + MTF)

## Notas

Para anotacoes pessoais de trabalho, crie um NOTAS.md local
(nao versionado - esta no .gitignore).
