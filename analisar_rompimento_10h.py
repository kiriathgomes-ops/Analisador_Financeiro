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
from datetime import datetime, time as dt_time, timedelta
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

# Fallback estatico — a lista real vem de Coletas/Dados_MT5_v2_2.json
SIMBOLOS_MT5_FALLBACK = ["WINV26", "WINZ26", "WIN$"]
JSON_MT5 = COLETAS_DIR / "Dados_MT5_v2_2.json"


def _descobrir_contrato_vigente():
    """
    Le Coletas/Dados_MT5_v2_2.json e retorna a lista de simbolos a testar
    no MT5. Prioriza ativos.WIN.contrato_principal e completa com
    contratos_vigentes (na ordem). Se falhar, usa o fallback estatico.
    """
    try:
        if JSON_MT5.exists():
            with open(JSON_MT5, "r", encoding="utf-8") as f:
                data = json.load(f)
            win = ((data.get("ativos") or {}).get("WIN") or {})
            principal = win.get("contrato_principal")
            simbolos = []
            if principal:
                simbolos.append(principal)
            for c in (win.get("contratos_vigentes") or []):
                nome = c.get("contrato")
                if nome and nome not in simbolos:
                    simbolos.append(nome)
            if simbolos:
                print(f"[DIAG] Contrato vigente do JSON: {principal}")
                print(f"[DIAG] Simbolos a testar: {simbolos}")
                return simbolos
    except Exception as e:
        print(f"[DIAG] Falha ao ler {JSON_MT5}: {e}")
    print(f"[DIAG] Usando fallback estatico: {SIMBOLOS_MT5_FALLBACK}")
    return list(SIMBOLOS_MT5_FALLBACK)


