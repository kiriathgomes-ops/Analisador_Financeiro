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


9. **MT5 stale pos-fim de semana (05/10/2026)** - o terminal Genial perdeu conexao as 12:51 e so reconectou as 14:50 (levou ~2h). Durante esse tempo, `bid/ask/last/session_close` ficaram presos no fechamento de quinta (187k) enquanto o mercado estava em 209k.

   Licao aprendida (registrada apos tentativa errada do fix58):
   - NAO comparar brapi `settlement` (ajuste oficial do dia anterior) com MT5 `bid/ask` (preco atual). A divergencia entre eles e o GAP, nao um erro.
   - Para validar consistencia: comparar brapi `settlement` com MT5 `session_close` (ambos sao ajustes do mesmo dia).
   - Se MT5 estiver stale, `WIN_AJUSTE` deve vir do brapi e `WIN_FUT` continua do MT5 (preco vivo).

   Fix defensivo pendente: detectar stale via `|session_close - settlement_brapi| > 500` e priorizar brapi no ajuste.

### Dividas tecnicas conhecidas

- `detectar_bos_choch` recebe `config` explicito, mas outros detectores
  ainda usam `CONFIG` global
- `Gerar_Relatorio_Mensagem.py` foi refatorado pra usar `global` (fix30) -
  funciona, mas nao e elegante
- Alguns scripts na raiz fazem parte do pipeline, outros sao one-shot
  (diagnostico, fix). Distinguir pelo conteudo, nao pelo nome.
- **VIX com change_percent instavel** - em 01/10/2026, o mesmo preco (16.33) apareceu como 0.0% e 0.98% em rodadas consecutivas. Provavelmente fonte (TVC:VIX) ou calculo do Validador. Investigar quando houver tempo.


## 10. Pivots clássicos — fix60

**Bug (05/10/2026):** pivots desordenados no `EstimativaAbertura.json`
(`R2=208k, PP=203k, R1=200k, S2=198k, S1=195k` — ordem invertida).
**Causa:** H/L vinham do `WIN_FUT` (MT5 ao vivo, mid-rally) e C vinha do
`previous_close` do mesmo WIN_FUT (settlement de sexta). Mistura de dias.
**Fix:** H/L/C agora vêm do `WIN_AJUSTE` (settlement B3, mesmo D1 fechado),
consistente com `preco_base` do mesmo arquivo. Guarda `low <= close <= high`
embutida — se incoerente, `pivots={}` + warning.
**Impacto:** decision_engine consome pivots via `market_service._extrair_pivots`
e `v2_orchestrator._ler_novo_motor`. Antes do fix60, decisões usaram pivots
invertidos sem serem bloqueados (fallback `any(pivots.values())` não dispara
com valores não-zero).

## 11. Confluência — fix61/fix62

**Bug (05/10/2026):** `Decisao_V2.json` mostrava `nm_conf=100` + `confianca_final=None`,
sugerindo "NM aprovou com força máxima e algo misterioso barrou". Na verdade,
5 early returns em `_verificar_confluencia` saíam sem preencher `confianca_final`,
e `nm_conf` (que é `|score|` clipado em [0,100]) já tinha sido gravado antes do return.
**Fix61:** campo `motivo_saida` preenchido em todos os 7 caminhos (`smc_neutro`,
`smc_conf_baixa`, `nm_indisponivel`, `nm_divergencia_interna`, `confianca_final_abaixo_minimo`,
`divergencia_smc_nm`, `ok`). `confianca_final` espelha o que a função de fato retornou.
**Fix62:** `nm_conf` documentado como magnitude (não confiança direcional). Adicionados
`nm_magnitude` (alias honesto), `nm_direcao_score` (direção do score agregado) e
`nm_divergencia_interna` (bool). `nm_conf` mantido por retrocompat.

### Débitos técnicos anotados
- `market_service._extrair_pivots`: fallback `preco ± 150/300` é arbitrário — substituir por
  pivots do último D1 fechado ou retornar `{}` explícito.
- `Agendador.py` não suporta `--once`: só roda em loop contínuo. Considerar adicionar flag.
- Entrypoint do orchestrator é `python -m v2.core.engines.v2_orchestrator` (não
  `python v2/core/engines/v2_orchestrator.py` — quebra import de `config`).

  ## 12. Gap — rotulado por fonte (fix63/fix63b)

**Bug (06/10/2026):** leilão (OCR) indisponível → coletor preenche
`abertura_projetada` com a teórica (`fonte_abertura=CALCULADO`), mas o
`motor_previsao` não distinguia e calculava gap como se fosse do leilão.
Operador via `[GAP] +10738 pts (+5.17%) -> EXTREMO` sem saber que esse gap
foi fabricado da teórica (mesma fonte do `var_teorica_pct`).

**Fix63:** campo `fonte` em `ClassificacaoGAP` (default `LEILAO_REAL`).
`classificar_gap` propaga. `motor_previsao` mapeia `fonte_abertura` →
`gap_fonte` (`OCR_LEILAO→LEILAO_REAL`, `CALCULADO→TEORICA_FALLBACK`,
`AJUSTE→AJUSTE_FALLBACK`). Log passa a mostrar `[fonte=...]`.

