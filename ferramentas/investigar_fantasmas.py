# -*- coding: utf-8 -*-
# investigar_fantasmas.py — v5: classificacao com whitelist API + analise de fluxo.
#
# Mudancas v5 (sobre v4):
#   - Whitelist manual de campos API conhecidos (Finnhub/brapi/MT5/TV)
#   - Janela de contexto de 20 linhas (era 15)
#   - Deteccao melhor de fallback legado
#
# Classificacoes:
#   TYPO_REAL        - LE sem nenhuma ESCRITA (bug silencioso)
#   FALLBACK_LEGADO  - LE apenas em cadeia de fallback (nao e bug)
#   CODIGO_MORTO     - Dentro de if FLAG_SEMPRE_FALSE
#   API_EXTERNA      - LE de resposta HTTP (whitelist + heuristica)
#   OK_AMBOS         - Tem escrita e leitura (falso positivo do detector)
#   NAO_ENCONTRADO   - Nao aparece no codigo
#   INDEFINIDO       - Nao classificavel automaticamente

import json
import re
import glob
import sys
from pathlib import Path
from collections import defaultdict

RAIZ = Path(__file__).resolve().parent.parent
OUT_DIR = RAIZ / "auditoria"

IGNORAR = [
    "__pycache__", ".git", ".bak", "Historico_",
    "auditoria", "ferramentas",
    "fix", "_grep", "_valida", "_check", "analise_",
    "verificar_", "buscar_", "ver_fantasmas", "investigar_",
    "rastrear_", "debug_", "mapear_", "minerador",
]

FLAGS_MORTAS = [
    "ENGINE_VIES_COMO_FALLBACK",
    "USE_LEGACY",
    "ENABLE_OLD",
]

MARCADORES_API = [
    "requests.get", "requests.post", "_HTTP.get", "_HTTP.post",
    "urllib.request", "urlopen", "json.loads(", ".json()",
    "requests.get(", "response.json", "res.json",
    "mt5.symbol_info", "mt5.copy_rates", "mt5.symbol_info_tick",
    "finnhub.io", "brapi.dev",
]

# Whitelist manual — campos que sao de resposta API
# (evita falsos positivos que a heuristica de janela nao pega)
CAMPOS_API_CONHECIDOS = {
    # Finnhub (quote endpoint)
    "actual", "country", "forecast", "importance", "previous",
    "datetime", "symbol", "title",
    # brapi (quote endpoint)
    "average", "settlement", "real_volume", "quotes", "change",
    # MT5
    "tick_volume",
    # TV scanner
    "change_abs",
    # Noticias / calendario
    "impacto", "relevancia",
}

# Whitelist de nomes conhecidamente legitimos (mesmo sem escrita visivel)
CAMPOS_LEGITIMOS = {
    "abertura",
    "analise_operacional",  # agora catalogado como codigo morto
    "estimativas_abertura",
}


def deve_ignorar(path):
    p = str(path).replace("\\", "/")
    return any(t in p for t in IGNORAR)


def procurar_em_projeto(campo):
    ocorrencias = []
    padroes = [
        re.compile(rf'\.get\(\s*["\']({re.escape(campo)})["\']'),
        re.compile(rf'\[\s*["\']({re.escape(campo)})["\']'),
        re.compile(rf'["\']({re.escape(campo)})["\']\s*:'),
    ]
    for arq in glob.glob(f"{RAIZ}/**/*.py", recursive=True):
        if deve_ignorar(arq):
            continue
        try:
            linhas = open(arq, encoding="utf-8", errors="ignore").read().splitlines()
        except Exception:
            continue
        for i, linha in enumerate(linhas, 1):
            sem = linha.split("#", 1)[0]
            for pat in padroes:
                if pat.search(sem):
                    ini = max(0, i - 20)
                    contexto = "\n".join(linhas[ini:i])
                    ocorrencias.append({
                        "arquivo": str(Path(arq).relative_to(RAIZ)),
                        "linha": i,
                        "texto": linha.strip()[:180],
                        "contexto": contexto,
                    })
                    break
    return ocorrencias


