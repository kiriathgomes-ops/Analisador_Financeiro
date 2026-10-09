# -*- coding: utf-8 -*-
# fix95.py — Ordena a legenda do gráfico por valor (decrescente).
#
# PROBLEMA:
#   Legenda atual = ordem de adicao dos traces (POC, VWAP, Entrada, Stop,
#   Alvos, BSL, SSL). Valores misturados, dificulta leitura.
#
# FIX:
#   Coletar todos os niveis horizontais numa lista, ordenar por Y (desc),
#   adicionar em sequencia. Plotly mantem a ordem de adicao na legenda.
#
# Uso:
#   python fix95.py --dry-run
#   python fix95.py
#   python fix95.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ = Path("pages/7.1_📊_SMC_Regras.py")

# Substitui o bloco inteiro dos "Niveis horizontais" (POC/VWAP/Entrada/Stop/
# Alvos/BSL/SSL) por uma versao que coleta + ordena antes de plotar.
ANCORA_ANTIGA = (
    '    if poc and poc > 0:\n'
    '        fig.add_trace(go.Scatter(\n'
    '            x=x_line, y=[poc, poc],\n'
    '            mode="lines",\n'
    '            name=f"POC Ontem ({poc:,.0f})",\n'
    '            line=dict(color="#a855f7", width=2, dash="dot"),\n'
    '            hovertemplate=f"<b>POC Ontem</b><br>{poc:,.0f} pts<extra></extra>",\n'
    '        ))\n'
    '\n'
    '    if vwap and vwap > 0:\n'
    '        fig.add_trace(go.Scatter(\n'
    '            x=x_line, y=[vwap, vwap],\n'
    '            mode="lines",\n'
    '            name=f"VWAP Ontem ({vwap:,.1f})",\n'
    '            line=dict(color="#9ca3af", width=2, dash="dot"),\n'
    '            hovertemplate=f"<b>VWAP Ontem</b><br>{vwap:,.1f} pts<extra></extra>",\n'
    '        ))\n'
    '\n'
    '    if entrada and entrada > 0:\n'
    '        fig.add_trace(go.Scatter(\n'
    '            x=x_line, y=[entrada, entrada],\n'
    '            mode="lines",\n'
    '            name=f"Entrada ({entrada:,.0f})",\n'
    '            line=dict(color="#00d4ff", width=2, dash="dash"),\n'
    '            hovertemplate=f"<b>Entrada</b><br>{entrada:,.0f}<extra></extra>",\n'
    '        ))\n'
    '\n'
    '    if stop and stop > 0:\n'
    '        fig.add_trace(go.Scatter(\n'
    '            x=x_line, y=[stop, stop],\n'
    '            mode="lines",\n'
    '            name=f"Stop ({stop:,.0f})",\n'
    '            line=dict(color="#ff3d00", width=2, dash="dash"),\n'
    '            hovertemplate=f"<b>Stop</b><br>{stop:,.0f}<extra></extra>",\n'
    '        ))\n'
    '\n'
    '    for i, alvo in enumerate(alvos[:2]):\n'
    '        if alvo and alvo > 0:\n'
    '            fig.add_trace(go.Scatter(\n'
    '                x=x_line, y=[alvo, alvo],\n'
    '                mode="lines",\n'
    '                name=f"Alvo {i+1} ({alvo:,.0f})",\n'
    '                line=dict(color="#00ff88", width=1.5, dash="longdash"),\n'
    '                hovertemplate=f"<b>Alvo {i+1}</b><br>{alvo:,.0f}<extra></extra>",\n'
    '            ))\n'
    '\n'
    '    for i, nivel in enumerate(bsl[:3]):\n'
    '        fig.add_trace(go.Scatter(\n'
    '            x=x_line, y=[nivel, nivel],\n'
    '            mode="lines",\n'
    '            name=f"BSL #{i+1} ({nivel:,.0f})",\n'
    '            line=dict(color="#00bfff", width=1, dash="dot"),\n'
    '            opacity=0.6,\n'
    '            hovertemplate=f"<b>BSL</b><br>{nivel:,.0f}<extra></extra>",\n'
    '        ))\n'
    '\n'
    '    for i, nivel in enumerate(ssl[:3]):\n'
    '        fig.add_trace(go.Scatter(\n'
    '            x=x_line, y=[nivel, nivel],\n'
    '            mode="lines",\n'
    '            name=f"SSL #{i+1} ({nivel:,.0f})",\n'
    '            line=dict(color="#ff6b6b", width=1, dash="dot"),\n'
    '            opacity=0.6,\n'
    '            hovertemplate=f"<b>SSL</b><br>{nivel:,.0f}<extra></extra>",\n'
    '        ))'
)

