# Mapeamento de Campos — V1/Atual → Modelo de Dados V2

**Projeto:** Analisador Financeiro — V2  
**Foco:** Previsão de Abertura WINFUT  
**Data:** 2026-08-16  
**Status:** Referência oficial da FASE 4

---

## Princípios

1. WINFUT é o único instrumento operacional.
2. TradingView → referência de **ajuste** (close).
3. MT5 → referência de **last** e contrato real.
4. Ativos externos são **contexto**, não sinal de ordem.
5. Dado bruto ≠ dado calculado ≠ decisão.

---

## 1. WinSession (núcleo operacional)

| Campo V2 | Fonte atual | Caminho / campo | Tipo | Observação |
|----------|-------------|-----------------|------|------------|
| `metadata.data_sessao` | — | derivar de timestamp | date | Ainda não isolado |
| `metadata.timestamp_coleta` | `Dados_MT5_v2_2.json` | `timestamp` | datetime ISO | Coletor MT5 |
| `metadata.contrato_principal` | `Dados_MT5_v2_2.json` | `ativos.WIN.contrato_principal` | str | Ex: WINV26 |
| `metadata.fonte_last` | item WIN_LAST_TICK | `fonte` | str | "MT5_v2.2" ou "MT5_v1" |
| `precos_referencia.ajuste` | `DadosAtivosUnificados.json` | `ativos.WIN_AJUSTE.preco` | float | TradingView close |
| `precos_referencia.last_mt5` | `Dados_MT5_v2_2.json` | `ativos.WIN.last` | float | Preferencial |
| `precos_referencia.last_mt5` (alt) | `DadosAtivosUnificados.json` | `ativos.WIN_LAST_TICK.preco` | float | Fallback unificado |
| `precos_referencia.fechamento_anterior` | — | — | float | **Não existe** (requer histórico) |
| `precos_referencia.pre_abertura` | — | — | float | **Não existe** (coleta pré-09:00) |
| `distancias.last_vs_ajuste_pts` | calcular | `last_mt5 - ajuste` | float | |
| `distancias.last_vs_ajuste_pct` | calcular | `(last_mt5 / ajuste - 1) * 100` | float | |
| `distancias.pre_abertura_vs_ajuste_pts` | calcular | depende de pré-abertura | float | Futuro |
| `distancias.pre_abertura_vs_fechamento_pts` | calcular | depende de pré-abertura | float | Futuro |
| `gap.gap_projetado_pts` | `EstimativaAbertura.json` | `abertura_teorica_pontos - pontos_ajuste_base` | float | Ou recalcular |
| `gap.gap_projetado_pct` | `EstimativaAbertura.json` | `estimativas_abertura.WIN_INDICE.variacao_teorica_pct` | float | Já existe |
| `gap.direcao_gap` | calcular | sinal do gap | str | ALTA / BAIXA / NEUTRO |
| `niveis.pivot_pp` | `EstimativaAbertura.json` | `pivot_points.WIN_FUT.PP` | float | |
| `niveis.r1` | `EstimativaAbertura.json` | `pivot_points.WIN_FUT.R1` | float | |
| `niveis.r2` | `EstimativaAbertura.json` | `pivot_points.WIN_FUT.R2` | float | |
| `niveis.s1` | `EstimativaAbertura.json` | `pivot_points.WIN_FUT.S1` | float | |
| `niveis.s2` | `EstimativaAbertura.json` | `pivot_points.WIN_FUT.S2` | float | |

---

## 2. MarketContext (contexto externo)

| Campo V2 | Fonte atual | Caminho | Tipo |
|----------|-------------|---------|------|
| `volatilidade.vix` | `DadosAtivosUnificados.json` | `ativos.VIX.preco` | float |
| `volatilidade.vix_var_pct` | idem | `ativos.VIX.variacao_pct` | float |
| `indices_eua.sp500_fut` | idem | `ativos.SP500_FUT.preco` | float |
| `indices_eua.sp500_var_pct` | idem | `ativos.SP500_FUT.variacao_pct` | float |
| `indices_eua.nasdaq_fut` | idem | `ativos.NASDAQ_FUT.preco` | float |
| `indices_eua.nasdaq_var_pct` | idem | `ativos.NASDAQ_FUT.variacao_pct` | float |
| `cambio_e_dolar.dxy` | idem | `ativos.DXY.preco` | float |
| `cambio_e_dolar.dxy_var_pct` | idem | `ativos.DXY.variacao_pct` | float |
| `cambio_e_dolar.usd_brl` | idem | `ativos.USD_BRL.preco` | float |
| `cambio_e_dolar.usd_brl_var_pct` | idem | `ativos.USD_BRL.variacao_pct` | float |
| `cambio_e_dolar.usd_ptax` | idem | `ativos.USD_PTAX.preco` | float |
| `adrs_brasileiras.vale` | idem | `ativos.VALE_ADR.preco` + `.variacao_pct` | float |
| `adrs_brasileiras.petr` | idem | `ativos.PETR_ADR.*` | float |
| `adrs_brasileiras.itub` | idem | `ativos.ITUB_ADR.*` | float |
| `adrs_brasileiras.bbd` | idem | `ativos.BBD_ADR.*` | float |
| `adrs_brasileiras.bbas` | idem | `ativos.BBAS_ADR.*` | float |
| `adrs_brasileiras.b3` | idem | `ativos.B3_ADR.*` | float |
| `adrs_brasileiras.indicador_adrs` | `Metricas_Calculadas.json` | `indicadores_compostos.indicador_adrs_brasileiras` | float |
| `commodities.iron_ore` | `DadosAtivosUnificados.json` | `ativos.IRON_ORE.*` | float |
| `commodities.iron_ore_2m` | idem | `ativos.IRON_ORE_2M.*` | float |
| `commodities.crude_oil` | idem | `ativos.CRUDE_OIL.*` | float |
| `commodities.gold` | idem | `ativos.GOLD.*` | float |
| `juros.di1_2027` | idem | `ativos.DI1_2027.preco` | float |
| `juros.di1_2029` | idem | `ativos.DI1_2029.preco` | float |
| `juros.inclinacao_bps` | `Metricas_Calculadas.json` | `curva_juros_b3.inclinacao_29_27_bps` | float |

