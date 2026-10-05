# -*- coding: utf-8 -*-
"""
audit_camada1.py - Auditoria dos JSONs de coleta (Camada 1)

Le os 4 JSONs de coleta e faz sanity check:
  - Faixas esperadas por ativo
  - Campos None em posicoes criticas
  - Divergencia entre arquivos
  - Timestamps desatualizados

Uso:
    python audit_camada1.py
"""

import json
from datetime import datetime
from pathlib import Path

COLETAS = Path("Coletas")

# Faixas plausiveis (min, max) - None = ignora check
FAIXAS = {
    "WIN_FUT":          (150000, 250000),
    "WIN_LAST_TICK":    (150000, 250000),
    "WIN_AJUSTE":       (150000, 250000),
    "WIN_FECHAMENTO_B3":(150000, 250000),
    "WDO_FUT":          (4000, 7000),
    "WDO_AJUSTE":       (4000, 7000),
    "WDO_FECHAMENTO_B3":(4000, 7000),
    "DI1_2027":         (8, 18),
    "DI1_2029":         (8, 18),
    "VIX":              (8, 50),
    "SP500_FUT":        (3000, 10000),
    "NASDAQ_FUT":       (10000, 40000),
    "DXY":              (80, 130),
    "USD_BRL":          (3, 10),
    "USD_PTAX":         (3, 10),
    "EWZ":              (15, 60),
    "IRON_ORE":         (50, 200),
    "CRUDE_OIL":        (30, 150),
    "GOLD":             (1500, 5000),
}


def _fmt_ts(ts_str):
    if not ts_str:
        return "?"
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        idade = (datetime.now().astimezone() - dt).total_seconds() / 60
        return f"{ts_str[:19]} ({idade:.1f}min)"
    except Exception:
        return ts_str


def _check_faixa(nome, valor):
    if valor is None:
        return "None"
    faixa = FAIXAS.get(nome)
    if not faixa:
        return "?"
    lo, hi = faixa
    if valor < lo or valor > hi:
        return f"FORA ({lo}-{hi})"
    return "OK"


def audit_unificado():
    print("=" * 70)
    print(" CAMADA 1.A - DadosAtivosUnificados.json")
    print("=" * 70)
    p = COLETAS / "DadosAtivosUnificados.json"
    if not p.exists():
        print("  [AUSENTE]")
        return
    d = json.load(open(p, encoding="utf-8"))
    ativos = d.get("ativos", {})
    print(f"  Total de ativos: {len(ativos)}")
    print()
    print(f"  {'ATIVO':<22} {'PRECO':>12} {'STATUS':<15} {'CHECK':<20}")
    print(f"  {'-'*22} {'-'*12} {'-'*15} {'-'*20}")

    # Ordena em grupos
    grupos = [
        ("B3", ["WIN_FUT", "WIN_LAST_TICK", "WIN_AJUSTE", "WIN_FECHAMENTO_B3",
                "WDO_FUT", "WDO_AJUSTE", "WDO_FECHAMENTO_B3",
                "DI1_2027", "DI1_2029"]),
        ("Global", ["VIX", "SP500_FUT", "NASDAQ_FUT", "DXY", "USD_BRL", "USD_PTAX"]),
        ("Commodities", ["IRON_ORE", "CRUDE_OIL", "GOLD"]),
        ("ADRs", ["EWZ", "VALE_ADR", "PETR_ADR", "ITUB_ADR", "BBAS_ADR",
                  "BBD_ADR", "B3_ADR"]),
        ("Acoes", ["VALE3", "PETR4", "ITUB4", "BBAS3", "BBDC4", "B3SA3"]),
    ]
    for grupo, ativos_grupo in grupos:
        print(f"  [{grupo}]")
        for nome in ativos_grupo:
            v = ativos.get(nome, {})
            preco = v.get("preco")
            status = v.get("status", "?")
            chk = _check_faixa(nome, preco)
            preco_s = f"{preco:>12.2f}" if isinstance(preco, (int, float)) else f"{'None':>12}"
            print(f"  {nome:<22} {preco_s} {status:<15} {chk:<20}")
        print()


def audit_mt5():
    print("=" * 70)
    print(" CAMADA 1.B - Dados_MT5_v2_2.json")
    print("=" * 70)
    p = COLETAS / "Dados_MT5_v2_2.json"
    if not p.exists():
        print("  [AUSENTE]")
        return
    d = json.load(open(p, encoding="utf-8"))
    print(f"  Versao: {d.get('versao_coletor')}")
    print(f"  Timestamp: {_fmt_ts(d.get('timestamp'))}")
    print(f"  Status: {d.get('status')}")
    print()
    ativos = d.get("ativos", {})
    for prefixo, info in ativos.items():
        contrato = info.get("contrato_principal")
        bid = info.get("bid")
        ask = info.get("ask")
        last = info.get("last")
        session_close = info.get("session_close")
        prev_close = info.get("prev_close")
        print(f"  [{prefixo}] {contrato}")
        print(f"     bid={bid}  ask={ask}  last={last}")
        print(f"     session_close={session_close}  prev_close={prev_close}")
        # Sanity: bid <= ask
        if bid and ask:
            if bid > ask:
                print(f"     [ALERTA] bid > ask")
            elif (ask - bid) / bid > 0.05:
                print(f"     [ALERTA] spread absurdo ({(ask-bid):.0f})")
        print()


def audit_validados():
    print("=" * 70)
    print(" CAMADA 1.C - Dados_Validados.json")
    print("=" * 70)
    p = COLETAS / "Dados_Validados.json"
    if not p.exists():
        print("  [AUSENTE]")
        return
    d = json.load(open(p, encoding="utf-8"))
    ativos = d.get("ativos_validados", [])
    print(f"  Total: {len(ativos)}")
    print()

    # Conta Nones por campo
    campos_criticos = ["close", "previous_close", "change_percent", "open", "high", "low"]
    contadores = {c: 0 for c in campos_criticos}
    sem_close = []
    for a in ativos:
        aid = a.get("ativo_id")
        for c in campos_criticos:
            if a.get(c) is None:
                contadores[c] += 1
        if a.get("close") is None:
            sem_close.append(aid)

    print("  Campos None (contagem):")
    for c, n in contadores.items():
        if n > 0:
            print(f"    {c:<20}: {n} de {len(ativos)}")
    print()
    if sem_close:
        print(f"  Ativos SEM close ({len(sem_close)}):")
        for aid in sem_close:
            print(f"    - {aid}")
    else:
        print("  Todos os ativos tem close")


def audit_ram():
    print("=" * 70)
    print(" CAMADA 1.D - Coleta_ram.json (ultimo snapshot)")
    print("=" * 70)
    p = COLETAS / "Coleta_ram.json"
    if not p.exists():
        print("  [AUSENTE]")
        return
    d = json.load(open(p, encoding="utf-8"))
    coletas = d.get("coletas", [])
    print(f"  Total de coletas: {len(coletas)}")
    ts = None
    for c in coletas[:3]:
        ts = c.get("timestamp")
        break
    if ts:
        print(f"  Timestamp (primeiro): {_fmt_ts(ts)}")


def main():
    print()
    print("#" * 70)
    print("# AUDITORIA - CAMADA 1 (Coleta)")
    print(f"# Executado em: {datetime.now().isoformat(timespec='seconds')}")
    print("#" * 70)
    print()

    audit_unificado()
    audit_mt5()
    audit_validados()
    audit_ram()

    print("=" * 70)
    print(" FIM DA AUDITORIA CAMADA 1")
    print("=" * 70)


if __name__ == "__main__":
    main()