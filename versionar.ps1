Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "          VERSIONADOR GIT - AUTOMAÇÃO DE FLUXO" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Write-Host "1) Criar nova feature branch (Main -> Pull -> New Branch)"
Write-Host "2) Salvar alterações (Add -> Commit -> Push)"
Write-Host "3) Finalizar feature (Merge na Main -> Push)"
Write-Host "4) Gerar nova versão/tag (Tag -> Push Tag)"
$Opcao = Read-Host "Opção (1-4)"

switch ($Opcao) {
    "1" {
        $Feature = Read-Host "Nome da funcionalidade (ex: novo-relatorio)"
        git switch main
        git pull
        git switch -c "feature/$Feature"
    }
    "2" {
        $Branch = (git branch --show-current)
        $Msg = Read-Host "Mensagem do commit"
        git add .
        git commit -m "$Msg"
        git push -u origin $Branch
    }
    "3" {
        $Branch = (git branch --show-current)
        if ($Branch -eq "main") {
            Write-Host "Erro: Você já está na branch main." -ForegroundColor Red
            return
        }
        git switch main
        git pull
        git merge $Branch
        git push
    }
    "4" {
        git switch main
        git pull
        $Tag = Read-Host "Nova versão (ex: v1.1.0)"
        $Msg = Read-Host "Descrição das alterações"
        git tag -a $Tag -m "$Msg"
        git push origin $Tag
    }
    Default { Write-Host "Opção inválida." -ForegroundColor Red }
}