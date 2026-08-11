@echo off
chcp 65001 >nul
title Versionador Git - Fluxo Simples
color 0B

echo ============================================================
echo      VERSIONADOR GIT - FLUXO COMPLETO (VERSAO SIMPLES)
echo ============================================================
echo.
echo Este script mostra o fluxo correto de trabalho.
echo Voce pode executar os comandos manualmente ou usar como guia.
echo.
pause

echo.
echo ============================================================
echo 1. SEMPRE COMECE NA MAIN ATUALIZADA
echo ============================================================
echo.
echo git switch main
echo git pull
echo.
pause

echo.
echo ============================================================
echo 2. CRIAR UMA NOVA FEATURE BRANCH
echo ============================================================
echo.
echo git switch -c feature/nome-da-funcionalidade
echo.
echo Exemplo:
echo git switch -c feature/novo-relatorio
echo.
pause

echo.
echo ============================================================
echo 3. DESENVOLVER E FAZER COMMITS
echo ============================================================
echo.
echo git add .
echo git commit -m "Descrição clara do que foi feito"
echo.
echo Dica: faca commits pequenos e frequentes.
echo.
pause

echo.
echo ============================================================
echo 4. ENVIAR A BRANCH PARA O GITHUB
echo ============================================================
echo.
echo git push -u origin feature/nome-da-funcionalidade
echo.
echo (Na primeira vez use -u. Nas proximas so "git push")
echo.
pause

echo.
echo ============================================================
echo 5. QUANDO A FEATURE ESTIVER PRONTA E TESTADA
echo ============================================================
echo.
echo git switch main
echo git pull
echo git merge feature/nome-da-funcionalidade
echo git push
echo.
pause

echo.
echo ============================================================
echo 6. CRIAR UMA NOVA VERSAO (TAG)
echo ============================================================
echo.
echo git tag -a v1.1.0 -m "Versão 1.1.0 - descricao do que mudou"
echo git push origin v1.1.0
echo.
echo Regras de versao:
echo   v1.0.1  = correcao pequena (PATCH)
echo   v1.1.0  = nova funcionalidade (MINOR)
echo   v2.0.0  = mudanca grande (MAJOR)
echo.
pause

echo.
echo ============================================================
echo 7. COMANDOS UTEIS DE CONSULTA
echo ============================================================
echo.
echo git status
echo git branch -vv
echo git log --oneline --decorate --graph --all -15
echo git tag -l -n
echo.
pause

echo.
echo ============================================================
echo FIM DO FLUXO
echo ============================================================
echo.
echo Lembre-se das regras de ouro:
echo - Nunca desenvolva direto na main
echo - Sempre trabalhe em feature/...
echo - So faca merge depois de testar
echo - Crie tag quando for versao estavel
echo.
echo Pressione qualquer tecla para sair...
pause >nul