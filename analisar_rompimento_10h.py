#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analisar_rompimento_10h.py
==========================
Le os JSONs do pipeline + a vela M5 de 10:00 do MT5 e monta um snapshot
pronto para copiar/colar no prompt de analise (PromptIA/Prompt_Rompimento_10h.txt).

Uso:
    python analisar_rompimento_10h.py
    python analisar_rompimento_10h.py --force     # gera snapshot mesmo fora de 10:00
    python analisar_rompimento_10h.py --vela-manual "186850,187100,186720,187050"

Saida:
    Coletas/snapshot_rompimento_10h.txt
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, time as dt_time
from pathlib import Path


BASE_DIR = Path(".").resolve()
COLETAS_DIR = BASE_DIR / "Coletas"
PROMPT_PATH = BASE_DIR / "PromptIA" / "Prompt_Rompimento_10h.txt"
SAIDA_PATH = COLETAS_DIR / "snapshot_rompimento_10h.txt"

ARQUIVOS = {
    "ativos":       COLETAS_DIR / "DadosAtivosUnificados.json",
    "metricas":     COLETAS_DIR / "Metricas_Calculadas.json",
    "estimativa":   COLETAS_DIR / "EstimativaAbertura.json",
    "smc":          COLETAS_DIR / "AnaliseGraficaSMC_Regras.json",
    "decisao":      COLETAS_DIR / "Decisao_V2.json",
}

# Simbolos candidatos para buscar a vela M5 no MT5
SIMBOLOS_MT5 = ["WINV26", "WINZ26", "WIN$"]


# ============================================================
# HELPERS
# ============================================================
def carregar_json(caminho: Path) -> dict:
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def fmt(valor, casas=2, sufixo=""):
    if valor is None:
        return "—"
    try:
        return f"{float(valor):,.{casas}f}{sufixo}"
    except (TypeError, ValueError):
        return str(valor)


def fmt_pct(valor):
    if valor is None:
        return "—"
    try:
        return f"{float(valor):+.2f}%"
    except (TypeError, ValueError):
        return "—"


# ============================================================
# VELA 10:00 DO MT5
# ============================================================
def obter_vela_10h():
    """Busca a vela M5 de 10:00 no MT5. Retorna dict ou None."""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("[AVISO] MetaTrader5 nao instalado. Use --vela-manual.")
        return None

    if not mt5.initialize():
        print(f"[AVISO] MT5 nao inicializou: {mt5.last_error()}")
        return None

    try:
        hoje = datetime.now().date()
        for simbolo in SIMBOLOS_MT5:
            info = mt5.symbol_info(simbolo)
            if info is None:
                continue
            if not info.visible:
                mt5.symbol_select(simbolo, True)

            rates = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M5, 0, 100)
            if rates is None or len(rates) == 0:
                continue

            # Procura a vela com hora 10:00 de hoje
            for r in rates:
                dt = datetime.fromtimestamp(r["time"])
                if dt.date() == hoje and dt.hour == 10 and dt.minute == 0:
                    agora = datetime.now()
                    # Se a vela esta em formacao (agora < 10:05)
                    em_formacao = agora.time() < dt_time(10, 5)
                    return {
                        "simbolo": simbolo,
                        "time": dt.isoformat(),
                        "open": float(r["open"]),
                        "high": float(r["high"]),
                        "low": float(r["low"]),
                        "close": float(r["close"]),
                        "volume": float(r["tick_volume"]),
                        "status": "EM_FORMACAO" if em_formacao else "FECHADA",
                    }

        print(f"[AVISO] Vela 10:00 de hoje nao encontrada no MT5.")
        return None
    finally:
        mt5.shutdown()


def vela_manual(csv: str):
    """Formato: open,high,low,close"""
    try:
        partes = [float(x.strip()) for x in csv.split(",")]
        if len(partes) != 4:
            raise ValueError("Esperado 4 valores: open,high,low,close")
        return {
            "simbolo": "MANUAL",
            "time": datetime.now().isoformat(),
            "open": partes[0],
            "high": partes[1],
            "low": partes[2],
            "close": partes[3],
            "volume": 0.0,
            "status": "MANUAL",
        }
    except Exception as e:
        print(f"[ERRO] --vela-manual invalido: {e}")
        return None


