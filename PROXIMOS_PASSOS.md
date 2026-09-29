# PROXIMOS PASSOS - Analisador_Financeiro

Data: 28/09/2026
Branch atual: main (sincronizada com origin)
Status: F2 + F3c concluidas e publicadas

## CONCLUIDO

- F2 - mapas de ticker centralizados no config.py -> mergeado e publicado.
- F3c - suite de contratos (8 testes) -> commit 8b1f383, publicado.
- Delecao da page 6.5 -> intencional (confirmado pelo Kiriath).
- Push -> main sincronizada com origin.

## F3 - PROXIMOS ALVOS DE REFACTOR (EM ABERTO)

| #   | Alvo                              | Descricao                                                        | Prioridade |
|-----|-----------------------------------|------------------------------------------------------------------|------------|
| F3a | Page 2 standalone                 | Centralizar caminhos (FILE_MT5_V2, FILE_UNIFICADO etc.) no config | alta       |
| F3b | ALIASES_BUSCA_ROM5 (page 4)       | Decidir se o mapa str -> list vai pro config.py                  | media      |
| F3d | MAPEAMENTO_ADR_B3 vs MAPA_B3_PARA_ADR | Revisar convivencia/nomenclatura dos dois mapas              | baixa      |

## SUITE DE TESTES

python -m v2.tests.test_contracts -v   # 8 testes (contratos dos mapas)

Obs: pytest nao instalado. Instalar se quiser: pip install pytest.

## BACKUPS

- _backup_fase2a/  -  _backup_fase2bc/  -  _backup_fase2d/
- git reflog para recuperar qualquer estado anterior.
