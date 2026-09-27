# Documentacao - Analisador Financeiro

Pacote de documentacao do projeto. Atualizado em 2026-09-26.

## Indice

| Arquivo | O que contem | Tipo |
|---|---|---|
| `arvore.md` | Estrutura de diretorios do projeto (gerada por script) | Automatico |
| `inventario.md` | Tabela de todos os `.py` com linhas, bytes, mtime (gerada por script) | Automatico |
| `estado_atual.md` | Visao geral do que o app faz e como esta organizado | Manual |
| `melhorias.md` | Pontos identificados como oportunidades de melhoria | Manual |
| `prompt_deepseek.md` | 5 prompts prontos para IA (auditoria + features + integracao) | Manual |
| `system_prompt_agente.md` | System prompt para criar agente de IA parceiro do projeto | Manual |

## Como manter

Os 2 primeiros sao GERADOS AUTOMATICAMENTE. Depois de qualquer mudanca
estrutural (novos scripts, pastas, refactors), rode:

    python gerar_docs.py

Os 4 ultimos sao CURADOS MANUALMENTE. Precisam de revisao periodica
quando decisoes de arquitetura ou prioridades mudarem.

## Ordem de leitura sugerida

Para quem esta chegando no projeto agora:

1. estado_atual.md    - entende o que existe
2. arvore.md          - ve onde cada coisa esta
3. melhorias.md       - sabe o que esta em aberto
4. inventario.md      - referencia (consulta pontual)
5. prompt_deepseek.md - so quando for usar IA externa
6. system_prompt_agente.md - para criar agente de IA parceiro

## Observacao

Este pacote NAO substitui os docstrings dos modulos. E uma visao de
alto nivel. Para detalhes de implementacao, olhar diretamente no codigo.