# ============================================================
# BLOCOS DE DADOS
# ============================================================
def bloco_ativos(unif: dict) -> str:
    a = (unif.get("ativos") or {}) if isinstance(unif, dict) else {}

    def linha(nome, unidade=""):
        item = a.get(nome) or {}
        preco = item.get("preco")
        var = item.get("variacao_pct")
        return f"  {nome:20s} {fmt(preco, 2):>12s}{unidade}  {fmt_pct(var):>9s}"

    linhas = [
        "--- BLOCO A: ATIVOS (DadosAtivosUnificados) ---",
        "",
        "[ B3 / Futuros ]",
        linha("WIN_FUT", " pts"),
        linha("WIN_LAST_TICK", " pts"),
        linha("WIN_AJUSTE", " pts"),
        linha("WIN_FECHAMENTO_B3", " pts"),
        linha("WDO_FUT"),
        linha("WDO_AJUSTE"),
        "",
        "[ Curva DI ]",
        linha("DI1_2027", " %"),
        linha("DI1_2029", " %"),
        "",
        "[ Global ]",
        linha("VIX"),
        linha("SP500_FUT"),
        linha("NASDAQ_FUT"),
        linha("DXY"),
        linha("USD_BRL"),
        linha("USD_PTAX"),
        "",
        "[ Commodities ]",
        linha("IRON_ORE_2M"),
        linha("CRUDE_OIL"),
        linha("GOLD"),
        "",
        "[ ADRs Brasileiras ]",
        linha("EWZ"),
        linha("VALE_ADR"),
        linha("PETR_ADR"),
        linha("ITUB_ADR"),
        linha("BBAS_ADR"),
        linha("BBD_ADR"),
        linha("B3_ADR"),
        "",
        "[ Acoes B3 ]",
        linha("VALE3"),
        linha("PETR4"),
        linha("ITUB4"),
        linha("BBAS3"),
        linha("BBDC4"),
        linha("B3SA3"),
    ]
    return "\n".join(linhas)


def bloco_metricas(met: dict) -> str:
    ind = (met.get("indicadores_compostos") or {}) if isinstance(met, dict) else {}
    cambio = (met.get("cambio_e_arbitragem") or {})
    curva = (met.get("curva_juros_b3") or {})
    return "\n".join([
        "--- BLOCO B: METRICAS (Metricas_Calculadas) ---",
        "",
        f"  Indicador Mercado Externo : {fmt_pct(ind.get('indicador_mercado_externo'))}",
        f"  Indicador ADRs Brasileiras: {fmt_pct(ind.get('indicador_adrs_brasileiras'))}",
        f"  Spread WDO vs PTAX        : {fmt(cambio.get('spread_wdo_ptax_pontos'))} pts",
        f"  Inclinacao DI (29-27)     : {fmt(curva.get('inclinacao_29_27_bps'), 1)} bps",
    ])


def bloco_estimativa(est: dict) -> str:
    if not est:
        return "--- BLOCO C: ESTIMATIVA (EstimativaAbertura) ---\n  [arquivo vazio]"
    win = (est.get("estimativa_abertura") or {}).get("WIN_INDICE") or {}
    piv = (est.get("pivot_points") or {}).get("WIN_FUT") or {}
    coc = win.get("cost_of_carry") or {}
    return "\n".join([
        "--- BLOCO C: ESTIMATIVA (EstimativaAbertura) ---",
        "",
        f"  Abertura Teorica  : {fmt(win.get('abertura_teorica_pontos'), 0)} pts",
        f"  Variacao Teorica  : {fmt_pct(win.get('variacao_teorica_pct'))}",
        f"  Preco Carregado DI: {fmt(coc.get('preco_teorico_carregado'), 0)} pts",
        "",
        "  Pivots Classicos:",
        f"    R2: {fmt(piv.get('R2'), 0)} | R1: {fmt(piv.get('R1'), 0)} | PP: {fmt(piv.get('PP'), 0)} | S1: {fmt(piv.get('S1'), 0)} | S2: {fmt(piv.get('S2'), 0)}",
    ])


