# DESCRITIVO COMPLETO — Pasta `Coletas`
## Projeto: Analisador_Financeiro

**Data da varredura:** 26/10/2026  
**Script de origem:** `_mapear_dados_spike.py`  
**Raiz:** `E:\ProjetosPython\Analisador_Financeiro\Coletas`  
**Modo:** Read-Only (apenas leitura e mapeamento)

---

## 1. Visão Geral do Sistema

A pasta `Coletas` é o **repositório central de dados operacionais** do Analisador_Financeiro.  
Ela concentra:

- Coletas de preços em tempo real e históricos
- Análises técnicas baseadas em **Smart Money Concepts (SMC)**
- Análises de tendência multiativos
- Decisões de trade automatizadas (versão 2)
- Dados de MT5 (MetaTrader 5)
- Notícias e calendário econômico
- Estimativas de abertura e pivôs institucionais
- Históricos de decisões e snapshots de mercado
- Cache de candles (1m, 5m e 15m)

O sistema é orientado principalmente ao **mini índice WIN** (contrato WINZ26 no momento da coleta) e ao **dólar futuro WDO**, com suporte a dezenas de ativos correlacionados (ADRs, commodities, índices americanos, curva de juros DI1, etc.).

---

## 2. Estrutura de Pastas

```
Coletas/
├── [arquivos raiz - análises e coletas atuais]
├── cache/                          → Cache de candles históricos
├── coleta_preco_teorico_historico/ → Histórico diário de preço teórico de abertura
├── Historico_Aberturas/            → Snapshots diários de abertura e posição
├── Historico_Decisoes_V2/          → Histórico completo de decisões do motor V2
└── Historico_MT5/                  → Snapshots históricos do coletor MT5
```

---

## 3. Arquivos Principais (Raiz)

### 3.1 Análises SMC (Smart Money Concepts)

| Arquivo | Tamanho | Descrição |
|---------|---------|-----------|
| `AnaliseGraficaSMC_MTF.json` | 1.9 KB | Análise Multi-Timeframe (15m + 5m + 1m) com confluência de bias |
| `AnaliseGraficaSMC_Regras.json` | 8.2 KB | Análise SMC no timeframe 5m (fonte: regras_smc) |
| `AnaliseGraficaSMC_Regras_M1.json` | 8.1 KB | Análise SMC no timeframe 1m |
| `AnaliseGraficaSMC_Regras_M15.json` | 6.9 KB | Análise SMC no timeframe 15m |

**Campos comuns nas análises SMC:**
- `ativo`: WINZ26
- `preco_atual`: 178360.0
- `bias_direcional` e `direcao_estrutura`: ALTA
- `bos` / `choch`: Break of Structure / Change of Character
- `order_blocks`, `fair_value_gaps`, `liquidez` (BSL/SSL)
- `eventos_estrutura`, `swings_recentes`
- `entrada_sugerida`, `stop_sugerido`, `alvos`
- Flag `stale: true` (candle antigo — ~270 minutos)

### 3.2 Análises de Tendência e Spike

| Arquivo | Descrição |
|---------|-----------|
| `Analise_Tendencias.json` | 33 ativos com estrutura padronizada (`precos`, `intervalo_10_para_5`, `intervalo_5_para_0`, `padrao_comportamento`) |
| `AnaliseSpike_IA.json` | Análise gerada por IA (Groq) + código NTSL gerado |
| `AnaliseSpike_IA_Expert.json` | Versão Expert SMC da análise por IA |

**Ativos monitorados em `Analise_Tendencias.json` (principais):**
- Futuros B3: WIN1!, WDO1!, DI1F2027, DI1F2029
- Ações: PETR4, VALE3, ITUB4, BBDC4, BBAS3, B3SA3
- ADRs: PBR, VALE, ITUB, BBD, BOLSY, BDORY
- Índices/Commodities: ES1!, NQ1!, CL1!, GOLD, VIX, DXY, EWZ
- Câmbio: USDBRL, USDMXN, USD_PTAX

### 3.3 Coletas de Mercado

| Arquivo | Descrição |
|---------|-----------|
| `Coleta_ram.json` | Coleta em memória (33 ativos) |
| `Coleta_rom-0.json` até `Coleta_rom-55.json` | Coletas persistidas em intervalos de 5 minutos (0, 5, 10...55) |
| `Dados_MT5_v2_2.json` | Snapshot atual do MetaTrader 5 (WIN, WDO, DI1) |
| `Dados_Validados.json` | Ativos após validação de qualidade |
| `DadosAtivosUnificados.json` | Visão unificada dos 33 ativos |
| `LastTick_Congelado.json` | Últimos ticks de WIN e WDO congelados |

### 3.4 Decisão e Métricas

| Arquivo | Descrição |
|---------|-----------|
| `Decisao_V2.json` | Decisão operacional atual (vies_final, confiança, entrada, etc.) |
| `Metricas_Calculadas.json` | Spread WDO×PTAX, curva de juros, VIX, DXY, performance relativa de ADRs e índices |
| `Resultado_Calculadora_Operacional_Abertura.json` | Resultado consolidado da calculadora de abertura |
| `EstimativaAbertura.json` + `EstimativaAbertura_Cache.json` | Estimativa de abertura do WIN + pivôs institucionais (POC e VWAP de ontem) |

### 3.5 Notícias e Calendário

| Arquivo | Descrição |
|---------|-----------|
| `Noticias_Calendario.json` | Calendário econômico do dia |
| `Noticias_Calendario_0900.json` | Alerta específico de notícias 3 estrelas às 09:00 |
| `Noticias_Impacto_Dia.json` | Resumo de impacto e classificação de risco de notícias |

