# Estado Atual do App - Analisador Financeiro



Atualizado em 2026-09-26. Publico-alvo: eu mesmo (retomada futura).



## 1. Visao geral



Sistema de analise financeira institucional para WIN/WDO na B3. Coleta

dados de multiplas fontes (MT5, brapi, Finnhub, TradingView, BACEN),

sanitiza, roda motores de analise tecnica (SMC/ICT) e macro, e produz

uma decisao operacional consolidada via orquestrador V2.



O app nao opera automaticamente. Ele gera uma decisao (vies, entrada,

stop, alvos) que serve de apoio manual. Toda analise roda via pipeline

assincrono, disparado pelo `Agendador.py` a cada 5 min (em :04, :09, :14...).



## 2. Pipeline end-to-end



Fluxo (definido em `main_pipeline.py`):



1\. Limpeza de imagens TradingView (cache de OCR)

2\. Coleta paralela:

&#x20;  - `Coletor.py` (brapi, Finnhub, TradingView, BACEN PTAX)

&#x20;  - `Coletor_MT5_v2_2.py` (WIN, WDO, DI1 direto do MT5)

&#x20;  - `Coleta_Noticias_Calendario.py`

3\. Analise de noticias (`Analise_Noticias.py`)

4\. Validacao (`Validador.py`) - sanitiza 34 ativos

5\. Motor SMC multi-TF (`Rodar_SMC_Regras.py`) - M1 + M5 + M15

6\. Calculadoras (paralelo):

&#x20;  - `Calculadora.py` (spreads, DI, indicadores compostos)

&#x20;  - `CalculadoraEstimativaAbertura.py` (abertura teorica + cost of carry)

7\. Consolidacao de payload (`Gerar_Resultado_Operacional_Abertura.py`)

8\. Decisao final V2 (`v2_rodar_decisao_completa.py` -> orquestrador)

9\. Relatorio + gravacao de sessao (paralelo):

&#x20;  - `Gerar_Relatorio_Mensagem.py`

&#x20;  - `v2_gravar_sessao_win.py`



Tempo medio: \~2-3 segundos por ciclo (com cache quente).



## 3. Componentes por pasta



### Raiz (scripts principais)



| Script | Funcao |

|---|---|

| `main_pipeline.py` | Orquestrador do pipeline assincrono |

| `Agendador.py` | Dispara o pipeline a cada 5 min |

| `config.py` | Fonte unica de verdade (caminhos, tickers, pesos) |

| `Coletor.py` | Coleta de APIs externas (brapi, Finnhub, TV) |

| `Coletor_MT5_v2_2.py` | Coleta MT5 (WIN, WDO, DI1) |

| `Validador.py` | Sanitizacao dos 34 ativos |

| `Calculadora.py` | Spreads, DI, indicadores compostos |

| `CalculadoraEstimativaAbertura.py` | Abertura teorica + cost of carry |

| `Motor_SMC_Regras.py` | Motor SMC/ICT (POC, VWAP, OB, FVG, liquidez) |

| `Rodar_SMC_Regras.py` | Executa SMC em M1/M5/M15 + consolidacao MTF |

| `cache_candles.py` | Cache incremental de candles (fetch MT5) |

| `Gerar_Resultado_Operacional_Abertura.py` | Consolida payload |

| `Gerar_Relatorio_Mensagem.py` | Gera relatorio em Markdown |

| `v2_rodar_decisao_completa.py` | Ponte para o orquestrador V2 |

| `v2_gravar_sessao_win.py` | Grava WinSession |

| `win_abertura_sniper.py` | Sniper de leilao (OCR do preco teorico) |

| `analisar_rompimento_10h.py` | Snapshot ORB 10:00 pra IA |

| `gerar_snapshot_mtf_ia.py` | Snapshot MTF pra colar em IA |

| `gerar_docs.py` | Gera arvore.md + inventario.md |

| `Temp_Validacao_Smoke.py` | Smoke test de integridade |

| `Analise_Noticias.py` | Analise quantitativa de noticias |

| `coleta_noticias_calendario.py` | Coleta de calendario economico |



### v2/ (orquestrador)



\- `v2/core/engines/v2_orchestrator.py` - Decisao final (confluencia SMC x NOVO_MOTOR + MTF)

\- `v2/core/engines/decision_engine.py` - Regras de decisao

\- `v2/core/services/market_service.py` - Leitura de tendencias

