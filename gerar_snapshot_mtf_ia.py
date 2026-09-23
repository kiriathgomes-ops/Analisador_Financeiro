#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_snapshot_mtf_ia.py
========================
Gera um .txt com prompt + candles M5/M15 prontos para colar em uma IA.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from Motor_SMC_Regras import analisar_smc, CONFIG, BRT
from Rodar_SMC_Regras import carregar_multi_mt5

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

SAIDA_TXT = BASE_DIR / "Coletas" / "snapshot_mtf_ia.txt"
SAIDA_JSON = BASE_DIR / "Coletas" / "snapshot_mtf_scripts.json"

ATIVO = "WIN$"


def coletar(qtd_m5, qtd_m15):
    tf_spec = {
        "15m": {"min": 15, "qtd": qtd_m15, "arquivo": ""},
        "5m":  {"min": 5,  "qtd": qtd_m5,  "arquivo": ""},
    }
    return carregar_multi_mt5(ATIVO, tf_spec)


PROMPT_INSTRUCOES = """Voce e um analista institucional de mesa especializado em Smart Money Concepts (SMC/ICT). Sua tarefa e aplicar EXATAMENTE as regras descritas abaixo sobre os candles M15 e M5 do WIN fornecidos.

Nao invente dados. Se faltar informacao, use null. Devolva SOMENTE um bloco JSON no formato especificado no final, sem texto extra.
"""

REGRAS = """## Regras SMC/ICT (replicar identicamente)

### 1. Swings
- Janela: 2 candles a esquerda + 2 a direita
- Swing HIGH: candle[i].high >= max(high[i-2 : i+3])
- Swing LOW:  candle[i].low  <= min(low[i-2 : i+3])
- Equal High/Low (tol 15 pts): dois swings no mesmo nivel

### 2. BOS / CHoCH
- BOS de alta:  close > swing_high anterior, em tendencia de alta
- CHoCH de alta: close > swing_high anterior, em tendencia de baixa
- BOS/CHoCH de baixa: espelhado
- BIAS = direcao do ULTIMO evento de estrutura (BOS/CHoCH)

### 3. FVG (Fair Value Gap)
- Precisa do candle do meio com EXPANSAO FORTE
  (volume >= 1.2x media20 E corpo >= 1.3x media20)
- FVG de COMPRA: candle[i].low > candle[i-2].high, gap >= 20 pts
- FVG de VENDA: candle[i].high < candle[i-2].low, gap >= 20 pts
- Marcar como preenchido se o preco voltar a faixa

### 4. Order Block
- OB de COMPRA: ultimo candle de baixa antes de swing LOW rompido
- OB de VENDA: ultimo candle de alta antes de swing HIGH rompido
- Range do OB >= 30 pts (menor = ruido)
- Validacao: precisa de BOS/CHoCH na direcao alvo em ate 40 candles
- Dedup: OBs a menos de 50 pts (WIN) sao o mesmo bloco

### 5. Liquidez
- BSL: equal highs agrupados (tol 15 pts)
- SSL: equal lows agrupados (tol 15 pts)

### 6. Confluencia OB x POC
- Se OB mais recente esta a <= 300 pts do POC ontem -> confluente

### 7. Confianca ponderada (0-100)
Pesos: bias=25, BOS=20, CHoCH=10, FVG=15, OB=15, OB_confluente=15
Score = soma dos pesos dos criterios ativos / total_possivel * 100

### 8. Consolidacao Multi-Timeframe
- bias_m15, bias_m5 definidos pelo passo 2
- Se M15=M5: veredito ALINHADO
- Se M15!=M5 e um deles LATERAL: veredito PULLBACK
- Se M15!=M5 e ambos direcionais: veredito CONFLITO
"""
FORMATO_SAIDA = """## Formato de saida (JSON exato)

Devolva SOMENTE este JSON, sem texto antes ou depois:

{
  "bias_m15": "ALTA | BAIXA | LATERAL",
  "confianca_m15": 0,
  "bias_m5": "ALTA | BAIXA | LATERAL",
  "confianca_m5": 0,
  "poc_ontem": null,
  "vwap_ontem": null,
  "order_blocks_m15": [],
  "order_blocks_m5": [],
  "fair_value_gaps_m15": [],
  "fair_value_gaps_m5": [],
  "liquidez_m15": {"bsl": [], "ssl": []},
  "liquidez_m5": {"bsl": [], "ssl": []},
  "eventos_m15": [],
  "eventos_m5": [],
  "consolidacao_mtf": {
    "veredito": "ALINHADO_FORTE | PULLBACK | CONFLITO_MACRO | DIVERGENTE | NEUTRO",
    "direcao_dominante": "ALTA | BAIXA | LATERAL",
    "racional": "1-3 linhas"
  }
}
"""