ANCORA_NOVA = (
    '    # fix95: coleta todos os niveis horizontais numa lista, ordena por\n'
    '    # valor DESC, e adiciona em sequencia. Plotly exibe a legenda na\n'
    '    # ordem de adicao — entao ordenar a lista ordena a legenda.\n'
    '    _niveis = []  # (valor_y, label, cor, dash, largura, opacity, tipo_hover)\n'
    '\n'
    '    if poc and poc > 0:\n'
    '        _niveis.append((poc, f"POC Ontem ({poc:,.0f})", "#a855f7", "dot", 2, 1.0, "POC Ontem"))\n'
    '    if vwap and vwap > 0:\n'
    '        _niveis.append((vwap, f"VWAP Ontem ({vwap:,.1f})", "#9ca3af", "dot", 2, 1.0, "VWAP Ontem"))\n'
    '    if entrada and entrada > 0:\n'
    '        _niveis.append((entrada, f"Entrada ({entrada:,.0f})", "#00d4ff", "dash", 2, 1.0, "Entrada"))\n'
    '    if stop and stop > 0:\n'
    '        _niveis.append((stop, f"Stop ({stop:,.0f})", "#ff3d00", "dash", 2, 1.0, "Stop"))\n'
    '    for i, alvo in enumerate(alvos[:2]):\n'
    '        if alvo and alvo > 0:\n'
    '            _niveis.append((alvo, f"Alvo {i+1} ({alvo:,.0f})", "#00ff88", "longdash", 1.5, 1.0, f"Alvo {i+1}"))\n'
    '    for i, nivel in enumerate(bsl[:3]):\n'
    '        _niveis.append((nivel, f"BSL #{i+1} ({nivel:,.0f})", "#00bfff", "dot", 1, 0.6, "BSL"))\n'
    '    for i, nivel in enumerate(ssl[:3]):\n'
    '        _niveis.append((nivel, f"SSL #{i+1} ({nivel:,.0f})", "#ff6b6b", "dot", 1, 0.6, "SSL"))\n'
    '\n'
    '    # Ordena do maior para o menor (decrescente em Y)\n'
    '    _niveis.sort(key=lambda x: -float(x[0]))\n'
    '\n'
    '    for valor, label, cor, dash, largura, opac, tipo in _niveis:\n'
    '        fig.add_trace(go.Scatter(\n'
    '            x=x_line, y=[valor, valor],\n'
    '            mode="lines",\n'
    '            name=label,\n'
    '            line=dict(color=cor, width=largura, dash=dash),\n'
    '            opacity=opac,\n'
    '            hovertemplate=f"<b>{tipo}</b><br>{valor:,.0f}<extra></extra>",\n'
    '        ))'
)

PATCHES = [
    {
        "nome": "ordena_legenda_por_valor",
        "ancora_antiga": ANCORA_ANTIGA,
        "ancora_nova": ANCORA_NOVA,
    },
]


def pre_validar(conteudo):
    for patch in PATCHES:
        n = conteudo.count(patch["ancora_antiga"])
        if n == 0:
            print(f"ABORTADO: ancora nao encontrada: {patch['nome']}")
            print("---primeiras 300 chars---")
            print(patch["ancora_antiga"][:300])
            print("---")
            return False
        if n > 1:
            print(f"ABORTADO: ancora ambigua ({n}x): {patch['nome']}")
            return False
    return True


def aplicar(conteudo):
    for patch in PATCHES:
        conteudo = conteudo.replace(patch["ancora_antiga"], patch["ancora_nova"], 1)
        print(f"OK: patch aplicado: {patch['nome']}")
    return conteudo


def validar_sintaxe(conteudo):
    try:
        compile(conteudo, str(ARQ), "exec")
    except SyntaxError as e:
        print(f"ABORTADO: sintaxe invalida: {e}")
        return False
    print("OK: sintaxe validada")
    return True


def mostrar_diff(antes, depois):
    print("\n--- DRY-RUN: diff (resumido, primeiras 60 linhas) ---")
    linhas = list(difflib.unified_diff(
        antes.splitlines(), depois.splitlines(),
        lineterm="", fromfile="antes", tofile="depois",
    ))
    for linha in linhas[:60]:
        print(linha)
    if len(linhas) > 60:
        print(f"... +{len(linhas) - 60} linhas")
    print("--- DRY-RUN: nada foi salvo ---")


def reverter():
    backups = sorted(ARQ.parent.glob(f"{ARQ.name}.bak_*"))
    if not backups:
        print("ERRO: nenhum backup encontrado")
        sys.exit(1)
    ultimo = backups[-1]
    shutil.copy(ultimo, ARQ)
    print(f"OK: revertido de {ultimo.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    if args.reverter:
        reverter()
        return

    if not ARQ.exists():
        print(f"ERRO: {ARQ} nao encontrado")
        sys.exit(1)

    original = ARQ.read_text(encoding="utf-8")
    if not pre_validar(original):
        sys.exit(1)

    novo = aplicar(original)
    if not validar_sintaxe(novo):
        sys.exit(1)

    if args.dry_run:
        mostrar_diff(original, novo)
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = ARQ.parent / f"{ARQ.name}.bak_{ts}"
    shutil.copy(ARQ, backup)
    print(f"OK: backup={backup.name}")
    ARQ.write_text(novo, encoding="utf-8")
    print(f"OK: {ARQ} atualizado")


if __name__ == "__main__":
    main()