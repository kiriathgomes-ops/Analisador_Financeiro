# -*- coding: utf-8 -*-
"""
audit_camada2.py - Auditoria dos JSONs de calculo (Camada 2)

Le os JSONs produzidos por:
  - Calculadora.py
  - CalculadoraEstimativaAbertura.py
  - Motor_SMC_Regras.py + Rodar_SMC_Regras.py
  - Gerar_Resultado_Operacional_Abertura.py
  - v2_orchestrator (Decisao_V2.json)

Faz sanity check:
  - Valores dentro de faixas plausiveis
  - Campos None em posicoes criticas
  - Coerencia entre JSONs (ex: pivots ordenados)
  - Presenca de campos novos (confluencia do fix57)

Uso:
    python audit_camada2.py
"""

import json
from datetime import datetime
from pathlib import Path

COLETAS = Path("Coletas")


def _load(nome):
    p = COLETAS / nome
    if not p.exists():
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print(f"  [ERRO] {nome}: {e}")
        return None


def _fmt_ts(ts):
    if not ts:
        return "?"
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        idade = (datetime.now().astimezone() - dt).total_seconds() / 60
        return f"{str(ts)[:19]} ({idade:.1f}min)"
    except Exception:
        return str(ts)[:19]


# ============================================================
# 2.A - Metricas_Calculadas.json
# ============================================================
def audit_metricas():
    print("=" * 70)
    print(" 2.A - Metricas_Calculadas.json")
    print("=" * 70)
    d = _load("Metricas_Calculadas.json")
    if not d:
        print("  [AUSENTE]")
        return

    meta = d.get("metadata_calculo", {})
    print(f"  Timestamp: {_fmt_ts(meta.get('timestamp'))}")
    print(f"  Total ativos processados: {meta.get('total_ativos_processados')}")
    print()

    cambio = d.get("cambio_e_arbitragem", {})
    print(f"  Spread WDO vs PTAX: {cambio.get('spread_wdo_ptax_pontos')} pts "
          f"({cambio.get('spread_wdo_ptax_percentual')}%)")

    curva = d.get("curva_juros_b3", {})
    print(f"  DI1 2027: {curva.get('di1_2027_taxa')}")
    print(f"  DI1 2029: {curva.get('di1_2029_taxa')}")
    inclin = curva.get("inclinacao_29_27_bps")
    print(f"  Inclinacao 29-27: {inclin} bps")
    if inclin is not None and (inclin < -100 or inclin > 300):
        print(f"     [ALERTA] inclinacao fora do plausivel")

    ind = d.get("indicadores_compostos", {})
    ext = ind.get("indicador_mercado_externo")
    adrs = ind.get("indicador_adrs_brasileiras")
    print()
    print(f"  Ind. Mercado Externo: {ext}")
    print(f"  Ind. ADRs Brasileiras: {adrs}")
    if ext is None:
        print(f"     [ALERTA] indicador externo e None")
    if adrs is None:
        print(f"     [ALERTA] indicador ADRs e None")


# ============================================================
# 2.B - EstimativaAbertura.json
# ============================================================
def audit_estimativa():
    print()
    print("=" * 70)
    print(" 2.B - EstimativaAbertura.json")
    print("=" * 70)
    d = _load("EstimativaAbertura.json")
    if not d:
        print("  [AUSENTE]")
        return

    est = (d.get("estimativa_abertura") or {}).get("WIN_INDICE") or {}
    if not est:
        print("  [VAZIO] estimativa_abertura.WIN_INDICE ausente")
        return

    at = est.get("abertura_teorica_pontos")
    var = est.get("variacao_teorica_pct")
    base = est.get("preco_referencia_base")
    print(f"  Abertura teorica: {at} pts")
    print(f"  Variacao teorica: {var}%")
    print(f"  Base referencia: {base}")

    coc = est.get("cost_of_carry", {})
    print(f"  Cost of carry (preco carregado): {coc.get('preco_teorico_carregado')}")

    if at and base:
        if abs(at - base) > 5000:
            print(f"     [ALERTA] divergencia abertura vs base > 5000 pts")

    piv = (d.get("pivot_points") or {}).get("WIN_FUT") or {}
    if piv:
        pp = piv.get("PP")
        r1 = piv.get("R1")
        r2 = piv.get("R2")
        s1 = piv.get("S1")
        s2 = piv.get("S2")
        print()
        print(f"  Pivots: R2={r2} R1={r1} PP={pp} S1={s1} S2={s2}")
        # Validacao: R2 > R1 > PP > S1 > S2
        erros = []
        if r2 and r1 and r2 <= r1: erros.append("R2 <= R1")
        if r1 and pp and r1 <= pp: erros.append("R1 <= PP")
        if pp and s1 and pp <= s1: erros.append("PP <= S1")
        if s1 and s2 and s1 <= s2: erros.append("S1 <= S2")
        if erros:
            print(f"     [ALERTA] pivots desordenados: {', '.join(erros)}")
        else:
            print(f"     [OK] pivots ordenados")


