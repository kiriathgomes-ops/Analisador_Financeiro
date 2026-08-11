@echo off
chcp 65001 >nul
title Versionador Git - Analisador Financeiro
color 0A

:MENU
cls
echo ============================================================
echo           VERSIONADOR GIT - ANALISADOR FINANCEIRO
echo ============================================================
echo.
echo   Branch atual:
git branch --show-current
echo.
echo ------------------------------------------------------------
echo   1. Ver status atual
echo   2. Atualizar main (git pull)
echo   3. Criar nova feature branch
echo   4. Fazer commit
echo   5. Enviar branch atual (push)
echo   6. Voltar para main
echo   7. Fazer merge de uma feature na main
echo   8. Criar nova tag (versão)
echo   9. Ver histórico visual
echo  10. Ver todas as branches
echo  11. Ver tags
echo   0. Sair
echo ------------------------------------------------------------
echo.
set /p opcao="Escolha uma opcao: "

if "%opcao%"=="1" goto STATUS
if "%opcao%"=="2" goto PULL_MAIN
if "%opcao%"=="3" goto NOVA_FEATURE
if "%opcao%"=="4" goto COMMIT
if "%opcao%"=="5" goto PUSH
if "%opcao%"=="6" goto VOLTAR_MAIN
if "%opcao%"=="7" goto MERGE
if "%opcao%"=="8" goto TAG
if "%opcao%"=="9" goto LOG
if "%opcao%"=="10" goto BRANCHES
if "%opcao%"=="11" goto TAGS
if "%opcao%"=="0" goto SAIR

echo Opcao invalida!
timeout /t 2 >nul
goto MENU

:STATUS
cls
echo === STATUS ATUAL ===
git status
echo.
pause
goto MENU

:PULL_MAIN
cls
echo === ATUALIZANDO MAIN ===
git switch main
git pull
echo.
pause
goto MENU

:NOVA_FEATURE
cls
echo === CRIAR NOVA FEATURE BRANCH ===
echo.
set /p nome="Digite o nome da feature (ex: novo-relatorio): "
if "%nome%"=="" (
    echo Nome invalido!
    pause
    goto MENU
)
git switch main
git pull
git switch -c feature/%nome%
echo.
echo Branch feature/%nome% criada e voce ja esta nela.
echo.
pause
goto MENU

:COMMIT
cls
echo === FAZER COMMIT ===
git status
echo.
set /p msg="Digite a mensagem do commit: "
if "%msg%"=="" (
    echo Mensagem invalida!
    pause
    goto MENU
)
git add .
git commit -m "%msg%"
echo.
pause
goto MENU

:PUSH
cls
echo === ENVIAR BRANCH ATUAL ===
git push -u origin HEAD
echo.
pause
goto MENU

:VOLTAR_MAIN
cls
echo === VOLTANDO PARA MAIN ===
git switch main
git status
echo.
pause
goto MENU

:MERGE
cls
echo === MERGE DE FEATURE NA MAIN ===
echo.
echo Branches feature disponiveis:
git branch | findstr "feature/"
echo.
set /p feature="Digite o nome completo da branch (ex: feature/novo-relatorio): "
if "%feature%"=="" (
    echo Nome invalido!
    pause
    goto MENU
)
git switch main
git pull
git merge %feature%
echo.
echo Merge concluido. Deseja enviar a main para o GitHub agora? (S/N)
set /p envia=
if /i "%envia%"=="S" (
    git push
)
echo.
pause
goto MENU

:TAG
cls
echo === CRIAR NOVA TAG (VERSAO) ===
echo.
echo Ultimas tags:
git tag -l --sort=-v:refname | more
echo.
set /p versao="Digite a versao (ex: v1.1.0): "
set /p msg="Digite a mensagem da tag: "
if "%versao%"=="" (
    echo Versao invalida!
    pause
    goto MENU
)
git tag -a %versao% -m "%msg%"
git push origin %versao%
echo.
echo Tag %versao% criada e enviada.
echo.
pause
goto MENU

:LOG
cls
echo === HISTORICO VISUAL ===
git log --oneline --decorate --graph --all -20
echo.
pause
goto MENU

:BRANCHES
cls
echo === TODAS AS BRANCHES ===
git branch -vv
echo.
pause
goto MENU

:TAGS
cls
echo === TAGS EXISTENTES ===
git tag -l -n
echo.
pause
goto MENU

:SAIR
echo.
echo Ate logo!
timeout /t 1 >nul
exit