\- `v2/core/services/leilao_service.py` - Le preco do leilao (OCR)

\- `v2/core/services/prediction_service.py` - Ponte para NOVO_MOTOR

\- `v2/core/services/win_session_builder.py` - Builder de sessao

\- `v2/pages/` - Dashboards Streamlit V2



### NOVO_MOTOR_PREVISAO_ABERTURA/



Motor macro + score direcional + cenarios:

\- `core/motor_previsao.py` - Orquestrador

\- `core/motor_gap.py` - Calculo de gap (limiares em %)

\- `core/motor_score.py` - Score direcional

\- `dados/coletor_dados.py` - Leitura dos JSONs



### pages/ (Streamlit)



| Pagina | Funcao |

|---|---|

| `1_Dashboard_Leilao_AoVivo.py` | Monitor do leilao + card MTF |

| `2_Setup_Abertura.py` | Setup consolidado + card MTF |

| `3_Monitor_Abertura_Leilao_V3.2.py` | Monitor V3.2 |

| `4_WINFUT_Intraday.py` | Grafico intraday |

| `7.1_SMC_Regras.py` | Graficos SMC multi-TF (M1/M5/M15) |

| `8.1_Mapa_da_Aplicacao.py` | Mapa do projeto |



### Coletas/ (dados runtime)



Maioria nao versionada. Principais:

\- `Dados_MT5_v2_2.json` - Contratos MT5

\- `DadosAtivosUnificados.json` - Ativos consolidados

\- `Dados_Validados.json` - Sanitizado

\- `AnaliseGraficaSMC_Regras.json` - SMC M5

\- `AnaliseGraficaSMC_Regras_M1.json` - SMC M1

\- `AnaliseGraficaSMC_Regras_M15.json` - SMC M15

\- `AnaliseGraficaSMC_MTF.json` - Consolidacao MTF

\- `Decisao_V2.json` - Decisao final

\- `EstimativaAbertura.json` - Abertura teorica

\- `Metricas_Calculadas.json` - Indicadores

\- `cache/` - Cache incremental de candles

\- `Historico_\*` - Sessoes gravadas



### utils/, ferramentas/, PromptIA/



\- `utils/` - Helpers internos

\- `ferramentas/` - Scripts auxiliares

\- `PromptIA/` - Prompts para IA (ex: Prompt_Rompimento_10h.txt)



---

## 4. Decisao operacional (como o V2 decide)

### Fluxo de confluencia

O orquestrador V2 (`v2/core/engines/v2_orchestrator.py`) combina 2 motores:

- **SMC** (tecnico) - peso 0.60
- **NOVO_MOTOR** (macro) - peso 0.40

Regra de decisao:
1. Se SMC e NOVO_MOTOR concordam em direcao -> calcula confianca ponderada
2. Se divergem -> retorna NEUTRO (nao opera)
3. Se NOVO_MOTOR tem divergencia interna (gap vs score) -> NEUTRO

### Modificador MTF (fix29)

Alem da confluencia SMC x NOVO_MOTOR, o V2 consome o `AnaliseGraficaSMC_MTF.json`
e aplica um delta de confianca sobre o SMC antes do gate de 55%:

| Veredito MTF | Delta |
|---|---|
| ALINHADO_FORTE | +10 |
| PULLBACK | 0 |
| REVERSAO_MICRO_MEDIO | -10 |
| CONFLITO_MACRO | -25 |
| DIVERGENTE | -40 |
| NEUTRO | -15 |
| PARCIAL | -15 |

### Gates de confianca

- `CONFIANCA_MINIMA_CONFLUENCIA = 55` (aplicado ao SMC ajustado)
- `CONFIANCA_MINIMA_FINAL = 45` (aplicado a confianca final ponderada)

Se algum gate falha -> `operar=False`, vies=NEUTRO.

### Consolidacao MTF

O `Rodar_SMC_Regras.py` gera os 3 TFs e consolida via `calcular_confluencia_mtf`:

| Cenario | Veredito |
|---|---|
| M15=M5=M1 | ALINHADO_FORTE |
| M15=M5, M1 contra | PULLBACK |
| M5=M1 contra M15 com soma > M15*1.8 | REVERSAO_MICRO_MEDIO |
| M5=M1 contra M15 com soma <= M15*1.8 | CONFLITO_MACRO |
| 3 direcoes diferentes | DIVERGENTE |
| Menos de 3 TFs disponiveis | PARCIAL |