def bloco_smc(smc: dict) -> str:
    if not smc:
        return "--- BLOCO D: SMC (AnaliseGraficaSMC_Regras) ---\n  [arquivo vazio]"
    niv = smc.get("niveis_institucionais") or {}
    liq = smc.get("liquidez") or {}
    return "\n".join([
        "--- BLOCO D: SMC (AnaliseGraficaSMC_Regras) ---",
        "",
        f"  Vies Direcional    : {smc.get('bias_direcional', '—')}",
        f"  Confianca Visual   : {smc.get('confianca_visual', '—')}%",
        f"  POC Ontem          : {fmt(niv.get('poc_ontem'), 0)} pts",
        f"  VWAP Ontem         : {fmt(niv.get('vwap_ontem'), 1)} pts",
        f"  OB Alinhado com POC: {niv.get('ob_alinhado_com_poc', False)}",
        "",
        f"  Order Blocks       : {len(smc.get('order_blocks') or [])}",
        f"  Fair Value Gaps    : {len(smc.get('fair_value_gaps') or [])}",
        f"  BSL (topos)        : {liq.get('bsl', [])}",
        f"  SSL (fundos)       : {liq.get('ssl', [])}",
    ])


def bloco_vela10(vela: dict) -> str:
    if not vela:
        return "\n".join([
            "--- BLOCO E: VELA 10:00 (M5) ---",
            "",
            "  [NAO DISPONIVEL — use --vela-manual open,high,low,close]",
        ])

    amplitude = vela["high"] - vela["low"]
    dentro = 50 <= amplitude <= 700
    status_filtro = "DENTRO DO FILTRO" if dentro else "FORA DO FILTRO"

    return "\n".join([
        "--- BLOCO E: VELA 10:00 (M5) ---",
        "",
        f"  Status   : {vela['status']}",
        f"  Simbolo  : {vela['simbolo']}",
        f"  Abertura : {fmt(vela['open'], 0)}",
        f"  Maxima   : {fmt(vela['high'], 0)}",
        f"  Minima   : {fmt(vela['low'], 0)}",
        f"  Close    : {fmt(vela['close'], 0)}",
        f"  Amplitude: {fmt(amplitude, 0)} pts  [{status_filtro}]",
        f"  Volume   : {fmt(vela['volume'], 0)}",
    ])


def bloco_decisao(dec: dict) -> str:
    if not dec:
        return "--- BLOCO F: DECISAO V2 ---\n  [arquivo vazio]"
    d = dec.get("decisao") or {}
    meta = d.get("metadados") or {}
    nm = meta.get("novo_motor") or {}
    motivos = d.get("motivos") or []
    riscos = d.get("riscos") or []

    linhas = [
        "--- BLOCO F: DECISAO V2 ---",
        "",
        f"  Vies Final       : {d.get('vies_final', '—')}",
        f"  Confianca        : {d.get('confianca', '—')}%",
        f"  Entrada          : {fmt(d.get('entrada'), 0)}",
        f"  Stop             : {fmt(d.get('stop_loss'), 0)}",
        f"  Alvo 1 / Alvo 2  : {fmt(d.get('alvo_1'), 0)} / {fmt(d.get('alvo_2'), 0)}",
        "",
        f"  NOVO_MOTOR direcao : {nm.get('direcao', '—')}",
        f"  NOVO_MOTOR gap     : {fmt(nm.get('gap_pontos'), 0)} pts ({fmt_pct(nm.get('gap_pct'))})",
        f"  NOVO_MOTOR score   : {fmt(nm.get('score_magnitude'), 1)} ({nm.get('score_forca', '—')})",
        f"  Fonte abertura     : {nm.get('fonte_abertura', '—')}",
    ]
    if motivos:
        linhas.append("")
        linhas.append("  Motivos:")
        for m in motivos[:5]:
            linhas.append(f"    - {m}")
    if riscos:
        linhas.append("")
        linhas.append("  Riscos:")
        for r in riscos[:5]:
            linhas.append(f"    - {r}")
    return "\n".join(linhas)


