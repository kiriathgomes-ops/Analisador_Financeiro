@echo off
title Pipeline 3x - Analisador Financeiro
echo ============================================================
echo 📦 RODANDO PIPELINE 3 VEZES (ROTACAO TEMPORAL)
echo ============================================================
echo.
echo Data/Hora: %date% %time%
echo.

:: Executa a pipeline 3 vezes
for /l %%i in (1,1,3) do (
    echo.
    echo [%%i/3] Executando main_pipeline.py...
    echo ------------------------------------------------------------
    python main_pipeline.py
    if errorlevel 1 (
        echo.
        echo ❌ ERRO na execucao %%i!
        echo Pressione qualquer tecla para sair...
        pause >nul
        exit /b 1
    )
    echo.
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
    echo.
    echo ⚠️ Erro ao gerar analise de tendencia!
    echo Continuando mesmo assim...
)

:: Gera resultado operacional
echo.
echo ============================================================
echo 📊 GERANDO RESULTADO OPERACIONAL
echo ============================================================
python Gerar_Resultado_Operacional_Abertura.py
if errorlevel 1 (
    echo.
    echo ⚠️ Erro ao gerar resultado operacional!
    echo Continuando mesmo assim...
)

:: ============================================================
echo.
echo ============================================================
echo ✅ PIPELINE 3x FINALIZADA COM SUCESSO!
echo ============================================================
echo.
echo Arquivos gerados:
echo   - Coleta_rom-0.json  (Execucao 1)
echo   - Coleta_rom-5.json  (Execucao 2)
echo   - Coleta_rom-10.json (Execucao 3)
echo   - Analise_Tendencias.json
echo   - Resultado_Calculadora_Operacional_Abertura.json
echo.
echo Data/Hora: %date% %time%
echo.
pause