**Fix63b:** propagação até `Decisao_V2.json` — `PredictionContext` ganha
`gap_fonte`, `prediction_service` lê do JSON (nested ou top-level),
orchestrator expõe em `metadados.novo_motor` e `metadados.precificacao_teorica`.

**Opção escolhida:** B (rotular, não silenciar). Gap continua calculado, score
continua recebendo contribuição; operador e backtest passam a distinguir.

## 13. Trilha C — análise descritiva (796 runs, 23/09 a 06/10)

**Dados analisados:** 796 runs históricos (`Historico_Decisoes_V2`).

**Descobertas:**
- Divergência SMC×NM real é **25,3%** (não estrutural, episódica)
- **Alinhamento pleno: 32,7%** dos runs
- **Um motor neutro: 41,9%** (comportamento conservador esperado)
- **Viés de VENDA no score NM: 48,7% VENDA vs 21,7% COMPRA**
- Saturação em |score|=100: **8,4%** (minoria, não dominante)
- Mediana do |score|: **25,9** — metade dos runs é FRACO

**Simulação LIMIAR_DIRECAO (sem cotovelo claro):**
| LIMIAR | % NEUTRO |
|---|---|
| 5 | 16,4% |
| 10 (atual) | 29,7% |
| 15 | 39,6% |
| 20 | 46,2% |
| 25 | 49,3% |
| 30 | 53,3% |

**Conclusão:** `LIMIAR_DIRECAO=10` não é obviamente errado, mas a curva suave indica que a escolha **precisa de dados de acurácia** (score alto acerta?). Não temos isso ainda.

**Próximas sub-frentes:**
- **C1** — Analisar viés de VENDA (qual componente empurra?)
- **C2** — Coletar outcome (preço pós-abertura) e correlacionar com score
- **C3** — Com C1+C2, escolher limiar empiricamente

**Débito de nomenclatura (anotado):** `nm_magnitude`/`nm_direcao_score` (confluencia) e `score_magnitude`/`score_direcao` (novo_motor) apontam pro mesmo dado — unificar em fix futuro.

## 15. Primeira operação legítima pós-fix66 (07/10/2026)

**Evento:** primeira vez que o orquestrador V2 emite sinal de operação
(`operar=True`) com dados honestos, desde a descoberta do bug dos ADRs.

**Log (07/10/2026, orquestrador rodando):**


**Contexto:**
- SMC: VENDA
- NM: VENDA (score 35.6, forca FORTE)
- Confluência: VENDA (concordância)
- Confiança final: 74%
- Gap: -488 pts, TEORICA_FALLBACK (leilão indisponível, TV cobriu)

**Por que é marco:**
- Antes do fix66, o score NM saturava em 100 (COMPRA forçada) e o SMC era
  VENDA — sempre divergentes, sempre NEUTRO. Nunca operava.
- Pós-fix66, o NM produziu score real (35.6, VENDA). Alinhou com o SMC.
  Confluência passou o gate duplo (smc_conf >= mínima E confianca_final >= 45).
- **Primeiro sinal operacional legítimo do sistema V2.**

**Monitorar nos próximos dias:**
- Win rate real dos sinais (acurácia do score vs outcome)
- Frequência de `operar=True` (se ficar raro demais, `LIMIAR_DIRECAO=10`
  pode estar alto; se ficar frequente demais, pode estar baixo)
- Correlação SMC × NM em dias de operação vs dias neutros

**Débito associado (Trilha C):**
- Distribuição de `score_magnitude` já é honesta (45 runs em 06/10, 0%
  saturação). Calibração empírica de `LIMIAR_DIRECAO` aguarda mais 2-3
  dias de coleta.

  ## 16. Fantasmas estáveis do minerador (ruído conhecido)

Os 9 campos abaixo aparecem como TYPO_REAL no `investigar_fantasmas.py` (v5)
mas NÃO são bugs — são padrões que o detector (regex) não distingue:

| Campo | Padrão real |
|---|---|
| `contratos` | fallback `contratos_vigentes or contratos` (fix71) |
| `estimativas_abertura` | fallback singular+plural (fix71) |
| `pontos_ajuste_base` | fallback `preco_referencia_base` (fix71) |
| `preco_carregado_di` | fallback `preco_teorico_carregado` (fix71) |
| `filtro_volume_aplicado` | corrigido p/ `filtro_volume_real_aplicado` (fix72) |
| `opening_scenario` | lido do Historico_Aberturas (fix73) |
| `direcao_provavel` | derivado de opening_scenario (fix73) |
| `relacao_com_ajuste` | derivado de opening_scenario (fix73) |
| `data_execucao` | Pipeline_Log.json nao existe (fix69 tratou UI) |

**Decisão (07/10/2026):** manter visíveis em vez de whitelist.
- Vantagem: se algum desses quebrar no futuro, aparece imediatamente
- Custo: 9 linhas de ruído em cada rodada (aceitável)
- Se crescerem, investigar; se estáveis, ignorar

