#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auditoria_geral_coletas.py — Mapeamento completo de tudo que o app coleta.
Lê os JSONs mais recentes e exibe um relatório unificado no terminal.
"""

import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
COLETAS = BASE_DIR / "Coletas"

def _load(path):
    if not path.exists(): return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro lendo {path.name}: {e}")
        return {}

def _fmt(val, sufixo=""):
    if val is None: return "—"
    try:
        return f"{float(val):,.2f}{sufixo}"
    except:
        return str(val)

def main():
    print("=" * 85)
    print(" 🕵️ AUDITORIA GERAL DAS COLETAS (Visão do Último Ciclo)")
    print("=" * 85)

    # 1. MT5 FUTUROS E DI1
    mt5 = _load(COLETAS / "Dados_MT5_v2_2.json")
    print(f"\n📌 1. MT5 (Futuros e DI1) — Fonte: MetaTrader 5")
    print(f"   Timestamp: {mt5.get('timestamp', '?')}")
    ativos_mt5 = mt5.get("ativos", {})
    
    for k in ["WIN", "WDO", "DI1"]:
        a = ativos_mt5.get(k, {})
        if not a:
            print(f"   ❌ {k:<5} | Não coletado")
            continue
        print(f"   ✅ {k:<5} | Contrato: {a.get('contrato_principal'):<8} | Last: {_fmt(a.get('last')):>10} | D1 Close: {_fmt(a.get('close')):>10}")

    # 2. APIS (TradingView, BRAPI, BACEN, Finnhub)
    rom0 = _load(COLETAS / "Coleta_rom-0.json")
    coletas_brutas = rom0.get("coletas", [])
    print(f"\n📌 2. APIs (TradingView, BRAPI, BACEN, Finnhub) — Total: {len(coletas_brutas)} ativos")
    
    # Agrupa por fonte para exibição
    fontes = {}
    for item in coletas_brutas:
        f = item.get("fonte", "DESCONHECIDA")
        fontes.setdefault(f, []).append(item)

    for fonte, items in fontes.items():
        print(f"\n   🔹 Fonte: {fonte} ({len(items)} ativos)")
        for i in items:
            ativo = i.get("ativo")
            # Ignora os futuros do MT5 que já foram listados acima
            if fonte == "MT5" and ativo in ("BMFBOVESPA:WIN1!", "BMFBOVESPA:WDO1!", "WIN_LAST_TICK", "WDO_LAST_TICK"):
                continue
            
            status = i.get("status")
            dados = i.get("dados_reais") or {}
            var = dados.get("change_percent")
            var_d = dados.get("change_daily")
            close = dados.get("close")
            
            status_icon = "✅" if status == "OK" else "⚠️"
            
            # Se for ADR, mostra Pré e Diário
            if var_d is not None and var != var_d:
                print(f"      {status_icon} {ativo:<20} | Close: {_fmt(close):>10} | Pré/Ext: {_fmt(var, '%'):>8} | Diário: {_fmt(var_d, '%'):>8}")
            else:
                print(f"      {status_icon} {ativo:<20} | Close: {_fmt(close):>10} | Var: {_fmt(var, '%'):>8}")

    # 3. NOTÍCIAS
    not_cal = _load(COLETAS / "Noticias_Calendario.json")
    not_imp = _load(COLETAS / "Noticias_Impacto_Dia.json")
    print(f"\n📌 3. Notícias e Calendário")
    print(f"   Impacto do Dia : {not_imp.get('resumo', {}).get('classificacao', 'N/A')}")
    eventos = not_cal.get("calendario_eventos", {}).get("eventos", [])
    print(f"   Eventos 2/3★   : {len(eventos)} mapeados")
    for ev in eventos[:3]: # Mostra apenas os 3 primeiros
        print(f"      - {ev.get('hora')} | {ev.get('pais')} | {ev.get('evento')} ({ev.get('importancia')}★)")
    if len(eventos) > 3:
        print(f"      ... e mais {len(eventos)-3} eventos.")

    # 4. SAÚDE DO DADOS VALIDADOS
    val = _load(COLETAS / "Dados_Validados.json")
    meta = val.get("metadata_validacao", {})
    print(f"\n📌 4. Validação de Dados (Dados_Validados.json)")
    print(f"   Recebidos : {meta.get('total_recebidos', 0)}")
    print(f"   Aprovados : {meta.get('total_aprovados', 0)}")
    print(f"   Rejeitados: {meta.get('total_rejeitados', 0)}")
    
    rejeitados = val.get("relatorio_rejeicoes", [])
    if rejeitados:
        print("   ⚠️ Motivos de Rejeição:")
        for r in rejeitados[:5]:
            print(f"      - {r.get('ativo')}: {r.get('motivo')}")

    print("\n" + "=" * 85)
    print(" FIM DA AUDITORIA")
    print("=" * 85)

if __name__ == "__main__":
    main()