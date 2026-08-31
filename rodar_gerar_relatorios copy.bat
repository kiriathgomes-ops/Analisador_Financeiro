@echo off
title Launcher Quant Terminal
echo ============================================================
echo 🚀 INICIANDO QUANT TRADING GERAR RELATORIOS E MAPAS
echo ============================================================

echo ------------------------------------------------------------
echo ⏳ Executando Passo 1: Gerar App Completo...
echo (Aguarde a conclusao do processo de coleta...)
echo ------------------------------------------------------------

:: Executa o Gerar_App_Completo.py e AGUARDA a finalizacao antes de prosseguir
python Gerar_App_Completo.py

:: Verifica se a coleta rodou sem erros
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ ERRO ao executar Gerar_App_Completo.py!
    echo Os scripts subsequentes foram cancelados para proteger os dados.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ✅ Coleta de dados do Passo 1 concluida com sucesso!
echo 🚀 Disparando os scripts restantes em janelas separadas...
echo ------------------------------------------------------------

:: Inicia os demais scripts em paralelo em novas janelas de terminal
start "2. Gerar Mapa de Inventario Tecnico" cmd /k "python Gerar_Mapa_Inventario_Tecnico.py"
start "3. Coletas Arquivos App" cmd /k "python Gerar_ColetasArquivosApp.py"
start "4. Gerar Mapa de Fluxo" cmd /k "python Gerar_Mapa_Fluxo.py"
start "5. Gerar Mapa de Projeto" cmd /k "python Gerar_Mapa_Projeto.py"
start "6. Gerar Relatorio Mensagem" cmd /k "python Gerar_Relatorio_Mensagem.py"
start "7. Gerar Relatorio" cmd /k "python Gerar_Relatorio.py"
start "8. Gerar Resultado Operacional" cmd /k "python Gerar_Resultado_Operacional_Abertura.py"

echo.
echo ✅ Todos os servicos foram disparados com sucesso!
echo Voce pode fechar esta janela do launcher se desejar.
pause