# ============================================================
# 2.C - SMC (M5 + M1 + M15 + MTF)
# ============================================================
def audit_smc():
    print()
    print("=" * 70)
    print(" 2.C - AnaliseGraficaSMC_Regras (M5 + M1 + M15 + MTF)")
    print("=" * 70)

    for nome, label in [
        ("AnaliseGraficaSMC_Regras.json", "M5"),
        ("AnaliseGraficaSMC_Regras_M1.json", "M1"),
        ("AnaliseGraficaSMC_Regras_M15.json", "M15"),
    ]:
        d = _load(nome)
        if not d:
            print(f"  [{label}] AUSENTE")
            continue
        bias = d.get("bias_direcional")
        conf = d.get("confianca_visual")
        n_obs = len(d.get("order_blocks") or [])
        n_fvgs = len(d.get("fair_value_gaps") or [])
        n_swings = d.get("metadados", {}).get("n_swings", 0)
        ts = d.get("timestamp")
        print(f"  [{label}] bias={bias} conf={conf}% OBs={n_obs} FVGs={n_fvgs} "
              f"swings={n_swings} ts={_fmt_ts(ts)}")

    # MTF
    mtf = _load("AnaliseGraficaSMC_MTF.json")
    if mtf:
        conf = mtf.get("confluencia", {})
        print()
        print(f"  [MTF] veredito={conf.get('veredito_mtf')} "
              f"alinh={conf.get('alinhamento')} "
              f"dir_dom={conf.get('direcao_dominante')} "
              f"conf_pond={conf.get('confianca_ponderada')}")


# ============================================================
# 2.D - Resultado_Calculadora_Operacional_Abertura.json
# ============================================================
def audit_resultado():
    print()
    print("=" * 70)
    print(" 2.D - Resultado_Calculadora_Operacional_Abertura.json")
    print("=" * 70)
    d = _load("Resultado_Calculadora_Operacional_Abertura.json")
    if not d:
        print("  [AUSENTE]")
        return

    # Estrutura desconhecida - vamos explorar
    print(f"  Chaves root: {list(d.keys())}")
    for k, v in d.items():
        if isinstance(v, dict):
            print(f"    {k}: dict com {len(v)} chaves -> {list(v.keys())[:8]}")


# ============================================================
# 2.E - Decisao_V2.json
# ============================================================
def audit_decisao():
    print()
    print("=" * 70)
    print(" 2.E - Decisao_V2.json")
    print("=" * 70)
    d = _load("Decisao_V2.json")
    if not d:
        print("  [AUSENTE]")
        return

    meta = d.get("metadata", {})
    dec = d.get("decisao", {})
    print(f"  Versao: {meta.get('versao')}")
    print(f"  Latencia: {meta.get('latencia_ms')} ms")
    print(f"  Vies final: {dec.get('vies_final')}")
    print(f"  Confianca: {dec.get('confianca')}")
    print(f"  Entrada: {dec.get('entrada')}")
    print(f"  Stop: {dec.get('stop_loss')}")

    # Bloco confluencia (fix57)
    md = dec.get("metadados", {})
    conf_blk = md.get("confluencia", {})
    print()
    if conf_blk:
        print("  [confluencia - fix57]:")
        for k in ["smc_conf_bruto", "mtf_veredito", "mtf_delta",
                  "smc_conf_ajustado", "nm_conf", "peso_smc", "peso_nm",
                  "score_magnitude", "score_direcao",  # fix75: canonicos
                  "confianca_final", "passou_gate_confluencia",
                  "passou_gate_final"]:
            print(f"    {k}: {conf_blk.get(k)}")
    else:
        print("  [ALERTA] bloco confluencia ausente (fix57 nao gravou)")


# ============================================================
# MAIN
# ============================================================
def main():
    print()
    print("#" * 70)
    print("# AUDITORIA - CAMADA 2 (Calculo)")
    print(f"# Executado em: {datetime.now().isoformat(timespec='seconds')}")
    print("#" * 70)
    print()

    audit_metricas()
    audit_estimativa()
    audit_smc()
    audit_resultado()
    audit_decisao()

    print()
    print("=" * 70)
    print(" FIM DA AUDITORIA CAMADA 2")
    print("=" * 70)


if __name__ == "__main__":
    main()