### 3.6 Outros

| Arquivo | Descrição |
|---------|-----------|
| `preco_teorico_win_fluxo.csv` | Fluxo de preço teórico do WIN no dia (25 linhas) |
| `snapshot_rompimento_10h.txt` | Prompt de análise de rompimento às 10:00 |
| `config_regiao.json` | Coordenadas de região de captura (top, left, width, height) |
| `Relatorio_Executivo.md` | Relatório executivo (ignorado na varredura por extensão) |
| `WIN_15min.png` / `WIN_5min.png` | Screenshots de gráficos (ignorados) |

---

## 4. Subpastas Detalhadas

### 4.1 `cache/` — Candles Históricos

Armazena séries de candles do WIN (contratos WINV26 e WINZ26):

| Arquivo | Timeframe | Candles | Atualizado em |
|---------|-----------|---------|---------------|
| `candles_WINZ26_1m.json` | 1m | 1000 | 26/10/2026 23:00 |
| `candles_WINZ26_5m.json` | 5m | 1500 | 26/10/2026 23:00 |
| `candles_WINZ26_15m.json` | 15m | 1038 | 26/10/2026 23:00 |
| `candles_WINV26_*` | 1m/5m/15m | Variável | 13/10/2026 (contrato anterior) |

Estrutura típica de cada candle:
```json
{
  "time": "2026-10-23T10:57:00-03:00",
  "open": 207805.0,
  "high": ...,
  "low": ...,
  "close": ...,
  "volume": ...
}
```

### 4.2 `coleta_preco_teorico_historico/`

Histórico diário de preço teórico de abertura do WIN (CSV).  
Arquivos nomeados por data (`preco_teorico_YYYY-MM-DD.csv`).  
Colunas típicas: `DataHora`, `PrecoTeorico`, `Confianca`, `Motivo`  
Motivos comuns: `MUDANCA_LEILAO`, `FORCADO_TEMPO_LEILAO`, `MUDANCA`, `FORCADO_TEMPO`.

Período coberto: de 15/09/2026 até 23/10/2026 (com algumas lacunas).

### 4.3 `Historico_Aberturas/`

Snapshots diários completos da abertura e evolução do dia.

- Arquivos: `YYYY-MM-DD.json`
- Contém lista de `atualizacoes` (tag “pipeline”)
- Último snapshot do dia com: contrato, ajuste, last_mt5, distância em pontos, posição, etc.
- Exemplo: 26/10/2026 → 196 snapshots

### 4.4 `Historico_Decisoes_V2/`

Histórico denso de decisões do motor de decisão V2.

- ~986 arquivos
- Nomeação: `YYYYMMDD_HHMMSS.json`
- Estrutura idêntica a `Decisao_V2.json` (metadata + contextos + decisão + erros)
- Frequência aproximada: a cada 5 minutos durante o pregão

### 4.5 `Historico_MT5/`

Snapshots históricos do coletor MT5 versão 2.2.

- ~997 arquivos
- Nomeação: `MT5_v2_2_YYYYMMDD_HHMMSS_xxxxxx.json`
- Contém status de conexão, versão do terminal e dados de WIN, WDO e DI1

---

## 5. Características Técnicas Observadas

1. **Foco principal:** WIN (mini índice Bovespa) + WDO (dólar futuro)
2. **Metodologia dominante:** Smart Money Concepts (Order Blocks, FVG, BOS, CHoCH, liquidez BSL/SSL)
3. **Multi-timeframe:** 1m, 5m e 15m com confluência
4. **Integração MT5:** Coletor próprio versão 2.2
5. **IA integrada:** Análises geradas via Groq (Spike_IA e Expert SMC) com geração de código NTSL
6. **Validação de dados:** Pipeline de validação (`Dados_Validados.json`)
7. **Congelamento de ticks:** Mecanismo para capturar last tick fora do pregão
8. **Calendário econômico:** Alertas específicos para 09:00 e classificação de impacto
9. **Histórico denso:** Decisões e MT5 gravados praticamente a cada 5 minutos
10. **Estado “stale”:** As análises SMC do dia 26/10/2026 às 23:00 estão marcadas como stale (candle com ~4,5 horas de idade), indicando que o pregão já havia encerrado.

---

## 6. Propósito do Sistema

O conjunto de arquivos indica um **sistema de análise e decisão operacional em tempo real** para day trade / scalp no mini índice, com as seguintes capacidades:

- Coleta multi-fonte (BRAPI, MT5, TradingView-like, etc.)
- Análise técnica institucional (SMC)
- Análise de tendência de ativos correlacionados
- Integração de notícias e risco de calendário
- Geração de decisão estruturada (vies, entrada, stop, alvos)
- Geração de código NTSL para plataformas de execução
- Histórico completo para backtest e auditoria
- Estimativa de abertura e pivôs institucionais

---

## 7. Observações Finais

- A varredura foi executada em modo **somente leitura**.
- Arquivos de imagem (`.png`) e Markdown (`.md`) foram ignorados pelo script de mapeamento.
- Existe um arquivo de backup de teste (`candles_WINV26_1m.json.bak_teste`).
- O sistema mantém tanto dados “ao vivo” quanto históricos densos, permitindo reconstrução completa do fluxo de decisão de qualquer momento do pregão.

---

**Arquivo gerado automaticamente a partir da saída do script `_mapear_dados_spike.py`**  
**Projeto:** Analisador_Financeiro  
**Data de geração do descritivo:** 26/10/2026
