# PLAYBOOK SPIKE — Contexto, Regras e Retomada

> Documento vivo. Atualizar ao fim de cada sessão.
> Última atualização: 2026-10-26, sessão de blindagem Fase 2 (em andamento).

---

## PARTE 1 — REGRAS DO PROJETO (LEIA PRIMEIRO)

Sou desenvolvedor Python solo, construindo um ecossistema de análise financeira
e day trade para B3 (WIN / WDO). Trabalho com um agente IA em sessões longas.

**Regras que a IA deve seguir SEMPRE:**
1. **Não encerrar a sessão** sem eu pedir explicitamente.
2. **Sempre arquivos .py COMPLETOS** (nunca patches isolados, exceto quando eu pedir).
3. **Comandos com `--dry-run`**: mande o dry-run primeiro e **aguarde meu retorno**.
4. **Não use "provavelmente"** para classificar bug — confirme ou marque como **suspeita**.
5. **PowerShell quebra com aspas em f-string** — prefira scripts `.py` temporários.
6. **1 comando por vez**, aguarde meu retorno antes de mandar o próximo.
7. Se for mexer em arquivo que você não tem em mãos, **peça o código atual**.

---

## PARTE 2 — ESTADO DO PROJETO (o que está fechado)

### ✅ Concluído e validado em produção

| Componente | Versão | Status |
|------------|--------|--------|
| `Coletor.py` | v2.9 | Sessão inteligente Pré/Regular/Pós com fuso BRT |
| `Calculadora.py` | — | Trava de ADRs 15% → 50% (não descarta quedas reais) |
| `NOVO_MOTOR_PREVISAO_ABERTURA` | — | `MAX_GAP_REALISTA=50000` movido para `pesos.yaml` |
| `v2/config.py` | — | Centraliza `PESOS_CONFLUENCE` e limiares do opening_scenario |
| `v2/core/engines/decision_engine.py` | v2.2 | Blindado contra pivôs fantasmas (não inventa níveis) |
| `v2/core/services/vision_service.py` | v2.0 | Lê SMC real (não adivinha por tendência) |
| `pages/7.2.1_SpikeImagem_Expert.py` | v5.2 | Foco SMC puro + validação R:R no Python (≥1:2) |
| `pages/7.4_Spike_Texto.py` | v2.7.3 | Contexto otimizado (anti-rate-limit) + Modo Direto estrito + Híbrido |
| `Motor_SMC_Regras.py` | v3.4 | Blindagem `except:pass` → `logger.warning` ✅ |
| `analisar_rompimento_10h.py` | v3.1 | Blindagem `except:pass` → `print` ✅ |

### ✅ Fase 1 da faxina (concluída)

- Removidos: `arvore_projeto.txt`, `dump_motor.txt`, `dump_v2.txt`, `_gerar_dump_*.py`, `_test_*.py`, `_audit_pente_fino.py`, `_relatorio_pente_fino.txt`
- `v2/main.py` movido para `lixeira_analise/` (era legado de testes)
- `requirements.txt` verificado e OK (`MetaTrader5`, `streamlit`, `groq`, `PyYAML`, `pandas`, `plotly`, etc.)

### 🔧 Fase 2 em andamento — Blindagem de `except:pass`

Objetivo: trocar `except: pass` silencioso por log de aviso. **Arquivo por arquivo.**

| Arquivo | `except:pass` | Status |
|---------|---------------|--------|
| `Motor_SMC_Regras.py` | 4 | ✅ concluído e testado |
| `analisar_rompimento_10h.py` | 3 | ✅ concluído e testado |
| **`cache_candles.py`** | **8** | **⏳ PRÓXIMO ALVO** |
| `Coletor_MT5_v2_2.py` | 2 | ⏸️ pendente |
| `Coletor.py` | (verificar) | ⏸️ pendente |
| `CalculadoraEstimativaAbertura.py` | 1 | ⏸️ pendente |
| `config.py` | 1 | ⏸️ pendente |
| `Gerar_Relatorio_Mensagem.py` | 1 | ⏸️ pendente |
| `Limpar_Imagens_TradingView.py` | 1 | ⏸️ pendente |
| `Rodar_SMC_Regras.py` | 1 | ⏸️ pendente |
| `win_abertura_sniper.py` | 1 | ⏸️ pendente |
| `KeyManager.py` | 1 | ⏸️ pendente |
| `pages/*.py` | vários | ⏸️ baixa prioridade (UI) |