---

## 5. Estado de maturidade

### Estavel / confiavel

- Coleta MT5 com contrato vigente por ativo (WIN/WDO front-month, DI1 por volume)
- Cache incremental de candles (QTD_REFRESH=60, cobre gaps de ate 5h)
- Motor SMC com dedup de eventos + ordenacao cronologica
- Timezone MT5 corrigido (wall-clock BRT)
- Relatorio em Markdown alinhado com decisao do V2
- Multi-TF visual na pagina SMC_Regras (M1/M5/M15 com zonas)
- MTF como modificador de confianca no V2

### Experimental / em observacao

- `calcular_confianca` - documentado (fix48) como "score de presenca",
  nao como probabilidade. Pode bater 100% em setups com pouca estrutura.
- Modificadores MTF (-10/-25/-40/-15) - valores sao chute, sem calibracao
  por backtest.
- Fator 1.8 do REVERSAO_MICRO_MEDIO - tambem sem calibracao.
- Sniper de leilao - deteccao por cor + OCR funcionam, mas os primeiros
  30s costumam ter glitches (fix26 pendente).
- M1 bate 100% as vezes (ver secao 4.5) - tolerado, nao corrigido.

### Nao implementado (backlog)

- Filtro de glitch do OCR em modo leilao (fix26)
- LEILAO_FIM do sniper - hoje hardcoded em 09:05, deveria detectar quando
  a barra deixa de ser azul
- Backtest dos pesos da confluencia (0.60/0.40 e chute)
- Calibrar `LIMIAR_DIRECAO` do `motor_score.py`
- Refatorar `run_sync_module` do `main_pipeline.py` pra nao crashar se
  1 script falha
- Card MTF no `Monitor_Abertura_Leilao_V3.2`

---

## 6. Pontos de atencao (detalhes que ja mordeste)

### Convencoes sutis que precisam ser lembradas

1. **Timezone MT5** - o server da Genial devolve `tick.time` em wall-clock
   BRT (nao UTC). Usar `.replace(tzinfo=BRT)`, nao `.astimezone(BRT)`.
   Bug corrigido no fix47 (v0.11.4).

2. **`confianca_visual`** - e SCORE TECNICO (presenca de 6 criterios), nao
   probabilidade. 100% nao significa "setup perfeito". Ver docstring de
   `calcular_confianca` (fix48).

3. **Eventos de estrutura** - precisam estar ordenados por `idx` (fix44).
   Sem isso, `eventos[-1]` nao era o mais recente.

4. **BOS/CHoCH** - so contam se a direcao bate com o bias (fix43). Senao
   inflavam a confianca indevidamente.

5. **Cache de candles** - chave = (contrato, TF). Rollover (WINV26->WINZ26)
   arquiva o cache antigo em `Coletas/cache/_arquivo/`.

6. **`QTD_REFRESH_INCREMENTAL`** - se a pagina/motor ficar sem chamar
   `obter_candles` por mais que N*TF, o cache tem gap. Hoje: 60 (cobre 5h M5).

7. **`main_pipeline.py`** - os JSONs do V2 sao gerados ANTES do relatorio e
   da gravacao de sessao. Nunca ler o JSON do relatorio esperando estado
   fresco do proximo ciclo.


8. **Minerio de ferro (SGX)** - o indicador de mercado externo usa F1 (front month, SGX:FEF1!) como proxy. O TV scanner nao indexa o continuo do 2o vencimento (SGX:FEF2!), entao F2 nunca chegava no Validador. Fix51 (01/10/2026) removeu toda a infra de "2o mes" (funcao, constante e mapeamento).

### Dividas tecnicas conhecidas

- `detectar_bos_choch` recebe `config` explicito, mas outros detectores
  ainda usam `CONFIG` global
- `Gerar_Relatorio_Mensagem.py` foi refatorado pra usar `global` (fix30) -
  funciona, mas nao e elegante
- Alguns scripts na raiz fazem parte do pipeline, outros sao one-shot
  (diagnostico, fix). Distinguir pelo conteudo, nao pelo nome.
- **VIX com change_percent instavel** - em 01/10/2026, o mesmo preco (16.33) apareceu como 0.0% e 0.98% em rodadas consecutivas. Provavelmente fonte (TVC:VIX) ou calculo do Validador. Investigar quando houver tempo.