def candles_para_json(candles, max_n=None):
    if max_n and len(candles) > max_n:
        candles = candles[-max_n:]
    return [
        {
            "t": c.get("time", ""),
            "o": round(float(c.get("open", 0)), 0),
            "h": round(float(c.get("high", 0)), 0),
            "l": round(float(c.get("low", 0)), 0),
            "c": round(float(c.get("close", 0)), 0),
            "v": int(float(c.get("volume", 0))),
        }
        for c in candles
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qtd-m5", type=int, default=300)
    ap.add_argument("--qtd-m15", type=int, default=300)
    ap.add_argument("--lookback-m5", type=int, default=120)
    ap.add_argument("--lookback-m15", type=int, default=80)
    ap.add_argument("--no-notepad", action="store_true")
    args = ap.parse_args()

    print("=" * 62)
    print(" GERADOR DE SNAPSHOT MTF PARA IA")
    print("=" * 62)

    print(f"\n-> Coletando {ATIVO}...")
    try:
        coletas = coletar(args.qtd_m5, args.qtd_m15)
    except Exception as e:
        print(f"[ERRO] Coleta MT5: {e}")
        return 1

    candles_5, simb_real = coletas.get("5m", ([], ""))
    candles_15, _ = coletas.get("15m", ([], ""))

    if not candles_5 or not candles_15:
        print("[ERRO] MT5 retornou candles vazios.")
        return 1

    print(f"   [OK] Simbolo: {simb_real}")
    print(f"   [OK] M5:  {len(candles_5)} candles")
    print(f"   [OK] M15: {len(candles_15)} candles")

    print("\n-> Rodando Motor_SMC_Regras em M5 e M15...")
    res_5 = analisar_smc(candles_5, ativo=simb_real or ATIVO, timeframe="5m", config=CONFIG)
    res_15 = analisar_smc(candles_15, ativo=simb_real or ATIVO, timeframe="15m", config=CONFIG)

    m5_ia = candles_para_json(candles_5, max_n=args.lookback_m5)
    m15_ia = candles_para_json(candles_15, max_n=args.lookback_m15)

    poc_ontem = (res_5.get("niveis_institucionais") or {}).get("poc_ontem")
    vwap_ontem = (res_5.get("niveis_institucionais") or {}).get("vwap_ontem")

    ts = datetime.now(BRT).strftime("%d/%m/%Y %H:%M")
    ts_iso = datetime.now(BRT).isoformat(timespec="seconds")

    sep = "=" * 62
    partes = [
        sep,
        f"ANALISE SMC MULTI-TIMEFRAME - {simb_real or ATIVO} ({ts})",
        sep,
        "",
        "[INSTRUCOES]",
        PROMPT_INSTRUCOES.strip(),
        "",
        "[REGRAS SMC/ICT]",
        REGRAS.strip(),
        "",
        "[NIVEIS JA CALCULADOS]",
        f"POC_ONTEM: {poc_ontem:.0f}" if poc_ontem else "POC_ONTEM: null",
        f"VWAP_ONTEM: {vwap_ontem:.1f}" if vwap_ontem else "VWAP_ONTEM: null",
        "",
        f"[CANDLES M15 - ultimos {len(m15_ia)} candles]",
        json.dumps(m15_ia, ensure_ascii=False, separators=(",", ":")),
        "",
        f"[CANDLES M5 - ultimos {len(m5_ia)} candles]",
        json.dumps(m5_ia, ensure_ascii=False, separators=(",", ":")),
        "",
        "[FORMATO DE SAIDA]",
        FORMATO_SAIDA.strip(),
        "",
        sep,
        f"FIM - snapshot gerado em {ts_iso}",
        sep,
    ]

    texto = "\n".join(partes)
    SAIDA_TXT.parent.mkdir(parents=True, exist_ok=True)
    SAIDA_TXT.write_text(texto, encoding="utf-8")

    payload_scripts = {
        "gerado_em": ts_iso,
        "ativo": simb_real or ATIVO,
        "timeframes": {
            "M15": {
                "bias": res_15.get("bias_direcional"),
                "confianca": res_15.get("confianca_visual"),
                "poc_ontem": (res_15.get("niveis_institucionais") or {}).get("poc_ontem"),
                "vwap_ontem": (res_15.get("niveis_institucionais") or {}).get("vwap_ontem"),
                "order_blocks": res_15.get("order_blocks"),
                "fvgs": res_15.get("fair_value_gaps"),
                "liquidez": res_15.get("liquidez"),
                "eventos": res_15.get("eventos_estrutura"),
            },
            "M5": {
                "bias": res_5.get("bias_direcional"),
                "confianca": res_5.get("confianca_visual"),
                "poc_ontem": (res_5.get("niveis_institucionais") or {}).get("poc_ontem"),
                "vwap_ontem": (res_5.get("niveis_institucionais") or {}).get("vwap_ontem"),
                "order_blocks": res_5.get("order_blocks"),
                "fvgs": res_5.get("fair_value_gaps"),
                "liquidez": res_5.get("liquidez"),
                "eventos": res_5.get("eventos_estrutura"),
            },
        },
    }
    SAIDA_JSON.write_text(
        json.dumps(payload_scripts, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print("=" * 62)
    print(" SNAPSHOT GERADO")
    print("=" * 62)
    print(f"  TXT (IA)    : {SAIDA_TXT}")
    print(f"  JSON (ref)  : {SAIDA_JSON}")
    print(f"  Tamanho     : {len(texto):,} chars")
    print(f"  M15 candles : {len(m15_ia)}")
    print(f"  M5 candles  : {len(m5_ia)}")
    print(f"  Scripts M15 : {res_15.get('bias_direcional')} ({res_15.get('confianca_visual')}%)")
    print(f"  Scripts M5  : {res_5.get('bias_direcional')} ({res_5.get('confianca_visual')}%)")
    print("=" * 62)

    if not args.no_notepad:
        try:
            import subprocess
            subprocess.Popen(["notepad.exe", str(SAIDA_TXT)])
            print("  [OK] Notepad aberto.")
        except Exception as e:
            print(f"  [AVISO] {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