---

## PARTE 3 — PENDÊNCIAS MAPEADAS (não iniciadas)

| ID | Item | Bloqueio |
|----|------|----------|
| D2 | Calibrar `ob_poc_dist_win` no Motor SMC | Aguarda 20-30 trades reais em produção |
| D3 | Mover `CONFIANCA_MINIMA_SMC_PEPITA=85` para `config.py` | Cosmético, 15 min |
| D4 | README documentando "~15% de execução é normal" | Cosmético, 10 min |
| — | Few-shot no Spike Desk (se a consistência piorar) | Opcional |

---

## PARTE 4 — ARQUITETURA (para orientação)

### Fluxo do pipeline (main_pipeline.py, 7 fases)

1. **Fase 1**: Limpeza de imagens
2. **Fase 2**: Coletor + Notícias/Calendário (paralelo)
3. **Fase 3**: Análise Notícias + Validador + **SMC** + Tendências + **Snapshot ORB**
4. **Fase 4**: Calculadora Macro + Estimativa Abertura (paralelo)
5. **Fase 5**: Consolidação Operacional
6. **Fase 6**: **V2 Orchestrator** (Decisão Final)
7. **Fase 7**: Relatório Markdown + Gravação Histórica

### Regras de negócio críticas

- **Pepita**: SMC conf ajustada por MTF **≥ 85%**, senão hard block.
- **Stale**: SMC sobre candle com idade **> 15 min** bloqueia operação.
- **R:R mínimo**: alvo 1 sempre **≥ 1.5× stop** (Motor v3.2+).
- **Ativos inversos ⟲**: WDO, DI1, VIX, DXY, **OURO** (sobe = ruim p/ WIN).
- **Gap Extremo**: se gap vs ajuste B3 **> 1000 pts**, SMC perde prioridade (prioriza Novo Motor).
- **SMC Expirado**: se preço atual > 500 pts da entrada sugerida, entrada expirou.
- **Op 3 (ORB)**: bloqueia se vela 10h ausente OU amplitude > 700 OU Regra 10 (gap > 500).

### Services (v2/core/services/)
- `market_service.py` — Lê DadosAtivosUnificados + Metricas → MarketContext
- `prediction_service.py` — Chama NOVO_MOTOR → PredictionContext
- `news_service.py` — Lê Noticias_Impacto_Dia → NewsContext
- `vision_service.py` — Lê AnaliseGraficaSMC_Regras → VisionContext
- `leilao_service.py` — Lê CSV do OCR com filtro de outliers (mediana ± 2000)
- `win_session_builder.py` — Monta WinSession para o motor de cenários
- `session_history.py` — Salva histórico diário em Coletas/Historico_Aberturas/

### Engines (v2/core/engines/)
- `confluence_engine.py` — Vota (pesos em v2/config.py)
- `decision_engine.py` — Entrada/Stop/Alvos (blindado contra pivôs fantasmas)
- `opening_scenario_engine.py` — Cenários de abertura (WinSession → OpeningScenario)
- `v2_orchestrator.py` — Maestro final: aplica Pepita + Stale + Visão C

### Pages (Streamlit)
- `7.1_SMC_Regras.py` — Cockpit visual do SMC
- `7.2.1_IA_SpikeImagem_Expert.py` — Vision AI (análise de imagem)
- `7.4_IA_Spike_Texto.py` — Spike Desk (chat de texto)
- `7.3_Gerador_Profit_Pro.py` — Gera NTSL para Profit Pro
- `7_Análise_Tendência.py` — Histograma de 12 janelas

---

## PARTE 5 — BLOCO DE RETOMADA (cole no chat novo)



CONTEXTO DE RETOMADA — Analisador Financeiro B3

Sou dev Python solo. Continuando sessão longa de auditoria e blindagem.
REGRAS: (1) não encerrar sem eu pedir; (2) .py COMPLETOS, nunca patches;
(3) --dry-run primeiro + aguardar; (4) sem "provavelmente"; (5) PowerShell
quebra com aspas em f-string → prefira scripts .py temporários; (6) 1 comando
por vez, aguarde meu retorno.

ESTADO: Fases A/B/C/D1 fechadas. Coletor v2.9, Novo Motor com YAML,
DecisionEngine v2.2, VisionService v2.0, Spike Vision v5.2, Spike Desk v2.7.3.

