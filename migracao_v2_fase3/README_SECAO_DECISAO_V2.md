## Decisão oficial (V2)

A partir de **27/08/2026**, a decisão operacional do Analisador Financeiro é **exclusivamente V2**.

| Item | Valor |
|------|--------|
| Fonte de previsão | `NOVO_MOTOR` + `OpeningScenario` |
| Decisão persistida | `Coletas/Decisao_V2.json` |
| Orquestrador | `v2/core/engines/v2_orchestrator.py` |
| Flags | `USAR_DECISAO_V2 = True` · `ENGINE_VIES_COMO_FALLBACK = False` |

### O que mudou

- A etapa **Engine de Viés Institucional** foi removida do `main_pipeline` (comentada).
- O `PredictionService` usa apenas o NOVO_MOTOR; se falhar, devolve contexto NEUTRO (não reativa o legado).
- Telas oficiais de decisão: `v2/pages/` (dashboard, comparador, análise) e `pages/5.3_Core_Engine` (já em V2).

### Legado

- `Engine_Vies.py` e `Decisao_Core.json` permanecem apenas para **leitura histórica** e eventual rollback.
- Páginas antigas de previsão/viés na pasta `pages/` devem ser tratadas como **LEGADO** até unificação de UX.

Detalhes: ver `DECISOES.md` e `CHECKLIST_MIGRACAO_V1_V2.md`.
