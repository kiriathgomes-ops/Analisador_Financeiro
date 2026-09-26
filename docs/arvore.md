# Arvore de Arquivos

Gerado em: 2026-09-26 09:28:50

```
.
|-- Coletas
|   |-- cache
|   |   `-- candles_WINV26_15m.json
|   |       (+2 arquivos semelhantes)
|   |-- coleta_preco_teorico_historico
|   |   `-- preco_teorico_2026-09-24.csv
|   |       (+7 arquivos semelhantes)
|   |-- Historico_Aberturas
|   |   `-- 2026-09-25.json
|   |       (+16 arquivos semelhantes)
|   |-- Historico_Decisoes_V2
|   |   `-- 20260925_185903.json
|   |       (+378 arquivos semelhantes)
|   |-- Historico_MT5
|   |   `-- MT5_v2_2_20260925_185902_174818.json
|   |       (+328 arquivos semelhantes)
|   |-- Analise_Tendencias.json
|   |-- AnaliseGraficaSMC_MTF.json
|   |-- AnaliseGraficaSMC_Regras.json
|   |-- AnaliseGraficaSMC_Regras_M1.json
|   |-- AnaliseGraficaSMC_Regras_M15.json
|   |-- ArquivosApp.py
|   |-- Coleta_ram.json
|   |-- Coleta_rom-0.json
|   |-- Coleta_rom-10.json
|   |-- Coleta_rom-15.json
|   |-- Coleta_rom-20.json
|   |-- Coleta_rom-25.json
|   |-- Coleta_rom-30.json
|   |-- Coleta_rom-35.json
|   |-- Coleta_rom-40.json
|   |-- Coleta_rom-45.json
|   |-- Coleta_rom-5.json
|   |-- Coleta_rom-50.json
|   |-- Coleta_rom-55.json
|   |-- config_regiao.json
|   |-- Dados_MT5_v2_2.json
|   |-- Dados_Validados.json
|   |-- DadosAtivosUnificados.json
|   |-- Decisao_V2.json
|   |-- EstimativaAbertura.json
|   |-- EstimativaAbertura_Cache.json
|   |-- LastTick_Congelado.json
|   |-- Mapa_Projeto.json
|   |-- Metricas_Calculadas.json
|   |-- monitor_2_completo - Copia (2).png
|   |-- monitor_2_completo - Copia.png
|   |-- monitor_2_completo.png
|   |-- Noticias_Calendario.json
|   |-- Noticias_Calendario_0900.json
|   |-- Noticias_Impacto_Dia.json
|   |-- preco_teorico_win_fluxo.csv
|   |-- Relatorio_Executivo.md
|   |-- Resultado_Calculadora_Operacional_Abertura.json
|   |-- snapshot_mtf_ia.txt
|   |-- snapshot_mtf_scripts.json
|   |-- snapshot_rompimento_10h copy.txt
|   |-- snapshot_rompimento_10h.txt
|   |-- token_usage.log
|   |-- WIN_1min.png
|   `-- WIN_5min.png
|-- docs
|   |-- arvore.md
|   `-- inventario.md
|-- ferramentas
|   |-- _debug_regiao.py
|   |-- mapear_regiao_ocr.py
|   `-- teste_ocr_direto.py
|-- Imagens
|   |-- SpikeIA.png
|   `-- SpikeIAGrande.jpg
|-- logs
|-- NOVO_MOTOR_PREVISAO_ABERTURA
|   |-- config
|   |   |-- __init__.py
|   |   `-- pesos.yaml
|   |-- core
|   |   |-- __init__.py
|   |   |-- motor_ajuste.py
|   |   |-- motor_cenarios.py
|   |   |-- motor_gap.py
|   |   |-- motor_previsao.py
|   |   `-- motor_score.py
|   |-- dados
|   |   |-- __init__.py
|   |   |-- coletor_dados.py
|   |   `-- schemas.py
|   `-- __init__.py
|-- pages
|   |-- 1_⚡_Dashboard_Leilao_AoVivo.py
|   |-- 2_🎯_Setup_Abertura.py
|   |-- 3_⚡_Monitor_Abertura_Leilao_V3.2.py
|   |-- 4_⚡_WINFUT_Intraday.py
|   |-- 6.5_📈_Previsao_Abertura_WINFUT.py
|   |-- 6.7_📈_Matriz_de_Influencia.py
|   |-- 6_📡_Ativos_Monitorados.py
|   |-- 7.1_📊_SMC_Regras.py
|   |-- 7.2_🤖_IA_SpikeImagem.py
|   |-- 7.3_📥_Gerador_Profit_Pro.py
|   |-- 7.4_🤖_IA_Imagem.py
|   |-- 7.5_📅_Noticias.py
|   |-- 7_🔬_Analise_Tendencia.py
|   |-- 8.1_🗺️_Mapa_da_Aplicacao.py
|   |-- 8.2_🔢_Calculadora.py
|   |-- 8.3_🔑_Status_Chaves.py
|   `-- 9.5_📈_Historico_Macro.py
|-- PromptIA
|   |-- Analista_SMC.txt
|   |-- Analista_SMC2.txt
|   |-- grafico.json
|   |-- grafico.txt
|   |-- padrao.txt
|   |-- Promp_Mestre_Visual_Ultra_Teste.txt
|   |-- Promp_Plus_Profit.txt
|   |-- Prompt_Abertura_0900.txt
|   |-- Prompt_Gemini_SMC.txt
|   |-- Prompt_Mestre_Visao_Ultra.txt
|   |-- Prompt_Mestre_Visao_Ultra1.txt
|   |-- Prompt_Rompimento_10h.txt
|   |-- PromptMestre.txt
|   |-- PromptMestreCurto.txt
|   `-- vision_prompt_config.json
|-- utils
|   |-- AnaliseGraficaSMC_Regras.json
|   `-- KeyManager.py
|-- v2
|   |-- core
|   |   |-- contracts
|   |   |   |-- __init__.py
|   |   |   |-- decision_context.py
|   |   |   |-- market_context.py
|   |   |   |-- news_context.py
|   |   |   |-- prediction_context.py
|   |   |   |-- vision_context.py
|   |   |   `-- win_session.py
|   |   |-- engines
|   |   |   |-- __init__.py
|   |   |   |-- confluence_engine.py
|   |   |   |-- decision_engine.py
|   |   |   |-- opening_scenario_engine.py
|   |   |   `-- v2_orchestrator.py
|   |   |-- services
|   |   |   |-- __init__.py
|   |   |   |-- leilao_service.py
|   |   |   |-- market_service.py
|   |   |   |-- news_service.py
|   |   |   |-- prediction_service.py
|   |   |   |-- session_history.py
|   |   |   |-- vision_ai_service.py
|   |   |   |-- vision_service.py
|   |   |   `-- win_session_builder.py
|   |   `-- __init__.py
|   |-- pages
|   |   |-- 1_dashboard_v2.py
|   |   |-- 2_analise_detalhada.py
|   |   |-- 3_page_cockpit_pregao.py
|   |   `-- __init__.py
|   |-- tests
|   |   `-- test_contracts.py
|   |-- __init__.py
|   `-- main.py
|-- .gitignore
|-- 03_rodar_gerar_relatorios.bat
|-- 0_rodar_tudo.bat
|-- 1_rodar_pipeline_3x.bat
|-- _patch_gerar_docs.py
|-- abertura 25set.txt
|-- Agendador.py
|-- analisar_divergencia.py
|-- analisar_historico.py
|-- analisar_historico_v2.py
|-- analisar_rompimento_10h.py
|-- Analise_Noticias.py
|-- app_home.py
|-- backtest_bias_estabilidade.py
|-- cache_candles.py
|-- Calculadora.py
|-- CalculadoraEstimativaAbertura.py
|-- Coleta_Noticias_Calendario.py
|-- Coletor.py
|-- Coletor_MT5_v2_2.py
|-- comçarNovotrab.txt
|-- config.py
|-- diag_orb_10h.py
|-- gerar_docs.py
|-- Gerar_Mapa_Fluxo.py
|-- Gerar_Mapa_Inventario_Tecnico.py
|-- Gerar_Mapa_Projeto.py
|-- Gerar_Relatorio_Mensagem.py
|-- Gerar_Resultado_Operacional_Abertura.py
|-- gerar_snapshot_mtf_ia.py
|-- Limpar_Imagens_TradingView.py
|-- main_pipeline.py
|-- MapearTendencia15Min.py
|-- Motor_SMC_Regras.py
|-- NOTAS.md
|-- README.md
|-- requirements.txt
|-- Rodar_SMC_Regras.py
|-- Temp_Validacao_Smoke.py
|-- v2_gravar_sessao_win.py
|-- v2_rodar_decisao_completa.py
|-- Validador.py
|-- versionar.ps1
`-- win_abertura_sniper.py
```