EM ANDAMENTO: Fase 2 — blindagem de except:pass arquivo por arquivo.
✅ Motor_SMC_Regras.py (v3.4) — concluído e testado.
✅ analisar_rompimento_10h.py (v3.1) — concluído e testado.
⏳ PRÓXIMO: cache_candles.py (8 except:pass nas linhas 42,56,62,262,353,395,432)

PENDENTES: D2 (calibrar OBs, aguarda trades reais), D3 (Pepita p/ config),
D4 (README). Few-shot opcional.

🎯 PONTO EXATO: acabei de validar analisar_rompimento_10h.py. Me peça o
cache_candles.py completo para eu blindar os 8 except:pass dele.


---

## PARTE 6 — CHECKLIST DE RETOMADA TÉCNICA

Se algum dia o ambiente parecer estranho, rode esta sequência de diagnóstico:

```powershell
# 1. Versões em disco
python -c "import Motor_SMC_Regras as m; print('Motor:', m.CONFIG.rr_minimo, '| stale:', m.CONFIG.stale_idade_max_min)"
python -c "import v2.core.engines.v2_orchestrator as o; import inspect; print('V3.4.1:', 'V3.4.1' in inspect.getsource(o))"
python -c "import analisar_rompimento_10h as a; print('ORB import OK')"

# 2. Status do Git
git status --short
git log --oneline -3

# 3. Pipeline quick test
python main_pipeline.py

Saída saudável esperada:

Motor: 1.5 | stale: 15.0

V3.4.1: True

ORB import OK

Pipeline em ~3-9s com PIPELINE V2 CONCLUÍDO COM SUCESSO

PARTE 7 — HISTÓRICO DE SESSÕES
Sessão 2026-10-22/26 (esta)
Validação Fase A (R:R 1.5 + Pepita em produção) ✅

Fase B (regressão) ✅ — 19/19

Fase C (Trilha C v2) ✅ — Pepita original era overfit; COMBO v3.3 é o ouro

D1 (guard stale) ✅

Coletor v2.9 + Calculadora fix + Novo Motor YAML ✅

Spike Vision Expert v5.2 (SMC puro + R:R validado no Python) ✅

Spike Desk v2.7.3 (híbrido + direto estrito + anti-rate-limit) ✅

Fase 1 faxina ✅

Fase 2 blindagem: Motor (✅) + analisar_rompimento (✅); cache_candles ⏳

Descobertas críticas (não perder)
Pepita pura era overfit: −6.9 pts/trade fora da amostra. O que sustenta é COMBO R:R 1.5 + Pepita.

Coletor cego ao pré-market durante a sessão inicial — corrigido com _coletar_tv_adr priorizando POST > PRE > REGULAR com base no horário BRT.

MAX_GAP_REALISTA estava em 1000 — perdia o gap de −31k da eleição. Ajustado para 50000 no YAML.

VisionService adivinhava por padrão de tendência. Corrigido para ler AnaliseGraficaSMC_Regras.json direto.

Modo Direto vazio com max_tokens=512 — modelo gasta tudo "pensando". Corrigido para 1024.

except: pass escondeu dados reais durante o gap da eleição — daí a Fase 2.

PARTE 8 — COMANDOS ÚTEIS
# Rodar pipeline completo
python main_pipeline.py

# Validar SMC e orquestrador
python v2_rodar_decisao_completa.py

# Gerar snapshot ORB manualmente
python analisar_rompimento_10h.py --force --abrir

# Limpar cache Python antes de testes
Get-ChildItem -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Commit de checkpoint
git add .
git commit -m "checkpoint: <descrição>"
git push origin main


Para qualquer chat novo: cole o bloco da PARTE 5 como primeira mensagem.
Para troubleshooting: PARTE 6.
Para entender uma decisão antiga: PARTE 7.


---

## 🎯 Como usar daqui pra frente

**1. Salve o arquivo** como `PLAYBOOK_SPIKE.md` na raiz do projeto.

**2. Faça o commit:**
```powershell
git add PLAYBOOK_SPIKE.md
git commit -m "docs: PLAYBOOK_SPIKE consolidado (Fases A/B/C/D1 + Fase 2 em andamento)"
git push origin main

3. No chat novo, cole apenas o bloco da Parte 5 (CONTEXTO DE RETOMADA). É o suficiente.

4. Sempre que terminar uma sessão, atualize a Parte 2 (status) e a Parte 7 (histórico) com o que mudou.