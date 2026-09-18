@echo off
title Launcher Quant Terminal
echo ============================================================
echo 🚀 QUANT TRADING TERMINAL - LAUNCHER COMPLETO
echo ============================================================
echo.

:: ============================================================
:: MENU PRINCIPAL
:: ============================================================
echo Escolha uma opcao:
echo.
echo [1] Rodar Pipeline 3x + Iniciar Terminal
echo [2] Iniciar Terminal (pular pipeline)
echo [3] Rodar Pipeline 3x (apenas pipeline)
echo [4] Sair
echo.
choice /c 1234 /n /m "Digite a opcao desejada: "

if errorlevel 4 goto SAIR
if errorlevel 3 goto RODAR_PIPELINE
if errorlevel 2 goto INICIAR_TERMINAL
if errorlevel 1 goto RODAR_TUDO

:: ============================================================
:: OPÇÃO 1: RODAR PIPELINE 3x + INICIAR TERMINAL
:: ============================================================
:RODAR_TUDO
echo.
echo ============================================================
echo 📦 RODANDO PIPELINE 3 VEZES (ROTACAO TEMPORAL)
echo ============================================================

:: Executa a pipeline 3 vezes
for /l %%i in (1,1,3) do (
    echo.
    echo [%%i/3] Executando main_pipeline.py...
    echo ------------------------------------------------------------
    python main_pipeline.py
    if errorlevel 1 (
        echo ❌ ERRO na execucao %%i!
        echo Pressione qualquer tecla para sair...
        pause >nul
        exit /b 1
    )
    echo ✅ Execucao %%i concluida!
    if %%i lss 3 (
        echo Aguardando 2 segundos...
        timeout /t 2 /nobreak >nul
    )
)

:: Gera análise de tendência
echo.
echo ============================================================
echo 📈 GERANDO ANALISE DE TENDENCIA (10m - 5m - 0m)
echo ============================================================
python MapearTendencia15Min.py
if errorlevel 1 (
    echo ⚠️ Atencao: Erro ao gerar analise de tendencia!
    echo Continuando mesmo assim...
    timeout /t 2 /nobreak >nul
)

:: Gera resultado operacional
echo.
echo ============================================================
echo 📊 GERANDO RESULTADO OPERACIONAL
echo ============================================================
python Gerar_Resultado_Operacional_Abertura.py
if errorlevel 1 (
    echo ⚠️ Atencao: Erro ao gerar resultado operacional!
    echo Continuando mesmo assim...
    timeout /t 2 /nobreak >nul
)

:: ============================================================
:: INICIAR TERMINAL (após pipeline)
:: ============================================================
:INICIAR_TERMINAL
echo.
echo ============================================================
echo 🚀 INICIANDO QUANT TRADING TERMINAL
echo ============================================================

:: Inicia o Streamlit em uma nova janela de terminal
echo 📱 Iniciando Interface Streamlit...
start "1. Interface Streamlit" cmd /k "python -m streamlit run app_home.py"

:: Aguarda 3 segundos para a interface carregar primeiro
timeout /t 3 /nobreak >nul

:: Inicia o Agendador Sincronizado em outra janela de terminal
echo ⏰ Iniciando Agendador Background...
start "2. Agendador Background" cmd /k "python Agendador.py"

echo.
echo ============================================================
echo ✅ TODOS OS SERVICOS INICIADOS COM SUCESSO!
echo ============================================================
echo.
echo 📱 Interface: http://localhost:8501
echo ⏰ Agendador: Executando em background
echo 📊 Pipeline: 3 execucoes concluidas
echo.
echo Voce pode fechar esta janela do launcher.
echo.
pause
goto SAIR

:: ============================================================
:: OPÇÃO 2: APENAS INICIAR TERMINAL
:: ============================================================
goto INICIAR_TERMINAL

:: ============================================================
:: OPÇÃO 3: APENAS RODAR PIPELINE 3x
:: ============================================================
:RODAR_PIPELINE
echo.
echo ============================================================
echo 📦 RODANDO PIPELINE 3 VEZES (ROTACAO TEMPORAL)
echo ============================================================

:: Executa a pipeline 3 vezes
for /l %%i in (1,1,3) do (
    echo.
    echo [%%i/3] Executando main_pipeline.py...
    echo ------------------------------------------------------------
    python main_pipeline.py
    if errorlevel 1 (
        echo ❌ ERRO na execucao %%i!
        echo Pressione qualquer tecla para sair...
        pause >nul
        exit /b 1
    )
    echo ✅ Execucao %%i concluida!
    if %%i lss 3 (
        echo Aguardando 2 segundos...
        timeout /t 2 /nobreak >nul
    )
)

:: Gera análise de tendência
echo.
echo ============================================================
echo 📈 GERANDO ANALISE DE TENDENCIA
echo ============================================================
python MapearTendencia15Min.py
if errorlevel 1 (
    echo ⚠️ Erro ao gerar analise de tendencia!
)

:: Gera resultado operacional
echo.
echo ============================================================
echo 📊 GERANDO RESULTADO OPERACIONAL
echo ============================================================
python Gerar_Resultado_Operacional_Abertura.py
if errorlevel 1 (
    echo ⚠️ Erro ao gerar resultado operacional!
)

echo.
echo ============================================================
echo ✅ PIPELINE 3x FINALIZADA COM SUCESSO!
echo ============================================================
echo.
echo Arquivos gerados:
echo   - Coleta_rom-0.json
echo   - Coleta_rom-5.json
echo   - Coleta_rom-10.json
echo   - Analise_Tendencias.json
echo   - Resultado_Calculadora_Operacional_Abertura.json
echo.
pause
goto SAIR

:: ============================================================
:: SAIR
:: ============================================================
:SAIR
exit