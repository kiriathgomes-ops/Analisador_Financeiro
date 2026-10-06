# -*- coding: utf-8 -*-
# minerador.py — v2: origem com heranca + aliases com nome-similar + output em auditoria/.

import json
import re
import glob
import argparse
import sys
from pathlib import Path
from collections import defaultdict, Counter

RAIZ = Path(__file__).resolve().parent.parent
OUT_DIR = RAIZ / "auditoria"
OUT_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(RAIZ))
from mapear_dados import (
    analisar as analisar_base,
    detectar_anomalias,
    deve_ignorar,
    carregar_tickers,
)

# --- Fontes conhecidas ---
FONTES_CONHECIDAS = {
    "MT5": ["MT5", "mt5", "MetaTrader", "copy_rates"],
    "TRADINGVIEW": ["TRADINGVIEW", "TradingView", "TVC:", "BMFBOVESPA:",
                    "NYSE:", "OTC:", "SGX:", "CME_MINI:", "NYMEX:",
                    "FX_IDC:", "AMEX:"],
    "BRAPI": ["BRAPI", "brapi", "B3_AJUSTE", "B3_FECHAMENTO", "SETTLEMENT"],
    "FINNHUB": ["FINNHUB", "finnhub"],
    "OCR_LEILAO": ["OCR", "leilao", "LEILAO"],
    "BACEN": ["BACEN", "bacen", "SGS", "PTAX"],
    "INTERNO": ["CALCULADO", "INTERNO", "derivado", "SMC"],
}

ALIASES_MANUAIS = {
    "close": ["preco", "fechamento", "last", "ultimo", "fechamento_real"],
    "high": ["maxima", "max", "topo"],
    "low": ["minima", "min", "fundo"],
    "open": ["abertura"],
    "volume": ["vol", "volume_total", "volume_negociado", "session_volume"],
    "change_percent": ["variacao_pct", "var_pct", "variacao_percentual"],
    "previous_close": ["fechamento_anterior", "prev_close"],
    "gap_pontos": ["gap_pts", "gap"],
    "score_magnitude": ["nm_magnitude", "valor", "nm_conf"],
    "score_direcao": ["nm_direcao_score", "direcao"],
}


def _normalizar_fonte(fonte_raw):
    if not fonte_raw:
        return None
    f = str(fonte_raw).upper()
    for canonico, tokens in FONTES_CONHECIDAS.items():
        for t in tokens:
            if t.upper() in f:
                return canonico
    return "DESCONHECIDA"


def _detectar_fonte_por_nome(arq):
    nome = str(arq).lower()
    if "mt5" in nome: return "MT5"
    if "brapi" in nome or "ajuste" in nome: return "BRAPI"
    if "validados" in nome or "unificados" in nome: return "MULTIPLA"
    if "smc" in nome or "grafica" in nome: return "INTERNO"
    if "decisao" in nome or "estimativa" in nome or "metricas" in nome: return "INTERNO"
    if "noticia" in nome: return "FINNHUB"
    if "rom-" in nome or "coleta_rom" in nome: return "MULTIPLA"
    return "DESCONHECIDA"


def inventariar_com_origem():
    """Extrai campos + origem com heranca pai->filho + heuristica por arquivo."""
    campos = defaultdict(lambda: {"arquivos": set(), "origens": set()})

    for arq in glob.glob(f"{RAIZ}/Coletas/**/*.json", recursive=True):
        if deve_ignorar(arq):
            continue
        try:
            d = json.load(open(arq, encoding="utf-8"))
        except Exception:
            continue

        fonte_default = _detectar_fonte_por_nome(arq)
        rel = str(Path(arq).relative_to(RAIZ))

        def walk(obj, fonte_herdada, depth=0):
            if depth > 5:
                return
            if isinstance(obj, dict):
                # `fonte` no proprio dict sobrescreve heranca
                fonte_local = _normalizar_fonte(obj.get("fonte")) or fonte_herdada
                for k, v in obj.items():
                    if k in ("fonte",):
                        continue
                    campos[k]["arquivos"].add(rel)
                    campos[k]["origens"].add(fonte_local or fonte_default)
                    walk(v, fonte_local or fonte_default, depth + 1)
            elif isinstance(obj, list):
                for item in obj[:5]:
                    walk(item, fonte_herdada, depth + 1)

        walk(d, fonte_default)

    return campos


def _nome_similar(a, b):
    """True se nomes tem relacao morfologica."""
    a, b = a.lower(), b.lower()
    if a == b:
        return True
    if len(a) >= 4 and len(b) >= 4 and (a in b or b in a):
        return True
    # Prefixo ou sufixo comum >= 5 chars
    n = min(len(a), len(b))
    for i in range(n, 4, -1):
        if a[:i] == b[:i] or a[-i:] == b[-i:]:
            return True
    return False


