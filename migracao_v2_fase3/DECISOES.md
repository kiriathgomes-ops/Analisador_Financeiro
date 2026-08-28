# Decisões oficiais — Migração V1 → V2

**Projeto:** Analisador Financeiro  
**Data da decisão:** 27/08/2026  
**Status:** Vigente

---

## 1. Fonte oficial de previsão e decisão

| Papel | Componente | Arquivo / artefato |
|-------|------------|--------------------|
| **Fonte oficial de previsão** | NOVO_MOTOR + OpeningScenario | `NOVO_MOTOR_PREVISAO_ABERTURA/` + `v2/core/engines/opening_scenario_engine.py` |
| **Decisão oficial persistida** | V2 Orchestrator → DecisionEngine | `Coletas/Decisao_V2.json` |
| **Hierarquia** | 1. NOVO_MOTOR → 2. OpeningScenario → 3. Confluence → 4. DecisionEngine | — |
| **Legado (somente leitura)** | Engine_Vies | `Engine_Vies.py` + `Coletas/Decisao_Core.json` |

### Flags em `config.py`

```python
USAR_DECISAO_V2 = True
ENGINE_VIES_COMO_FALLBACK = False
FONTE_OFICIAL_PREVISAO = "NOVO_MOTOR+OpeningScenario"
```

- Páginas e serviços devem preferir `Decisao_V2.json`.
- `PredictionService` **não** chama mais `Engine_Vies` enquanto `ENGINE_VIES_COMO_FALLBACK` for `False`.
- Em caso de falha do NOVO_MOTOR, retorna contexto NEUTRO (não reativa o legado).

---

## 2. Pipeline operacional

A etapa `"8 - ENGINE DE VIES INSTITUCIONAL"` está **comentada** em `main_pipeline.py`.

Ordem atual das etapas relevantes de decisão:

1. Coleta / validação / métricas / estimativa  
2. SMC regras  
3. Relatório  
4. **`v2_gravar_sessao_win.py`**  
5. **`v2_rodar_decisao_completa.py`** → grava `Decisao_V2.json`

Engine_Vies permanece no repositório apenas para:

- leitura histórica / auditoria  
- rollback emergencial (reativar flag + etapa, se necessário)

---

## 3. Interface (UI)

| Tela | Status | Observação |
|------|--------|------------|
| `v2/pages/1.1_dashboard_v2.py` | Oficial | Dashboard principal de decisão |
| `v2/pages/1.2_comparador.py` | Oficial | Compara V1×V2; avisa que V1 está descontinuada |
| `v2/pages/1.3_analise_detalhada.py` | Oficial | Detalhamento da decisão V2 |
| `pages/5.3_⚙️_Core_Engine.py` | Oficial (V2) | Já consome `Decisao_V2.json` (versão 2.0) |
| Páginas 1.2 / 1.3 / 2.0 (pasta `pages/`) | Legado | Manter no menu com banner “LEGADO” até unificação UX |

**Regra:** o usuário deve ver **uma** decisão principal (V2). Páginas legadas de viés devem ser marcadas ou arquivadas.

---

## 4. Critérios de “migração de decisão concluída”

- [x] Uma decisão oficial persistida (`Decisao_V2.json`)
- [x] Engine_Vies fora do pipeline operacional
- [x] PredictionService sem fallback ativo para Engine_Vies
- [x] `config.py` com flags de migração
- [~] Páginas principais consumindo apenas contratos V2 (5.3 e v2/pages ok; restante em andamento)
- [ ] Documentação e mapa de fluxo 100% alinhados (este documento + checklist atualizado)

---

## 5. Registro

| Data | Decisão | Responsável |
|------|---------|-------------|
| 27/08/2026 | Fonte oficial = NOVO_MOTOR + OpeningScenario; decisão = Decisao_V2.json | Migração V2 |
| 27/08/2026 | ENGINE_VIES_COMO_FALLBACK = False | Migração V2 |
| 27/08/2026 | Etapa Engine_Vies removida do main_pipeline (comentada) | Migração V2 |
| — | Release v2.0-migracao-completa | Pendente |

---

*Documento gerado na Fase 0 da migração V1 → V2 — 27/08/2026.*