---

## 3. OpeningScenario (previsão de abertura)

| Campo V2 | Fonte atual | Situação |
|----------|-------------|----------|
| `direcao_provavel` | `Decisao_Core.json` / Estimativa | Parcial (viés legado) |
| `probabilidade_direcao` | — | **Não existe** (hoje é score) |
| `relacao_com_ajuste.posicao` | calcular | `last_mt5 ? ajuste` → ACIMA / ABAIXO / NO_AJUSTE |
| `relacao_com_ajuste.cenario_principal` | — | **Não existe** |
| `relacao_com_ajuste.probabilidade_cenario` | — | **Não existe** |
| `comportamentos_possiveis.romper_e_continuar` | — | **Não existe** |
| `comportamentos_possiveis.testar_e_rejeitar` | — | **Não existe** |
| `comportamentos_possiveis.testar_e_recuperar` | — | **Não existe** |
| `comportamentos_possiveis.retornar_ao_ajuste` | — | **Não existe** |
| `comportamentos_possiveis.falso_rompimento` | — | **Não existe** |
| `niveis_observacao` | pivots + ajuste + abertura teórica | Parcial |
| `contexto_resumo` | — | **Não existe** |
| `cenario_alternativo` | — | **Não existe** |
| `confianca_geral` | score Engine_Vies | Parcial (escala diferente) |

---

## 4. SessionHistory (FASE 5 — reservado)

| Campo V2 | Situação |
|----------|----------|
| `data` | Futuro |
| `ajuste` | Futuro |
| `last_pre` | Futuro |
| `abertura_real` | Futuro |
| `gap_real_pts` | Futuro |
| `direcao_real` | Futuro |
| `testou_ajuste` | Futuro |
| `rejeitou_ajuste` | Futuro |
| `rompeu_ajuste` | Futuro |
| `continuou_direcao` | Futuro |
| `reverteu` | Futuro |
| `maxima_sessao` / `minima_sessao` | Futuro |
| `resultado_resumo` | Futuro |

---

## 5. Ordem de leitura recomendada (builder V2)

1. **`Dados_MT5_v2_2.json`** → contrato_principal, last, bid, ask, volume, timestamp  
2. **`DadosAtivosUnificados.json`** → ajuste (WIN_AJUSTE), todo o contexto externo  
3. **`EstimativaAbertura.json`** → gap teórico, pivots  
4. **`Metricas_Calculadas.json`** → indicador ADRs, inclinação DI, spreads  
5. **`Decisao_Core.json`** → viés legado (referência, não fonte primária da V2)

---

## 6. Lacunas críticas

| Lacuna | Impacto | Fase de resolução |
|--------|---------|-------------------|
| Pré-abertura | Impede distância pré × ajuste e gap real de abertura | FASE 5 / coleta dedicada |
| Fechamento anterior | Impede comparação com sessão anterior | FASE 5 (histórico) |
| Probabilidades de cenário | Hoje só existe score, não distribuição | FASE 6 |
| Comportamentos (romper / testar / rejeitar) | Core do motor de previsão | FASE 6 |
| Histórico de sessões | Base estatística | FASE 5 |

---

## 7. Notas importantes

- **WIN_AJUSTE ≈ WIN_FUT** não é duplicidade. Ambos vêm do close do TradingView e servem como referência de ajuste.
- **WDO** e dados de dólar permanecem apenas como contexto. Não entram no WinSession operacional.
- O arquivo unificado (`DadosAtivosUnificados.json`) é um **resumo**. Campos como bid/ask/volume detalhados estão apenas no `Dados_MT5_v2_2.json`.
- Qualquer alteração neste mapeamento deve ser versionada e documentada.

---

*Documento gerado na FASE 4 do Prompt Master de Continuidade — Analisador Financeiro V2.*