def classificar(oc):
    texto = oc["texto"]
    contexto = oc["contexto"]
    campo = oc.get("campo", "")

    # 0. Whitelist manual de API (maior prioridade)
    if campo in CAMPOS_API_CONHECIDOS:
        return "api"

    # 1. API externa (janela 20 linhas)
    for m in MARCADORES_API:
        if m in contexto:
            return "api"

    # 2. Codigo morto
    for flag in FLAGS_MORTAS:
        if f"if {flag}" in contexto:
            return "morto"

    # 3. Dataclass field: "    campo: tipo = ..." ou "    campo: tipo"
    if re.match(rf'^\s*{re.escape(campo)}\s*:\s*\w', texto):
        return "escrita"

    # 4. Attr assign: "obj.campo = ..."
    if re.search(rf'\.{re.escape(campo)}\s*=\s*[^=]', texto):
        return "escrita"

    # 5. Dict literal (escrita): '"campo":'
    if re.search(rf'["\']{re.escape(campo)}["\']\s*:', texto):
        return "escrita"

    # 6. Dict assign: ["campo"] =
    if re.search(rf'\[\s*["\']{re.escape(campo)}["\']\s*\]\s*=', texto):
        return "escrita"

    # 7. Fallback legado
    if " or " in texto:
        pos_or = texto.find(" or ")
        pos_campo = texto.find(f'"{campo}"')
        if pos_campo < 0:
            pos_campo = texto.find(f"'{campo}'")
        if pos_or >= 0 and pos_campo > pos_or:
            return "fallback"

    # 8. Leitura
    if ".get(" in texto or re.search(r'\[\s*["\']', texto):
        return "leitura"

    return "indefinido"


def classificar_campo(campo):
    ocorrencias = procurar_em_projeto(campo)
    for oc in ocorrencias:
        oc["campo"] = campo
        oc["tipo_detectado"] = classificar(oc)

    if not ocorrencias:
        return "NAO_ENCONTRADO", ocorrencias

    tipos = [oc["tipo_detectado"] for oc in ocorrencias]
    tem_escrita = "escrita" in tipos
    tem_leitura = "leitura" in tipos
    tem_fallback = "fallback" in tipos
    tem_morto = "morto" in tipos
    tem_api = "api" in tipos

    if tem_escrita:
        return "OK_AMBOS", ocorrencias
    if tem_morto and not tem_leitura:
        return "CODIGO_MORTO", ocorrencias
    if tem_api and not tem_leitura:
        return "API_EXTERNA", ocorrencias
    if tem_fallback and not tem_leitura:
        return "FALLBACK_LEGADO", ocorrencias
    if tem_leitura:
        return "TYPO_REAL", ocorrencias
    return "INDEFINIDO", ocorrencias


def main():
    mapa_path = OUT_DIR / "mapa_mina.json"
    if not mapa_path.exists():
        print(f"ERRO: {mapa_path} nao existe. Roda minerador.py antes.")
        sys.exit(1)

    d = json.load(open(mapa_path, encoding="utf-8"))
    fantasmas = d["problemas"]["fantasmas"]
    print(f"Investigando {len(fantasmas)} fantasmas (v5)...\n")

    resultado = defaultdict(list)
    detalhes = {}

    for i, campo in enumerate(fantasmas, 1):
        status, oc = classificar_campo(campo)
        resultado[status].append(campo)
        detalhes[campo] = {"status": status, "ocorrencias": oc}

    out = ["# 🔍 Investigacao de Fantasmas (v5)", ""]
    out.append(f"Total: {len(fantasmas)} campos")
    out.append("")
    for status in ["TYPO_REAL", "FALLBACK_LEGADO", "CODIGO_MORTO",
                   "API_EXTERNA", "OK_AMBOS", "INDEFINIDO", "NAO_ENCONTRADO"]:
        lista = resultado.get(status, [])
        if not lista:
            continue
        out.append(f"## {status} ({len(lista)})")
        out.append("")
        for c in lista:
            out.append(f"### `{c}`")
            for oc in detalhes[c]["ocorrencias"][:5]:
                out.append(f"- `{oc['arquivo']}:{oc['linha']}` ({oc.get('tipo_detectado', '?')}) → `{oc['texto'][:120]}`")
            out.append("")

    (OUT_DIR / "relatorio_fantasmas.md").write_text("\n".join(out), encoding="utf-8")
    (OUT_DIR / "relatorio_fantasmas.json").write_text(
        json.dumps({"resultado": dict(resultado), "detalhes": detalhes},
                   indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")

    print("=" * 60)
    print(" RESULTADO v5")
    print("=" * 60)
    for status in ["TYPO_REAL", "FALLBACK_LEGADO", "CODIGO_MORTO",
                   "API_EXTERNA", "OK_AMBOS", "INDEFINIDO", "NAO_ENCONTRADO"]:
        lista = resultado.get(status, [])
        if lista:
            print(f"  {status:<20}: {len(lista):>3}")

    if resultado.get("TYPO_REAL"):
        print()
        print("=" * 60)
        print(" BUGS SILENCIOSOS REAIS (TYPO_REAL)")
        print("=" * 60)
        for c in resultado["TYPO_REAL"]:
            print(f"  {c}")


if __name__ == "__main__":
    main()