**Regra de ouro:** o `investigar_fantasmas.py` aponta candidatos;
a validação final é sempre humana (grep direcionado + leitura do código).


## 17. Trilha C — análise de 181 runs honestos (07/10/2026)

**Objetivo:** calibrar `LIMIAR_DIRECAO` com dados pós-fix66.

### Números

| Métrica | 796 contaminados | 181 honestos |
|---|---|---|
| Alinhamento SMC×NM | 32.7% | **66.4%** |
| Confluência `ok` | 0% | **53.6%** |
| Saturação em 100 | 8.4% | **0%** |
| `gap_fonte=LEILAO_REAL` | — | **92.8%** |

**Sistema saiu de "nunca opera" (0% ok) para "opera 53.6% do tempo".**

### Limiar

Distribuição do score é **bimodal**:
- NEUTRO (06/10): 45 runs com score 0-7.4
- VENDA (07/10): 136 runs com score 25.7-52.5

**Não há valores entre 10 e 25.** Isso significa que `LIMIAR=10` está no "cotovelo" natural — qualquer valor entre 10 e 25 produz o mesmo resultado. **Manter 10.**

### 0% COMPRA (07/10) — não é bug

Análise confirmou: **6/6 ADRs batem com TradingView real** (VALE=-3.34,
PETR=+0.80, ITUB=-4.04, BBAS=-2.78, BBD=-3.77, B3=-2.07). Mercado americano
virou ao longo do dia (08:38 misto → 19:00 todo em queda).

**Conclusão:** 0% COMPRA reflete mercado real. Score 40.8 VENDA é legítimo.

### Ponto de design: `adrs` domina o score

O componente `adrs` contribui ±38 tipicamente (6 ADRs × ±3% × 2.5).
Os outros somam ~±15. **Isso não é bug — é design** (peso 0.25 e variação
natural dos 6 ADRs). Vale calibrar em versão futura, se desejado:
- Opção A: reduzir peso do `adrs` (0.25 → 0.15)
- Opção B: normalizar (dividir por N=6 antes de multiplicar)
- Opção C: manter como está (mercado real é volátil mesmo)

**Decisão:** manter como está. Calibração só depois de mais dados (mín. 10 dias).


## 18. Timezone MT5 — convenção do projeto (07/10/2026)

### Configuracao

| Fonte | Timezone |
|---|---|
| Windows (host) | **BRT (UTC-3)** |
| MT5 Genial | **BRT (UTC-3)** — mesmo do host |
| B3 pregao regular | 10:00 - 17:00 BRT |
| WIN after-market | 17:00 - 18:30 BRT |

### Quirk do `tick.time`

O MT5 retorna `tick.time` como epoch calculado a partir do **horario local
do servidor** (BRT), mas o epoch parece UTC quando lido pelo Python.
Verificado em 07/10/2026 (tick WINV26 = 1791397872):

```python
from datetime import datetime, timezone, timedelta

# ERRADO — parece UTC mas é BRT
dt = datetime.fromtimestamp(tick.time, tz=timezone.utc)
# → 18:31:12 "UTC" (iluso — na verdade é BRT)

# CORRETO — ler como BRT
dt_brt = datetime.fromtimestamp(tick.time, tz=timezone.utc).replace(tzinfo=None)
# → 18:31:12 (BRT real)

# Para UTC real: somar |offset|
dt_utc = datetime.fromtimestamp(tick.time, tz=timezone.utc) + timedelta(hours=3)
# → 21:31:12 UTC

## 19. Motor de Visão IA — feature inacabada (07/10/2026)

**Achado:** 3 pages do Streamlit leem `Coletas/AnaliseGraficaSMC.json`:
- `pages/7.2_🤖_IA_SpikeImagem.py` — anomalias visuais / spikes LTF (1min)
- `pages/7.3_📥_Gerador_Profit_Pro.py` — dropdown com 2 fontes (algó OU IA)
- `pages/7.4_🤖_IA_Imagem.py` — insights SMC via Visão Computacional (5min)

**Problema:** o arquivo **nunca é gerado** por nenhum script do projeto.
Nenhum produtor em `Coletor.py`, `Motor_SMC_Regras.py` ou qualquer outro.
Não existe constante `FILE_SMC_VISAO_IA` no `config.py` — cada page
define localmente (hardcoded).

**Diagnóstico:** feature planejada (Motor de Visão IA — OCR/análise de
imagem de gráfico) que **nunca foi implementada**. As 3 pages foram
criadas antecipando o output.

**Comportamento atual:**
- 7.2 / 7.3: `carregar_json_defensivo` retorna `{}` → empty state silencioso
- 7.4: mostra `❌ Erro: O arquivo não foi encontrado... O motor contextual
  de visão precisa ser executado pelo Orq...` — **alarme falso** (motor
  nunca existiu)

**Ação tomada:** documentado aqui + adicionado ao `melhorias.md` como
feature futura. Nenhuma mudança de código (as 3 pages ficam navegáveis).

**Ver também:** item 16 (fantasmas estáveis do minerador) — onde
`AnaliseGraficaSMC.json` aparece como fantasma legítimo.


