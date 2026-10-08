# Melhorias Pendentes - Analisador Financeiro



Atualizado em 2026-09-26.



## Alta prioridade (afeta decisao operacional)



\- \[ ] Backtest dos pesos 0.60/0.40 da confluencia (SMC x NOVO_MOTOR)

\- \[ ] Calibrar modificadores MTF (-10/-25/-40/-15/0/+10)

\- \[ ] Calibrar fator 1.8 do REVERSAO_MICRO_MEDIO

\- \[ ] Calibrar LIMIAR_DIRECAO do motor_score.py (hoje: 10)



## Baixa prioridade (limpeza / nice-to-have)




\- \[ ] Trocar `global` do Gerar_Relatorio_Mensagem por parametro explicito

\- \[ ] Cache: revisar MAX_CACHE_POR_TF (hoje 1000)

\- \[ ] Documentar convencao timezone MT5 em docs/

\- \[ ] Padronizar encoding nos scripts PowerShell



## Concluidas recentemente (contexto)



\- \[x] Remover uso de CONFIG global nos detectores SMC (fix02.py)
\- \[x] Cache incremental de candles (v0.11.0)

\- \[x] Multi-TF visual M1/M5/M15 na pagina SMC_Regras (v0.11.0)

\- \[x] Timezone MT5 corrigido (v0.11.4)

\- \[x] Dedup + ordenacao cronologica de eventos SMC (v0.11.1)

\- \[x] Coerencia direcional BOS/CHoCH com bias (v0.11.1)

\- \[x] Restauracao de variaveis globais da pagina SMC_Regras (v0.11.2)

\- \[x] QTD_REFRESH_INCREMENTAL 15 -> 60 (v0.11.3)

\- \[x] Documentacao da semantica de calcular_confianca (sem tag)

\- \[x] README + pacote de docs (em andamento)



## Como usar este arquivo



\- Alta prioridade: revisar antes de qualquer release novo

\- Baixa prioridade: agrupar em sessoes de limpeza

\- Concluidas: manter as ultimas \~10 pra contexto; podar as antigas



Nao colocar prazos nem estimativas aqui - este arquivo lista o QUE fazer,

nao QUANDO.



## Features futuras (roadmap)

\- \[ ] **Motor de Visão IA** (OCR/análise de imagem SMC)
  - Objetivo: gerar `Coletas/AnaliseGraficaSMC.json` a partir de imagens de gráfico
  - Consumidores prontos: pages 7.2 (spike LTF), 7.3 (Profit Pro), 7.4 (SMC via IA)
  - Estado atual: 3 pages órfãs aguardando o motor (ver item 19 do estado_atual.md)
  - Escopo: OCR + classificação de padrões SMC + output no schema esperado
  - Bloqueio: motor nunca foi implementado; páginas existem desde antes da V2
  - Pendente: definir se será (a) integração com IA generativa multimodal,
    (b) OCR clássico + parser, ou (c) remover as 3 pages

\- \[ ] **Integrar `opening_scenario_engine` no payload do orchestrator**
  - Hoje o engine gera cenários, mas o resultado só vai pro `Historico_Aberturas`
  - Page 2 lê do `Historico_Aberturas` (fix73+fix79)
  - Alternativa: expor `opening_scenario` também em `Decisao_V2.json`
  - Ver item 15 do estado_atual.md (TODO deixado pelo fix71)