def detectar_aliases(campos_json):
    """Aliases com Jaccard >= 0.9 E nome similar."""
    suspeitos = []
    nomes = list(campos_json.keys())
    for i, a in enumerate(nomes):
        for b in nomes[i+1:]:
            arqs_a = campos_json[a]["arquivos"]
            arqs_b = campos_json[b]["arquivos"]
            if not arqs_a or not arqs_b:
                continue
            inter = arqs_a & arqs_b
            uniao = arqs_a | arqs_b
            jaccard = len(inter) / len(uniao) if uniao else 0
            if jaccard >= 0.9 and _nome_similar(a, b):
                suspeitos.append((a, b, round(jaccard, 2)))
    return suspeitos


def gerar_mermaid(campos):
    out = ["```mermaid", "graph LR"]
    origens = set()
    for info in campos.values():
        origens.update(info.get("origens", []))
    for o in sorted(origens):
        out.append(f'  {o}["{o}"]')
    top = sorted([(c, i) for c, i in campos.items() if i["total_leituras"] >= 5],
                 key=lambda x: -x[1]["total_leituras"])[:30]
    for c, info in top:
        safe = re.sub(r'[^a-zA-Z0-9_]', '_', c)
        out.append(f'  {safe}["{c}"]')
        for o in info.get("origens", []):
            out.append(f'  {o} --> {safe}')
    out.append("```")
    return "\n".join(out)


def gerar_markdown(campos, problemas, aliases_est, campo_filtro=None, origem_filtro=None):
    out = ["# ⛏️ Mapa da Mina — Analisador Financeiro", ""]
    out.append(f"**Campos:** {len(campos)} | **Orfaos:** {len(problemas['orfaos'])} | "
               f"**Fantasmas:** {len(problemas['fantasmas'])} | "
               f"**Aliases suspeitos:** {len(aliases_est)}")
    out.append("")

    out.append("## 🔍 Origem dos dados\n")
    por_origem = defaultdict(list)
    for c, info in campos.items():
        for o in info.get("origens", []):
            por_origem[o].append(c)
    for origem, lista in sorted(por_origem.items()):
        out.append(f"### {origem} ({len(lista)} campos)\n")
        for c in sorted(lista)[:25]:
            out.append(f"- `{c}`")
        if len(lista) > 25:
            out.append(f"- ... +{len(lista)-25}")
        out.append("")

    if problemas["orfaos"]:
        out.append("## ⚠️ Orfaos\n")
        for c in problemas["orfaos"][:80]:
            out.append(f"- `{c}`")
        out.append("")

    if problemas["fantasmas"]:
        out.append("## 🚨 Fantasmas\n")
        for c in problemas["fantasmas"][:80]:
            out.append(f"- `{c}`")
        out.append("")

    if aliases_est:
        out.append("## 🕵️ Aliases suspeitos\n")
        for a, b, j in aliases_est[:60]:
            out.append(f"- `{a}` ↔ `{b}` (Jaccard={j})")
        out.append("")

    out.append("---\n## 📋 Inventario\n")
    for campo, info in sorted(campos.items(),
                              key=lambda x: -(x[1]["total_escritas"] + x[1]["total_leituras"])):
        if campo_filtro and campo_filtro not in campo:
            continue
        if origem_filtro and origem_filtro not in info.get("origens", []):
            continue
        out.append(f"### `{campo}`")
        out.append(f"- **Origens:** {', '.join(sorted(info.get('origens', []))) or 'N/A'}")
        out.append(f"- **Escritas:** {info['total_escritas']} | **Leituras:** {info['total_leituras']}")
        if info["em_json"]:
            out.append(f"- **JSONs** ({len(info['em_json'])}):")
            for j in info["em_json"][:4]:
                out.append(f"  - `{j}`")
        out.append("")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campo")
    parser.add_argument("--origem")
    args = parser.parse_args()

    print("===== MINERADOR v2 =====")
    campos = analisar_base()
    anomalias = detectar_anomalias(campos)

    print("[3/4] Origem com heranca + heuristica...")
    campos_orig = inventariar_com_origem()
    for c, info in campos.items():
        info["origens"] = sorted(campos_orig.get(c, {}).get("origens", []) or ["DESCONHECIDA"])

    print("[4/4] Aliases com nome-similar...")
    aliases = detectar_aliases(campos_orig)
    print(f"      {len(aliases)} suspeitos\n")

    problemas = {"orfaos": anomalias["orfaos"], "fantasmas": anomalias["fantasmas"]}

    md = gerar_markdown(campos, problemas, aliases, args.campo, args.origem)
    (OUT_DIR / "mapa_mina.md").write_text(md, encoding="utf-8")
    (OUT_DIR / "mapa_mina.mmd").write_text(gerar_mermaid(campos), encoding="utf-8")
    (OUT_DIR / "mapa_mina.json").write_text(
        json.dumps({"campos": campos, "problemas": problemas, "aliases_estatisticos": aliases},
                   indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")

    print("=" * 60)
    print(f"  Orfaos:              {len(problemas['orfaos'])}")
    print(f"  Fantasmas:           {len(problemas['fantasmas'])}")
    print(f"  Aliases suspeitos:   {len(aliases)}")
    print(f"\n  Output: {OUT_DIR}/")

    if not problemas["orfaos"] and not problemas["fantasmas"]:
        print("\n  ✅ OK — MAPA COMPLETO")


if __name__ == "__main__":
    main()