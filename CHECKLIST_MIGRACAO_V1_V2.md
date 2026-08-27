# CHECKLIST DE MIGRAÇÃO V1 → V2
**Projeto:** Analisador Financeiro  
**Base:** Auditoria de duplicidade (27/08/2026) + Roadmap v1.0  
**Objetivo:** Eliminar duplicidade crítica, unificar decisão e descontinuar Engine_Vies de forma controlada.

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
| 0.1 | Backup completo do projeto + pasta `Coletas/` | — | [ ] | Antes de qualquer alteração estrutural |
| 0.2 | Branch `feature/migracao-v2` criada | — | [ ] | Trabalho isolado do main |
| 0.3 | Documentar decisão oficial: **fonte da verdade de previsão** | A1 | [ ] | Sugerido: NOVO_MOTOR + OpeningScenario; Engine_Vies só leitura histórica |
| 0.4 | Congelar novas features em V1 (exceto correções críticas) | — | [ ] | Evitar aumentar a dívida |

---

## FASE 1 — Centralizar configuração (A2)

| # | Item | Roadmap | Status | Notas |
|---|------|---------|--------|-------|
| 1.1 | Expandir `config.py` com caminhos (`BASE_DIR`, `COLETAS_DIR`, nomes de JSON) | A2 | [ ] | ⚠ |
| 1.2 | Centralizar listas de tickers (TradingView, Finnhub, MT5 B3, ADRs) | A2 | [ ] | Hoje em `Coletor.py` |
| 1.3 | Centralizar pesos da estimativa de abertura (EWZ, ADRs, SPX, commodities) | A2 | [ ] | Alinhar com `NOVO_MOTOR/.../pesos.yaml` |
| 1.4 | Centralizar parâmetros de pipeline (timeouts, janela de ajuste 19:00–08:50) | A2 | [ ] | |
| 1.5 | Substituir hardcoding nos módulos críticos (`Coletor`, `Calculadora*`, `Engine_Vies`, services V2) por imports de `config` | A2 | [ ] | Incremental |
| 1.6 | Validar que pipeline e V2 ainda rodam após a centralização | A2 | [ ] | Smoke test |

**Critério de saída da Fase 1:** nenhum caminho/ticker/peso crítico hardcoded nos módulos principais.

---

## FASE 2 — Unificar decisão (eliminar dualidade crítica)

| # | Item | Roadmap | Status | Notas |
|---|------|---------|--------|-------|
| 2.1 | Definir hierarquia oficial: **NOVO_MOTOR → OpeningScenario → Confluence/Decision** | A1 | [ ] | ⚠ |
| 2.2 | Remover fallback `Engine_Vies` do `PredictionService` (ou marcar como deprecated com log) | A1 | [ ] | ⚠ |
| 2.3 | Garantir que `v2_orchestrator` sempre grava `Decisao_V2.json` completo | A1 | [ ] | |
| 2.4 | No `main_pipeline`: tornar etapa V2 a **única** geradora de decisão ativa | A3 | [ ] | Manter Engine_Vies só se necessário para compatibilidade temporária |
| 2.5 | Criar flag/config `USAR_DECISAO_V2 = True` (páginas leem V2 por padrão) | A1 | [ ] | |
| 2.6 | Atualizar comparador V1×V2 para deixar claro que V2 é a referência | U* | [ ] | |
| 2.7 | Documentar no `mapeamento_campos_v2.md` a fonte oficial de cada campo de decisão | Do* | [ ] | |

**Critério de saída da Fase 2:** uma única decisão persistida como “oficial” (`Decisao_V2.json`); Engine_Vies não alimenta mais o fluxo ativo.

---

## FASE 3 — Migrar interface (páginas)

| # | Item | Roadmap | Status | Notas |
|---|------|---------|--------|-------|
| 3.1 | `pages/5.3_Core_Engine.py` → consumir `Decisao_V2` (ou redirecionar para dashboard V2) | A1 | [ ] | |
| 3.2 | `pages/1.2` e `1.3` (NOVO_MOTOR) → alinhar exibição com OpeningScenario / Decisao_V2 | A1 | [ ] | Evitar 3 “verdades” na UI |
| 3.3 | `pages/2.0_Previsao_Abertura_WINFUT` → usar apenas contratos V2 | A1 | [ ] | |
| 3.4 | Dividir `1.1_Setup_Abertura` em sub-abas (Ajuste B3, 09:00, 10:00) | U1 | [ ] | Ganho rápido de UX |
| 3.5 | Unificar ou arquivar páginas duplicadas de decisão (manter 1 dashboard principal) | U* | [ ] | |
| 3.6 | Garantir que `v2/pages/` (dashboard, comparador, análise) sejam as telas oficiais de decisão | A1 | [ ] | |

