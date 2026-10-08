# -*- coding: utf-8 -*-
# ver_componentes_hoje.py — Mostra contribuicao por componente do score NM AGORA.
#
# Usa a API publica executar_previsao() — nao depende de fix algum.

from NOVO_MOTOR_PREVISAO_ABERTURA.core.motor_previsao import executar_previsao

r = executar_previsao()
if not r:
    print("ERRO: executar_previsao retornou None")
    raise SystemExit(1)

score = r.get("score", {}) or {}
print(f"Score total: {score.get('valor')} ({score.get('classificacao')})")
print(f"Direcao:     {score.get('direcao')}")
print()
print("Contribuicao por componente:")
det = score.get("detalhes", {}) or {}
if not det:
    print("  (vazio)")
for k, v in sorted(det.items(), key=lambda x: x[1]):
    sinal = "+" if v >= 0 else ""
    print(f"  {k:<25} {sinal}{v:>8.2f}")