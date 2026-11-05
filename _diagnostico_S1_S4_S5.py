#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diagnostico_S1_S4_S5.py — Auditoria read-only das suspeitas pendentes

Read-only. Não modifica arquivos.
Único efeito: pode inicializar/fechar MT5 se ainda não estiver aberto
(para consultar symbol_info e copy_rates_from_pos). Use --skip-mt5 para evitar.

Uso:
    python diagnostico_S1_S4_S5.py
    python diagnostico_S1_S4_S5.py --skip-mt5
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
COLETAS = BASE_DIR / "Coletas"

FILE_MT5 = COLETAS / "Dados_MT5_v2_2.json"
FILE_SMC = COLETAS / "AnaliseGraficaSMC_Regras.json"
FILE_UNIF = COLETAS / "DadosAtivosUnificados.json"
FILE_VAL = COLETAS / "Dados_Validados.json"


def _safe_load(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  ❌ Erro lendo {path.name}: {e}")
        return None


def _fmt(v, suf="", casas=2):
    if v is None:
        return "—"
    try:
        return f"{float(v):,.{casas}f}{suf}"
    except (TypeError, ValueError):
        return str(v)


def _sep(titulo: str):
    print()
    print("═" * 78)
    print(f"  {titulo}")
    print("═" * 78)


# =============================================================================
# S1 — prev_close / session_close do WIN e WDO
# =============================================================================
def auditar_s1(skip_mt5: bool):
    _sep("S1 — prev_close / session_close de WIN e WDO")

    mt5_json = _safe_load(FILE_MT5)
    if mt5_json is None:
        print(f"  ⚠️ {FILE_MT5.name} não encontrado")
        return

    print(f"  Fonte: {FILE_MT5.name}")
    print(f"  Timestamp da coleta: {mt5_json.get('timestamp', '?')}")
    print()

    ativos = mt5_json.get("ativos", {})
    for prefixo in ("WIN", "WDO"):
        info = ativos.get(prefixo, {})
        if not info:
            print(f"  ⚠️ {prefixo}: sem dados no JSON")
            continue
        print(f"  ┌─ {prefixo} ({info.get('contrato_principal', '?')})")
        print(f"  │  session_close: {_fmt(info.get('session_close'), ' pts')}")
        print(f"  │  prev_close:    {_fmt(info.get('prev_close'), ' pts')}")
        print(f"  │  close (D1):    {_fmt(info.get('close'), ' pts')}")
        print(f"  │  last:          {_fmt(info.get('last'), ' pts')}")
        print(f"  │  open (D1):     {_fmt(info.get('open'), ' pts')}")
        print(f"  │  high (D1):     {_fmt(info.get('high'), ' pts')}")
        print(f"  │  low  (D1):     {_fmt(info.get('low'), ' pts')}")
        print(f"  │  change_pct:    {_fmt(info.get('change_percent'), '%', 4)}")
        print(f"  │  status:        {info.get('status')}")

        sc = info.get("session_close")
        last = info.get("last")
        if isinstance(sc, (int, float)) and isinstance(last, (int, float)) and sc > 0 and last > 0:
            var_sc = (last / sc - 1) * 100
            print(f"  │  → Last / session_close - 1 = {var_sc:+.4f}%")
            if abs(var_sc) > 5:
                print(f"  │  🚨 SUSPEITA: session_close inconsistente com last (var > 5%)")
        print(f"  └─")
        print()

    if skip_mt5:
        print("  (--skip-mt5: consulta fresca do MT5 pulada)")
        return

    print("  ── Consulta fresca do MT5 ──")
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("  ⚠️ MetaTrader5 não instalado")
        return

    own_init = False
    if mt5.terminal_info() is None:
        if not mt5.initialize():
            print(f"  ⚠️ mt5.initialize falhou: {mt5.last_error()}")
            return
        own_init = True

    try:
        for prefixo in ("WIN", "WDO"):
            info_json = ativos.get(prefixo, {})
            contrato = info_json.get("contrato_principal") or prefixo + "$"
            print()
            print(f"  {prefixo} — consulta em {contrato}")

            si = mt5.symbol_info(contrato)
            if si is None:
                print(f"    ⚠️ symbol_info({contrato}) retornou None")
                continue

            print(f"    session_close (fresh): {_fmt(getattr(si, 'session_close', None), ' pts')}")
            print(f"    basis (rollover?):     {getattr(si, 'basis', '?')}")
            exp = getattr(si, 'expiration_time', 0)
            if exp:
                try:
                    exp_dt = datetime.fromtimestamp(exp)
                    print(f"    expiration_time:       {exp_dt.isoformat()}")
                except Exception:
                    print(f"    expiration_time:       {exp} (raw)")

            rates = mt5.copy_rates_from_pos(contrato, mt5.TIMEFRAME_D1, 0, 5)
            if rates is not None and len(rates) > 0:
                print(f"    D1 últimos {len(rates)} candles:")
                for r in rates[-5:]:
                    try:
                        t = datetime.fromtimestamp(r["time"]).strftime("%Y-%m-%d")
                        print(f"      {t}  O:{r['open']:.0f}  H:{r['high']:.0f}  L:{r['low']:.0f}  C:{r['close']:.0f}")
                    except Exception as e:
                        print(f"      ⚠️ {e}")
    finally:
        if own_init:
            try:
                mt5.shutdown()
            except Exception:
                pass


# =============================================================================
# S4 — POC/VWAP vs preço atual
# =============================================================================
def auditar_s4():
    _sep("S4 — POC/VWAP em AnaliseGraficaSMC_Regras.json")

    smc = _safe_load(FILE_SMC)
    if smc is None:
        print(f"  ⚠️ {FILE_SMC.name} não encontrado")
        return

    print(f"  Fonte: {FILE_SMC.name}")
    print(f"  Timestamp: {smc.get('timestamp', '?')}")
    print(f"  bias_direcional: {smc.get('bias_direcional')}")
    print(f"  confianca_visual: {smc.get('confianca_visual')}")
    print(f"  preco_atual: {_fmt(smc.get('preco_atual'), ' pts')}")
    print(f"  stale: {smc.get('stale', False)}")
    print()

    niveis = smc.get("niveis_institucionais", {})
    poc = niveis.get("poc_ontem")
    vwap = niveis.get("vwap_ontem")
    preco = smc.get("preco_atual")

    print(f"  niveis_institucionais:")
    print(f"    poc_ontem:  {_fmt(poc, ' pts')}")
    print(f"    vwap_ontem: {_fmt(vwap, ' pts')}")
    print()

    unif = _safe_load(FILE_UNIF)
    last_tick = None
    ajuste = None
    if unif:
        ativos_u = unif.get("ativos", {})
        last_tick = (ativos_u.get("WIN_LAST_TICK") or {}).get("preco")
        ajuste = (ativos_u.get("WIN_AJUSTE") or {}).get("preco")
        fut = (ativos_u.get("WIN_FUT") or {}).get("preco")
        print(f"  Preço atual (DadosAtivosUnificados):")
        print(f"    WIN_AJUSTE:     {_fmt(ajuste, ' pts')}")
        print(f"    WIN_LAST_TICK:  {_fmt(last_tick, ' pts')}")
        print(f"    WIN_FUT:        {_fmt(fut, ' pts')}")
        print()

    ref_preco = preco if isinstance(preco, (int, float)) and preco > 0 else (last_tick or ajuste)
    if isinstance(poc, (int, float)) and isinstance(ref_preco, (int, float)) and ref_preco > 0:
        delta_poc = poc - ref_preco
        delta_pct = (delta_poc / ref_preco) * 100
        print(f"  Delta POC vs preço de referência:")
        print(f"    ref: {_fmt(ref_preco, ' pts')}")
        print(f"    Δ:   {delta_poc:+,.0f} pts ({delta_pct:+.2f}%)")
        if abs(delta_pct) > 5:
            print(f"  🚨 SUSPEITA: POC {delta_pct:+.2f}% distante do preço — de contrato anterior/rollover")
        else:
            print(f"  ✅ POC dentro de faixa razoável")


# =============================================================================
# S5 — WIN_AJUSTE: estrutura e presença de H/L
# =============================================================================
def auditar_s5():
    _sep("S5 — WIN_AJUSTE em DadosAtivosUnificados e Dados_Validados")

    unif = _safe_load(FILE_UNIF)
    if unif is None:
        print(f"  ⚠️ {FILE_UNIF.name} não encontrado")
        return

    ativos = unif.get("ativos", {})
    print(f"  Fonte: {FILE_UNIF.name}")
    print(f"  metadata: {unif.get('metadata', {})}")
    print()

    for chave in ("WIN_AJUSTE", "WIN_FECHAMENTO_B3", "WIN_LAST_TICK", "WIN_FUT"):
        item = ativos.get(chave)
        if not item:
            print(f"  ⚠️ {chave}: não presente")
            continue
        print(f"  {chave}:")
        for k in ("preco", "variacao_pct", "ticker_original", "status", "fonte", "timestamp_coleta"):
            print(f"    {k}: {item.get(k)!r}")
        print()

    val = _safe_load(FILE_VAL)
    if val is None:
        print(f"  ⚠️ {FILE_VAL.name} não encontrado")
        return

    print(f"  ── Dados_Validados.json ──")
    validados = val.get("ativos_validados", [])
    for ativo in validados:
        if ativo.get("ativo_id") == "WIN_AJUSTE":
            print(f"  WIN_AJUSTE em Dados_Validados:")
            for k, v in ativo.items():
                print(f"    {k}: {v!r}")
            print()
            o, h, l, c = ativo.get("open"), ativo.get("high"), ativo.get("low"), ativo.get("close")
            if c and not (o or h or l):
                print(f"  🚨 CONFIRMADO: close={c} populado, mas open/high/low ausentes")
                print(f"     → pivots clássicos não calculam (requer H>0 e L>0)")
            elif all(x is not None for x in (o, h, l, c)):
                print(f"  ✅ H/L presentes — pivots deveriam calcular")
            break


# =============================================================================
# MAIN
# =============================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-mt5", action="store_true", help="Não abre MT5 (só lê arquivos)")
    args = ap.parse_args()

    print("=" * 78)
    print("  AUDITORIA S1 / S4 / S5 — Read-only")
    print("=" * 78)
    print(f"  Iniciado em: {datetime.now().isoformat(timespec='seconds')}")
    print(f"  Raiz: {BASE_DIR}")

    auditar_s1(skip_mt5=args.skip_mt5)
    auditar_s4()
    auditar_s5()

    print()
    print("═" * 78)
    print("  FIM")
    print("═" * 78)


if __name__ == "__main__":
    main()