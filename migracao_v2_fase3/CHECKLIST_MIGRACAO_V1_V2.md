# CHECKLIST DE MIGRAÇÃO V1 → V2
**Projeto:** Analisador Financeiro  
**Base:** Auditoria de duplicidade (27/08/2026) + Roadmap v1.0 + dump real do código  
**Objetivo:** Eliminar duplicidade crítica, unificar decisão e descontinuar Engine_Vies de forma controlada.  
**Última atualização de status:** 27/08/2026 (após análise do código real)

---

## Legenda de status
- [ ] Pendente
- [x] Concluído
- [~] Em andamento / parcial
- ⚠ Bloqueante para a próxima fase

---

## FASE 0 — Preparação (pré-requisitos)

| # | Item | Roadmap | Status | Notas |
|---|------|---------|--------|-------|
| 0.1 | Backup completo do projeto + pasta `Coletas/` | — | [ ] | Executar no ambiente local antes de novos commits |
| 0.2 | Branch `feature/migracao-v2` criada | — | [ ] | Trabalho isolado do main |
| 0.3 | Documentar decisão oficial: **fonte da verdade de previsão** | A1 | [x] | 27/08/2026 — ver `DECISOES.md` |
| 0.4 | Congelar novas features em V1 (exceto correções críticas) | — | [~] | Decisão tomada; comunicar no time |

---

## FASE 1 — Centralizar configuração (A2)

| # | Item | Roadmap | Status | Notas |
|---|------|---------|--------|-------|
| 1.1 | Expandir `config.py` com caminhos (`BASE_DIR`, `COLETAS_DIR`, nomes de JSON) | A2 | [x] | 27/08/2026 — `config.py` completo |
| 1.2 | Centralizar listas de tickers (TradingView, Finnhub, MT5 B3, ADRs) | A2 | [x] | Em `config.py` |
| 1.3 | Centralizar pesos da estimativa de abertura (EWZ, ADRs, SPX, commodities) | A2 | [x] | + pesos NOVO_MOTOR + limiares gap/score |
| 1.4 | Centralizar parâmetros de pipeline (timeouts, janela de ajuste 19:00–08:50) | A2 | [x] | `JANELA_AJUSTE_*`, timeouts HTTP |
| 1.5 | Substituir hardcoding nos módulos críticos por imports de `config` | A2 | [~] | **Coletor.py** migrado; Calculadora / Analise_Noticias / etc. ainda locais |
| 1.6 | Validar que pipeline e V2 ainda rodam após a centralização | A2 | [~] | Smoke test no ambiente com MT5/.env |

**Critério de saída da Fase 1:** nenhum caminho/ticker/peso crítico hardcoded nos módulos principais.  
**Arquivos desta fase:** `config.py`, `Coletor.py` (exemplo).

---

## FASE 2 — Unificar decisão (eliminar dualidade crítica)

| # | Item | Roadmap | Status | Notas |
|---|------|---------|--------|-------|
| 2.1 | Definir hierarquia oficial: **NOVO_MOTOR → OpeningScenario → Confluence/Decision** | A1 | [x] | Documentado em `DECISOES.md` e `config.FONTE_OFICIAL_PREVISAO` |
| 2.2 | Remover fallback `Engine_Vies` do `PredictionService` (ou marcar deprecated) | A1 | [x] | `ENGINE_VIES_COMO_FALLBACK = False`; serviço retorna NEUTRO se motor falhar |
| 2.3 | Garantir que `v2_orchestrator` sempre grava `Decisao_V2.json` completo | A1 | [x] | Confirmado no código |
| 2.4 | No `main_pipeline`: tornar etapa V2 a **única** geradora de decisão ativa | A3 | [x] | Etapa Engine_Vies **comentada**; etapas 10–11 são V2 |
| 2.5 | Criar flag/config `USAR_DECISAO_V2 = True` | A1 | [x] | Presente em `config.py` |
| 2.6 | Atualizar comparador V1×V2 para deixar claro que V2 é a referência | U* | [x] | `v2/pages/1.2_comparador.py` já avisa descontinuação da V1 |
| 2.7 | Documentar no `mapeamento_campos_v2.md` a fonte oficial de cada campo de decisão | Do* | [~] | Mapeamento existe; falta seção explícita “fonte oficial = V2” |

**Critério de saída da Fase 2:** uma única decisão persistida como “oficial” (`Decisao_V2.json`); Engine_Vies não alimenta mais o fluxo ativo. → **ATINGIDO no backend**

---

## FASE 3 — Migrar interface (páginas)