**Critério de saída da Fase 3:** usuário vê uma única decisão principal na UI; páginas legadas de viés marcadas como “legado” ou removidas do menu.

---

## FASE 4 — Descontinuar Engine_Vies e limpar V1 de decisão

| # | Item | Roadmap | Status | Notas |
|---|------|---------|--------|-------|
| 4.1 | Remover etapa `"8 - ENGINE DE VIES INSTITUCIONAL"` do `main_pipeline` (ou tornar no-op) | A1 | [ ] | ⚠ após Fase 2 e 3 |
| 4.2 | Manter `Engine_Vies.py` apenas para leitura histórica / rollback por N ciclos | A1 | [ ] | Não deletar de imediato |
| 4.3 | Remover imports de `Engine_Vies` de páginas e services | A1 | [ ] | |
| 4.4 | Atualizar `Gerar_Mapa_Fluxo` / inventário técnico para refletir o novo fluxo | Do* | [ ] | |
| 4.5 | Comunicar no README / guia: “Decisão oficial = V2” | Do1 | [ ] | |

**Critério de saída da Fase 4:** `Engine_Vies` fora do pipeline operacional; zero referências ativas no código de produção.

---

## FASE 5 — Orquestrador unificado e resiliência

| # | Item | Roadmap | Status | Notas |
|---|------|---------|--------|-------|
| 5.1 | Evoluir `v2_orchestrator` para class com estados (coleta ok / métricas ok / decisão ok) | A3 | [ ] | |
| 5.2 | Opcional: mover etapas de coleta/cálculo para serem invocáveis pelo orquestrador V2 (sem subprocess cego) | A3 | [ ] | Médio esforço |
| 5.3 | Fallback MT5 (Yahoo / cache / estático) quando MT5 falhar | C1 | [ ] | |
| 5.4 | Monitoramento de qualidade de dados (preços fora de faixa, gaps absurdos) | C2 | [ ] | |
| 5.5 | Cache em memória para leituras repetidas de JSON | D2 | [ ] | |

---

## FASE 6 — Persistência e testes

| # | Item | Roadmap | Status | Notas |
|---|------|---------|--------|-------|
| 6.1 | Avaliar migração de histórico (preços, decisões, sessões) para SQLite | D1 | [ ] | Após unificação da decisão |
| 6.2 | Testes unitários: Calculadora, Validador, Motor_SMC_Regras, OpeningScenario, DecisionEngine | T1 | [ ] | |
| 6.3 | Testes de integração do pipeline com dados mockados | T2 | [ ] | Depende de D1/A1 |
| 6.4 | Expandir `v2/tests/` além de `test_contracts.py` | T1 | [ ] | |

---

## FASE 7 — Documentação e fechamento

| # | Item | Roadmap | Status | Notas |
|---|------|---------|--------|-------|
| 7.1 | Guia de instalação / variáveis de ambiente / dependências | Do1 | [ ] | |
| 7.2 | Docstrings nos módulos principais (formato Sphinx ou Google) | Do2 | [ ] | |
| 7.3 | Diagrama de fluxo atualizado (entradas → processamentos → Decisao_V2) | Do3 | [ ] | |
| 7.4 | Atualizar este checklist e o Roadmap com datas reais de conclusão | — | [ ] | |
| 7.5 | Tag de release `v2.0-migracao-completa` | — | [ ] | |

---

## Ordem mínima recomendada (caminho crítico)

```
0.1–0.3  →  Fase 1 (A2)  →  2.1–2.4  →  Fase 3 (páginas)  →  Fase 4 (desligar Vies)
         →  depois C1/C2/D2 conforme necessidade
         →  D1 e Testes quando a decisão já estiver unificada
```

---

## Critérios de “migração concluída”

- [ ] Existe **uma** decisão oficial persistida (`Decisao_V2.json`)
- [ ] `Engine_Vies` não participa do pipeline nem do PredictionService
- [ ] Páginas principais de abertura/decisão consomem apenas contratos V2
- [ ] `config.py` é a única fonte de caminhos, tickers e pesos críticos
- [ ] Pipeline e Agendador continuam estáveis em produção
- [ ] Documentação e mapa de fluxo refletem o estado real

---

## Registro de decisões (preencher durante a migração)

| Data | Decisão | Responsável |
|------|---------|-------------|
| | Fonte oficial de previsão: _______________ | |
| | Engine_Vies desligado do pipeline em: _______________ | |
| | Release v2.0 em: _______________ | |

---

*Documento gerado a partir da auditoria de duplicidade V1×V2 — 27/08/2026.*