# ============================================================
# MONTAGEM
# ============================================================
def montar_snapshot(vela: dict) -> str:
    ativos = carregar_json(ARQUIVOS["ativos"])
    metricas = carregar_json(ARQUIVOS["metricas"])
    estimativa = carregar_json(ARQUIVOS["estimativa"])
    smc = carregar_json(ARQUIVOS["smc"])
    decisao = carregar_json(ARQUIVOS["decisao"])

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Le o prompt do arquivo (se existir)
    if PROMPT_PATH.exists():
        prompt_txt = PROMPT_PATH.read_text(encoding="utf-8")
    else:
        prompt_txt = "[AVISO] Prompt nao encontrado em PromptIA/Prompt_Rompimento_10h.txt"

    sep = "=" * 65

    partes = [
        sep,
        "PROMPT — ANALISE DE ROMPIMENTO 10:00 (WINFUT)",
        f"Snapshot gerado em: {agora}",
        sep,
        "",
        prompt_txt,
        "",
        "",
        sep,
        "DADOS REAIS — SNAPSHOT DO PIPELINE",
        f"Timestamp: {agora}",
        sep,
        "",
        bloco_ativos(ativos),
        "",
        bloco_metricas(metricas),
        "",
        bloco_estimativa(estimativa),
        "",
        bloco_smc(smc),
        "",
        bloco_vela10(vela),
        "",
        bloco_decisao(decisao),
        "",
        sep,
        "FIM DO SNAPSHOT — COPIE TUDO E COLE NA IA",
        sep,
    ]

    return "\n".join(partes)


# ============================================================
# MAIN
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Gera snapshot mesmo fora da janela 10:00-10:10")
    parser.add_argument("--vela-manual", type=str, default=None,
                        help="Vela manual: 'open,high,low,close'")
    args = parser.parse_args()

    # Janela recomendada
    agora = datetime.now().time()
    if not args.force and not (dt_time(9, 55) <= agora <= dt_time(10, 15)):
        print(f"[AVISO] Fora da janela ideal (09:55-10:15). Agora: {agora.strftime('%H:%M:%S')}")
        print(f"        Use --force para gerar mesmo assim.")

    # Vela
    if args.vela_manual:
        vela = vela_manual(args.vela_manual)
    else:
        vela = obter_vela_10h()

    # Monta snapshot
    texto = montar_snapshot(vela)

    # Salva
    COLETAS_DIR.mkdir(parents=True, exist_ok=True)
    SAIDA_PATH.write_text(texto, encoding="utf-8")

    print()
    print("=" * 60)
    print(" SNAPSHOT GERADO")
    print("=" * 60)
    print(f"  Arquivo : {SAIDA_PATH}")
    print(f"  Tamanho : {len(texto)} caracteres")
    if vela:
        print(f"  Vela    : {vela['status']} | O={vela['open']:.0f} H={vela['high']:.0f} L={vela['low']:.0f} C={vela['close']:.0f}")
    print()
    print("  Abrindo no Notepad...")
    print()
    print("  Proximo passo (dentro do Notepad):")
    print("    1. Ctrl+A (seleciona tudo)")
    print("    2. Ctrl+C (copia)")
    print("    3. Cola na IA (Claude, GPT-4, etc)")
    print()

    # Abre automaticamente no Notepad (Windows)
    try:
        import subprocess
        subprocess.Popen(["notepad.exe", str(SAIDA_PATH)])
        print("  [OK] Notepad aberto.")
    except FileNotFoundError:
        # Fallback: os.startfile (abre com app padrao do .txt)
        try:
            import os
            os.startfile(str(SAIDA_PATH))
            print("  [OK] Arquivo aberto no app padrao.")
        except Exception as e:
            print(f"  [AVISO] Nao foi possivel abrir automaticamente: {e}")
            print(f"  Abra manualmente: notepad {SAIDA_PATH}")
    except Exception as e:
        print(f"  [AVISO] Falha ao abrir Notepad: {e}")
        print(f"  Abra manualmente: notepad {SAIDA_PATH}")

    print()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())