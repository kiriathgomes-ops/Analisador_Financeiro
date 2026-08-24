# ============================================================
# ARQUIVO: Gerar_Relatorio_Mensagem.py
#
# OBJETIVO:
#   Ler Coletas/EstimativaAbertura.json e montar uma mensagem
#   em texto (Markdown) para day trade (WIN e, se houver, WDO).
#
# COMPATIBILIDADE DE SCHEMA:
#   Aceita as duas formas geradas pela CalculadoraEstimativaAbertura:
#     - "estimativa_abertura"  (singular  — versão só WIN)
#     - "estimativas_abertura" (plural    — versão WIN + WDO)
#   Blocos de WDO / pivot WDO são opcionais: se não existirem,
#   o relatório omite a seção do Mini Dólar sem quebrar.
# ============================================================

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_INPUT = os.path.join(BASE_DIR, "Coletas", "EstimativaAbertura.json")


def _fmt_num(valor, casas=0, default="N/A"):
    """Formata número com separador de milhar; devolve default se inválido."""
    if valor is None:
        return default
    try:
        v = float(valor)
        if casas == 0:
            return f"{v:,.0f}"
        return f"{v:,.{casas}f}"
    except (TypeError, ValueError):
        return default


def _bloco_estimativas(data: dict) -> dict:
    """
    Extrai o bloco de estimativas aceitando singular ou plural.
    Retorno: dict com chaves possíveis WIN_INDICE, WDO_DOLAR.
    """
    return (
        data.get("estimativas_abertura")
        or data.get("estimativa_abertura")
        or {}
    )


def formatar_relatorio():
    if not os.path.exists(FILE_INPUT):
        print(f"[ERRO] Arquivo {FILE_INPUT} não encontrado.")
        return None

    try:
        with open(FILE_INPUT, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERRO] Falha ao ler JSON: {e}")
        return None

    # ---- Metadata / horário ----
    meta = data.get("metadata_calculo") or {}
    ts = meta.get("timestamp_calculo") or meta.get("timestamp")
    if ts:
        try:
            hora_str = datetime.fromisoformat(ts).strftime("%d/%m/%Y às %H:%M")
        except ValueError:
            hora_str = str(ts)
    else:
        hora_str = datetime.now().strftime("%d/%m/%Y às %H:%M")

    # ---- Estimativas (compatível singular/plural) ----
    bloco_est = _bloco_estimativas(data)
    win = bloco_est.get("WIN_INDICE")
    wdo = bloco_est.get("WDO_DOLAR")

    if not win:
        print(
            "[ERRO] WIN_INDICE não encontrado em EstimativaAbertura.json "
            "(nem em estimativa_abertura nem em estimativas_abertura)."
        )
        return None

    # ---- Pivots (WDO opcional) ----
    pivots = data.get("pivot_points") or {}
    pivot_win = pivots.get("WIN_FUT")
    pivot_wdo = pivots.get("WDO_FUT")

    # ---- Macro ----
    macro = data.get("resumo_macro") or {}

    # ---- Ícones de direção ----
    var_win = win.get("variacao_teorica_pct") or 0.0
    icon_win = "🟢" if var_win >= 0 else "🔴"

    # ============================================================
    # MONTAGEM DA MENSAGEM
    # ============================================================
    linhas = [
        "🚀 *MÉRICA DE ABERTURA - DAY TRADE* 🚀",
        f"⏱ _Atualizado em: {hora_str}_",
        "",
        "----------------------------------",
        "📊 *MINI ÍNDICE (WIN)*",
        f"• Teórico: `{_fmt_num(win.get('abertura_teorica_pontos'))} pts`",
        f"• Variação Est.: `{icon_win} {var_win:+.2f}%`",
        f"• Ajuste Base: `{_fmt_num(win.get('pontos_ajuste_base'))} pts`",
        "",
    ]

    if pivot_win and all(
        pivot_win.get(k) is not None for k in ("PP", "R1", "R2", "S1", "S2")
    ):
        linhas.extend(
            [
                "📍 *Pontos Relevantes (WIN):*",
                (
                    f"• R2: `{_fmt_num(pivot_win['R2'])}` | "
                    f"R1: `{_fmt_num(pivot_win['R1'])}`"
                ),
                f"• Pivot: `{_fmt_num(pivot_win['PP'])}`",
                (
                    f"• S1: `{_fmt_num(pivot_win['S1'])}` | "
                    f"S2: `{_fmt_num(pivot_win['S2'])}`"
                ),
                "",
            ]
        )
    else:
        linhas.append("_Pivot WIN indisponível neste JSON._")
        linhas.append("")

    # ---- Seção WDO (só se existir no JSON) ----
    if wdo:
        var_wdo = wdo.get("variacao_teorica_pct") or 0.0
        icon_wdo = "🟢" if var_wdo >= 0 else "🔴"
        linhas.extend(
            [
                "----------------------------------",
                "💵 *MINI DÓLAR (WDO)*",
                f"• Teórico: `{_fmt_num(wdo.get('abertura_teorica_pontos'), 2)}`",
                f"• Variação Est.: `{icon_wdo} {var_wdo:+.2f}%`",
                f"• Ajuste Base: `{_fmt_num(wdo.get('pontos_ajuste_base'), 2)}`",
                "",
            ]
        )
        if pivot_wdo and all(
            pivot_wdo.get(k) is not None for k in ("PP", "R1", "R2", "S1", "S2")
        ):
            linhas.extend(
                [
                    "📍 *Pontos Relevantes (WDO):*",
                    (
                        f"• R2: `{_fmt_num(pivot_wdo['R2'], 2)}` | "
                        f"R1: `{_fmt_num(pivot_wdo['R1'], 2)}`"
                    ),
                    f"• Pivot: `{_fmt_num(pivot_wdo['PP'], 2)}`",
                    (
                        f"• S1: `{_fmt_num(pivot_wdo['S1'], 2)}` | "
                        f"S2: `{_fmt_num(pivot_wdo['S2'], 2)}`"
                    ),
                    "",
                ]
            )
        else:
            linhas.append("_Pivot WDO indisponível neste JSON._")
            linhas.append("")
    else:
        linhas.extend(
            [
                "----------------------------------",
                "💵 *MINI DÓLAR (WDO)*",
                "_Não gerado nesta versão da estimativa (somente WIN)._ ",
                "",
            ]
        )

    # ---- Macro ----
    linhas.extend(
        [
            "----------------------------------",
            "🌐 *CENÁRIO MACRO EXTERNO*",
            f"• VIX (Volatilidade): `{macro.get('vix', 'N/A')}`",
            f"• Minério de Ferro: `${macro.get('iron_ore', 'N/A')}`",
            f"• Petróleo: `${macro.get('crude_oil', 'N/A')}`",
            (
                f"• DI 2027: `{macro.get('di1_2027', 'N/A')}%` | "
                f"DI 2029: `{macro.get('di1_2029', 'N/A')}%`"
            ),
            "----------------------------------",
            "⚠️ _Relatório quantitativo teórico para apoio de decisão._",
            "",
        ]
    )

    return "\n".join(linhas)


if __name__ == "__main__":
    relatorio = formatar_relatorio()
    if relatorio:
        print(relatorio)