| # | Item | Roadmap | Status | Notas |
|---|------|---------|--------|-------|
| 3.1 | `pages/5.3_Core_Engine.py` → consumir `Decisao_V2` | A1 | [x] | Já na versão 2.0 (27/08/2026); prioriza Decisao_V2.json |
| 3.2 | `pages/1.2` e `1.3` (NOVO_MOTOR) → alinhar com OpeningScenario / Decisao_V2 | A1 | [ ] | Evitar 3 “verdades” na UI |
| 3.3 | `pages/2.0_Previsao_Abertura_WINFUT` → usar apenas contratos V2 | A1 | [ ] | |
| 3.4 | Dividir `1.1_Setup_Abertura` em sub-abas (Ajuste B3, 09:00, 10:00) | U1 | [ ] | Ganho rápido de UX |
| 3.5 | Unificar ou arquivar páginas duplicadas de decisão | U* | [~] | Menu ainda lista `pages/` + `v2/pages/` automaticamente |
| 3.6 | Garantir que `v2/pages/` sejam as telas oficiais de decisão | A1 | [~] | Dashboard/comparador/análise V2 ok; menu a organizar |

**Critério de saída da Fase 3:** usuário vê uma única decisão principal na UI; páginas legadas de viés marcadas como “legado” ou removidas do menu.

---

## FASE 4 — Descontinuar Engine_Vies e limpar V1 de decisão

| # | Item | Roadmap | Status | Notas |
|---|------|---------|--------|-------|
| 4.1 | Remover etapa Engine_Vies do `main_pipeline` (ou tornar no-op) | A1 | [x] | Já comentada |
| 4.2 | Manter `Engine_Vies.py` apenas para leitura histórica / rollback | A1 | [x] | Arquivo preservado |
| 4.3 | Remover imports ativos de `Engine_Vies` de páginas e services | A1 | [~] | PredictionService ainda importa (protegido pela flag) |
| 4.4 | Atualizar `Gerar_Mapa_Fluxo` / inventário técnico | Do* | [ ] | |
| 4.5 | Comunicar no README / guia: “Decisão oficial = V2” | Do1 | [~] | Ver seção em README + `DECISOES.md` |

**Critério de saída da Fase 4:** Engine_Vies fora do pipeline operacional; zero referências ativas no fluxo de produção.

---

## FASE 5 — Orquestrador unificado e resiliência

| # | Item | Roadmap | Status | Notas |
|---|------|---------|--------|-------|
| 5.1 | Evoluir `v2_orchestrator` para class com estados | A3 | [~] | Classe `V2Orchestrator` já existe; estados ainda simples |
| 5.2 | Opcional: etapas de coleta invocáveis pelo orquestrador V2 | A3 | [ ] | Médio esforço |
| 5.3 | Fallback MT5 (Yahoo / cache / estático) | C1 | [ ] | |
| 5.4 | Monitoramento de qualidade de dados | C2 | [ ] | |
| 5.5 | Cache em memória para leituras repetidas de JSON | D2 | [~] | Streamlit `@st.cache_data` em algumas páginas |

---

## FASE 6 — Persistência e testes

| # | Item | Roadmap | Status | Notas |
|---|------|---------|--------|-------|
| 6.1 | Avaliar migração de histórico para SQLite | D1 | [ ] | Após unificação da decisão |
| 6.2 | Testes unitários (Calculadora, OpeningScenario, DecisionEngine…) | T1 | [ ] | |
| 6.3 | Testes de integração do pipeline com mocks | T2 | [ ] | |
| 6.4 | Expandir `v2/tests/` além de `test_contracts.py` | T1 | [ ] | |

---

## FASE 7 — Documentação e fechamento

| # | Item | Roadmap | Status | Notas |
|---|------|---------|--------|-------|
| 7.1 | Guia de instalação / variáveis de ambiente / dependências | Do1 | [ ] | |
| 7.2 | Docstrings nos módulos principais | Do2 | [ ] | |
| 7.3 | Diagrama de fluxo atualizado (→ Decisao_V2) | Do3 | [ ] | |
| 7.4 | Atualizar este checklist e o Roadmap com datas reais | — | [x] | 27/08/2026 |
| 7.5 | Tag de release `v2.0-migracao-completa` | — | [ ] | |

---

## Ordem mínima recomendada (caminho crítico) — atualizado

```
Fase 0 formal (0.1–0.2 local)  →  Fase 2 (já concluída no backend)
→ Fase 3 (páginas + menu)  →  Fase 4 limpeza residual
→ depois C1/C2/D2 conforme necessidade
→ D1 e Testes quando a UI estiver unificada
```

---

## Critérios de “migração concluída”

- [x] Existe **uma** decisão oficial persistida (`Decisao_V2.json`)
- [x] `Engine_Vies` não participa do pipeline nem do PredictionService (flag off)
- [~] Páginas principais de abertura/decisão consomem apenas contratos V2
- [x] `config.py` é a fonte de caminhos, tickers, pesos e flags críticos
- [ ] Pipeline e Agendador estáveis em produção (validar no ambiente real)
- [~] Documentação e mapa de fluxo refletem o estado real

---

## Registro de decisões

| Data | Decisão | Responsável |
|------|---------|-------------|
| 27/08/2026 | Fonte oficial de previsão: NOVO_MOTOR + OpeningScenario | Migração V2 |
| 27/08/2026 | Engine_Vies desligado do pipeline (etapa comentada) | Migração V2 |
| | Release v2.0 em: _______________ | |

---

*Documento atualizado a partir da auditoria de duplicidade + dump do código — 27/08/2026.*