def _obter_spot_mt5():
    """
    Le o spot REAL do MT5 no instante da geracao (last/bid/ask).
    Usa o contrato vigente do JSON. Retorna dict ou None.
    Nao deve travar o pipeline: qualquer erro retorna None.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return None
    if not mt5.initialize():
        return None
    try:
        simbolos = _descobrir_contrato_vigente()
        simbolo = simbolos[0] if simbolos else None
        if not simbolo:
            return None
        info = mt5.symbol_info(simbolo)
        if info is None:
            return None
        if not info.visible:
            mt5.symbol_select(simbolo, True)
        tick = mt5.symbol_info_tick(simbolo)
        if tick is None:
            return None
        return {
            "simbolo": simbolo,
            "bid": float(getattr(tick, "bid", 0) or 0),
            "ask": float(getattr(tick, "ask", 0) or 0),
            "last": float(getattr(tick, "last", 0) or 0),
            "time": datetime.fromtimestamp(tick.time).isoformat(),
        }
    except Exception:
        return None
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


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
        simbolos = _descobrir_contrato_vigente()
        hoje = datetime.now().date()

        # Tenta hoje e cai para ate 7 dias uteis anteriores se nao achar
        # (fim de semana, feriado, ou rodada fora da janela do pregao).
        for offset_dias in range(0, 7):
            alvo = hoje - timedelta(days=offset_dias)
            for simbolo in simbolos:
                info = mt5.symbol_info(simbolo)
                if info is None:
                    print(f"[DIAG] {simbolo}: symbol_info=None (nao existe)")
                    continue
                if not info.visible:
                    mt5.symbol_select(simbolo, True)

                rates = mt5.copy_rates_from_pos(
                    simbolo, mt5.TIMEFRAME_M5, 0, 500
                )
                if rates is None or len(rates) == 0:
                    print(
                        f"[DIAG] {simbolo}: copy_rates_from_pos "
                        f"retornou vazio (last_error={mt5.last_error()})"
                    )
                    continue

                dt_first = datetime.fromtimestamp(rates[0]["time"])
                dt_last = datetime.fromtimestamp(rates[-1]["time"])
                print(
                    f"[DIAG] {simbolo} qtd=500: {len(rates)} barras, "
                    f"{dt_first.isoformat()} -> {dt_last.isoformat()} "
                    f"(alvo={alvo.isoformat()})"
                )

                for r in rates:
                    dt = datetime.fromtimestamp(r["time"])
                    if (
                        dt.date() == alvo
                        and dt.hour == 10
                        and dt.minute == 0
                    ):
                        agora = datetime.now()
                        em_formacao = agora.time() < dt_time(10, 5)
                        if alvo != hoje:
                            print(
                                f"[DIAG] Vela 10:00 de hoje nao achada; "
                                f"usando ultimo dia util: {alvo.isoformat()}"
                            )
                        return {
                            "simbolo": simbolo,
                            "time": dt.isoformat(),
                            "open": float(r["open"]),
                            "high": float(r["high"]),
                            "low": float(r["low"]),
                            "close": float(r["close"]),
                            "volume": float(r["tick_volume"]),
                            "status": (
                                "EM_FORMACAO" if em_formacao else "FECHADA"
                            ),
                        }

        print(
            "[AVISO] Vela 10:00 nao encontrada nos ultimos 7 dias "
            "em nenhum simbolo testado."
        )
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


def bloco_risco_orb(vela: dict, spot: dict, ajuste: float = None) -> str:
    """
    Bloco E.5 — Risco do setup ORB.
    Explicita M, m, stops, alvos e o estado REAL do rompimento
    (usando o spot do MT5, nao o WIN_FUT defasado do Bloco A).
    """
    if not vela:
        return "--- BLOCO E.5: RISCO ORB ---\n  [sem vela 10:00 para calcular]"

    M = float(vela["high"])
    m = float(vela["low"])
    A = M - m

    preco_ref = None
    fonte_ref = "—"
    if spot and spot.get("last", 0) > 0:
        preco_ref = spot["last"]
        fonte_ref = f"MT5 spot ({spot.get('simbolo','?')})"

    linhas = [
        "--- BLOCO E.5: RISCO ORB ---",
        "",
        f"  Gatilho COMPRA (M) : {fmt(M, 0)}",
        f"  Stop  COMPRA       : {fmt(m, 0)}   (risco {fmt(A, 0)} pts)",
        f"  Alvo  COMPRA       : {fmt(M + A, 0)}",
        "",
        f"  Gatilho VENDA  (m) : {fmt(m, 0)}",
        f"  Stop  VENDA        : {fmt(M, 0)}   (risco {fmt(A, 0)} pts)",
        f"  Alvo  VENDA        : {fmt(m - A, 0)}",
        "",
        f"  Preco spot MT5     : {fmt(preco_ref, 0) if preco_ref else '—'}   ({fonte_ref})",
    ]

    if preco_ref:
        if preco_ref > M:
            dist = preco_ref - M
            linhas.append(f"  Rompimento REAL    : ALTA  (dist {fmt(dist, 0)} pts)")
        elif preco_ref < m:
            dist = m - preco_ref
            linhas.append(f"  Rompimento REAL    : BAIXA (dist {fmt(dist, 0)} pts)")
        else:
            linhas.append("  Rompimento REAL    : NAO OCORREU (preco dentro da faixa)")

    # --- REGRA 10 (prioridade maxima) ---
    if preco_ref and ajuste and ajuste > 0:
        gap = abs(preco_ref - ajuste)
        if preco_ref > ajuste:
            posicao = "ACIMA"
            direcao_bloqueada = "VENDA"
        elif preco_ref < ajuste:
            posicao = "ABAIXO"
            direcao_bloqueada = "COMPRA"
        else:
            posicao = "NO AJUSTE"
            direcao_bloqueada = None

        linhas.append("")
        linhas.append(f"  WIN_AJUSTE B3      : {fmt(ajuste, 0)}")
        linhas.append(f"  Posicao vs ajuste  : {posicao}  (gap {fmt(gap, 0)} pts)")
        if gap > 500 and direcao_bloqueada:
            linhas.append(f"  REGRA 10 ATIVA     : {direcao_bloqueada} BLOQUEADA (gap > 500)")
            linhas.append("  -> VIES FINAL = AGUARDAR (prioridade maxima).")
        else:
            linhas.append(f"  REGRA 10           : ok (gap {fmt(gap, 0)} < 500)")

    if A > 400:
        linhas.append("")
        linhas.append(f"  ALERTA: amplitude {fmt(A, 0)} pts — stop largo.")
        linhas.append(f"  Loss potencial (1 contrato) = {fmt(A, 0)} pts por lado.")

    linhas.append("")
    linhas.append("  NOTA: quando o alinhamento e DIVERGENTE mas o gatilho")
    linhas.append("  mecanico JA disparou ha menos de 150 pts, o setup ORB")
    linhas.append("  segue valido — com confianca reduzida e stop = amplitude.")

    return "\n".join(linhas)


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

    # Spot real do MT5 no instante da geracao (contorna defasagem do Bloco A)
    spot = _obter_spot_mt5()
    if spot:
        print(f"[DIAG] Spot MT5: {spot['simbolo']} last={spot['last']} "
              f"bid={spot['bid']} ask={spot['ask']}")

    # Ajuste B3 (para checagem da Regra 10 no Bloco E.5)
    _aj = ((ativos.get("ativos") or {}).get("WIN_AJUSTE") or {}).get("preco")
    try:
        ajuste_b3 = float(_aj) if _aj else None
    except (TypeError, ValueError):
        ajuste_b3 = None
    if ajuste_b3:
        print(f"[DIAG] Ajuste B3: {ajuste_b3}")

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
        bloco_risco_orb(vela, spot, ajuste_b3),
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