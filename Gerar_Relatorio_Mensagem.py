import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_INPUT = os.path.join(BASE_DIR, "Coletas", "EstimativaAbertura.json")


def formatar_relatorio():
    if not os.path.exists(FILE_INPUT):
        print(f"[ERRO] Arquivo {FILE_INPUT} não encontrado.")
        return None

    with open(FILE_INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extração de Dados
    ts = data["metadata_calculo"]["timestamp_calculo"]
    hora_str = datetime.fromisoformat(ts).strftime("%d/%m/%Y às %H:%M")

    win = data["estimativas_abertura"]["WIN_INDICE"]
    wdo = data["estimativas_abertura"]["WDO_DOLAR"]
    pivot_win = data["pivot_points"]["WIN_FUT"]
    pivot_wdo = data["pivot_points"]["WDO_FUT"]
    macro = data["resumo_macro"]

    # Indicadores visuais (Emoji de Alta / Baixa)
    icon_win = "🟢" if win["variacao_teorica_pct"] >= 0 else "🔴"
    icon_wdo = "🟢" if wdo["variacao_teorica_pct"] >= 0 else "🔴"

    # Montagem do Texto em Markdown
    mensagem = f"""
🚀 *MÉRICA DE ABERTURA - DAY TRADE* 🚀
⏱ _Atualizado em: {hora_str}_

----------------------------------
📊 *MINI ÍNDICE (WIN)*
• Teórico: `{win['abertura_teorica_pontos']:,.0f} pts`
• Variação Est.: `{icon_win} {win['variacao_teorica_pct']:+.2f}%`
• Ajuste Base: `{win['pontos_ajuste_base']:,.0f} pts`

📍 *Pontos Relevantes (WIN):*
• R2: `{pivot_win['R2']:,.0f}` | R1: `{pivot_win['R1']:,.0f}`
• Pivot: `{pivot_win['PP']:,.0f}`
• S1: `{pivot_win['S1']:,.0f}` | S2: `{pivot_win['S2']:,.0f}`

----------------------------------
💵 *MINI DÓLAR (WDO)*
• Teórico: `{wdo['abertura_teorica_pontos']:.2f} pts`
• Variação Est.: `{icon_wdo} {wdo['variacao_teorica_pct']:+.2f}%`
• Ajuste Base: `{wdo['pontos_ajuste_base']:.2f} pts`

📍 *Pontos Relevantes (WDO):*
• R2: `{pivot_wdo['R2']:.2f}` | R1: `{pivot_wdo['R1']:.2f}`
• Pivot: `{pivot_wdo['PP']:.2f}`
• S1: `{pivot_wdo['S1']:.2f}` | S2: `{pivot_wdo['S2']:.2f}`

----------------------------------
🌐 *CENÁRIO MACRO EXTERNO*
• VIX (Volatilidade): `{macro['vix']}`
• Minério de Ferro: `${macro['iron_ore']}`
• Petróleo Brent: `${macro['crude_oil']}`
• DI 2027: `{macro['di1_2027']}%` | DI 2029: `{macro['di1_2029']}%`
----------------------------------
⚠️ _Relatório quantitativo teórico para apoio de decisão._
"""
    return mensagem


if __name__ == "__main__":
    relatorio = formatar_relatorio()
    if relatorio:
        print(relatorio)