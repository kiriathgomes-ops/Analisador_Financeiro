@echo off
:: Configura o terminal para aceitar acentuação e emojis no padrão UTF-8 do Windows
chcp 65001 >nul
title Launcher Quant Terminal - Gerador de Relatórios V2
color 0B

echo ============================================================
echo 🚀 QUANT TRADING TERMINAL - LAUNCHER DE RELATÓRIOS V2
echo ============================================================
echo.
echo Horário de Início: %time%
echo.

echo ------------------------------------------------------------
echo ⏳ PASSO 1 [OBRIGATÓRIO]: Gerando Inventário Técnico Base...
echo ------------------------------------------------------------
:: Executa de forma síncrona. Os outros scripts dependem deste arquivo salvo no disco.
python Gerar_Mapa_Inventario_Tecnico.py

:: Verifica se o inventário foi gerado sem erros de execução
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ [ERRO CRÍTICO] Falha ao executar Gerar_Mapa_Inventario_Tecnico.py!
    echo Os scripts subsequentes foram abortados para proteger a integridade dos dados.
    echo.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ✅ Inventário 'ArquivosApp.py' consolidado com sucesso!
echo 🚀 PASSO 2: Disparando processamento de mapas e relatórios...
echo ------------------------------------------------------------

:: Inicia as ferramentas de mapas de infraestrutura em paralelo em novas janelas ocultas/visíveis
start "Mapeador de Projeto V2" cmd /c "python Gerar_Mapa_Projeto.py"
start "Mapeador de Fluxo Dinâmico V2" cmd /c "python Gerar_Mapa_Fluxo.py"

:: Executa a calculadora operacional de consolidação final do resultado
start "Consolidador Operacional" cmd /c "python Gerar_Resultado_Operacional_Abertura.py"

echo.
echo ------------------------------------------------------------
echo ⏳ PASSO 3: Gerando Relatório Executivo de Auditoria Macro...
echo ------------------------------------------------------------
:: Executa o gerador de relatório macro oficial consolidado da V2
python Gerar_Relatorio.py

echo.
echo ============================================================
echo ✅ COMPILAÇÃO DE METADADOS E RELATÓRIOS CONCLUÍDA!
echo ============================================================
echo.
echo Todos os serviços em lote e mapas V2 foram atualizados.
echo Os arquivos estão prontos para consumo na interface Streamlit.
echo.
pause
exit
