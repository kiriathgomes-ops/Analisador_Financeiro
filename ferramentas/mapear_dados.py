# -*- coding: utf-8 -*-
# mapear_dados.py — Data lineage: rastreia cada campo desde a coleta ate o consumo.
# v2: output em auditoria/ + filtro de tickers nos orfaos.

import json
import re
import glob
import argparse
import sys
from pathlib import Path
from collections import defaultdict

# --- Paths ---
RAIZ = Path(__file__).resolve().parent.parent
OUT_DIR = RAIZ / "auditoria"
OUT_DIR.mkdir(exist_ok=True)

DIRS_JSON = ["Coletas"]
DIRS_CODIGO = ["."]

IGNORAR_PATH = [
    "__pycache__", ".git", ".bak", "venv", "env",
    "Historico_Decisoes_V2_PRE_FIX66", "Historico_MT5",
    "Historico_Aberturas", "cache", "auditoria",
    "Coleta_rom-", "Coleta_ram",
]

CAMPOS_IGNORAR = {
    "id", "ok", "status", "type", "nome", "name", "value",
    "data", "versao", "versao_coletor",
}

PADROES_CAMADA = {
    "coleta": ["Coletor", "Validador", "coletor_dados", "coleta_"],
    "calculo": ["Calculadora", "Motor_", "motor_", "SMC", "NOVO_MOTOR",
                "Gerar_Resultado", "estimativa", "analisar_"],
    "consumo": ["pages/", "pages\\", "Gerar_Relatorio", "v2_gravar",
                "v2_orchestrator", "prediction_service", "market_service",
                "win_session_builder", "confluence_engine"],
    "auditoria": ["audit_", "analise_", "ver_", "mapear_", "minerador",
                  "_grep", "_check", "fix"],
}


def deve_ignorar(path):
    p = str(path).replace("\\", "/")
    return any(t in p for t in IGNORAR_PATH)


def classificar_camada(path):
    p = str(path).replace("\\", "/")
    for camada, padroes in PADROES_CAMADA.items():
        if any(x in p for x in padroes):
            return camada
    return "outros"


def carregar_tickers():
    """Tickers validos (evitam falso positivo em orfaos)."""
    try:
        sys.path.insert(0, str(RAIZ))
        import config
        return (set(config.MAPEAMENTO_TICKERS.keys())
                | set(config.MAPEAMENTO_TICKERS.values()))
    except Exception:
        return set()


def extrair_campos_json(obj, prefixo="", depth=0):
    if depth > 4:
        return set()
    caminhos = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            caminhos.add(f"{prefixo}.{k}" if prefixo else k)
            caminhos.add(k)
            caminhos.update(extrair_campos_json(v, f"{prefixo}.{k}", depth + 1))
    elif isinstance(obj, list):
        for item in obj[:3]:
            caminhos.update(extrair_campos_json(item, prefixo, depth + 1))
    return caminhos


def inventariar_campos():
    campos = defaultdict(set)
    for arq in glob.glob(f"{RAIZ}/Coletas/**/*.json", recursive=True):
        if deve_ignorar(arq):
            continue
        try:
            d = json.load(open(arq, encoding="utf-8"))
        except Exception:
            continue
        for caminho in extrair_campos_json(d):
            folha = caminho.split(".")[-1]
            if folha in CAMPOS_IGNORAR or len(folha) < 3:
                continue
            campos[folha].add(str(Path(arq).relative_to(RAIZ)))
    return campos


RE_GET = re.compile(r'\.get\(\s*["\']([a-z_][a-z0-9_]{2,})["\']')
RE_ATRIB_ESCRITA = re.compile(r'\[\s*["\']([a-z_][a-z0-9_]{2,})["\']\s*\]\s*=')
RE_DICT_ESCRITA = re.compile(r'["\']([a-z_][a-z0-9_]{2,})["\']\s*:')
RE_DICT_LEITURA = re.compile(r'\[\s*["\']([a-z_][a-z0-9_]{2,})["\']\s*\]')


def rastrear_codigo():
    ocorrencias = defaultdict(list)
    for arq in glob.glob(f"{RAIZ}/**/*.py", recursive=True):
        if deve_ignorar(arq):
            continue
        try:
            linhas = open(arq, encoding="utf-8", errors="ignore").read().splitlines()
        except Exception:
            continue
        for i, linha in enumerate(linhas, 1):
            sem = linha.split("#", 1)[0].strip()
            for m in RE_ATRIB_ESCRITA.finditer(sem):
                c = m.group(1)
                if c not in CAMPOS_IGNORAR:
                    ocorrencias[c].append((arq, i, "escrita", linha.strip()[:140]))
            for m in RE_DICT_ESCRITA.finditer(sem):
                c = m.group(1)
                if c not in CAMPOS_IGNORAR and "==" not in sem:
                    ocorrencias[c].append((arq, i, "escrita", linha.strip()[:140]))
            for m in RE_GET.finditer(sem):
                c = m.group(1)
                if c not in CAMPOS_IGNORAR:
                    ocorrencias[c].append((arq, i, "leitura", linha.strip()[:140]))
            for m in RE_DICT_LEITURA.finditer(sem):
                c = m.group(1)
                if c not in CAMPOS_IGNORAR:
                    ocorrencias[c].append((arq, i, "leitura", linha.strip()[:140]))
    return ocorrencias


def analisar():
    print("[1/2] Inventariando campos...")
    campos_json = inventariar_campos()
    print(f"      {len(campos_json)} campos unicos")

    print("[2/2] Rastreando uso no codigo...")
    usos = rastrear_codigo()
    print(f"      {len(usos)} campos referenciados\n")

    resultado = {}
    for campo in sorted(set(campos_json) | set(usos)):
        ocorr = usos.get(campo, [])
        escritas = [o for o in ocorr if o[2] == "escrita"]
        leituras = [o for o in ocorr if o[2] == "leitura"]
        por_camada = defaultdict(lambda: {"escrita": [], "leitura": []})
        for arq, linha, tipo, texto in ocorr:
            camada = classificar_camada(arq)
            por_camada[camada][tipo].append((str(Path(arq).relative_to(RAIZ)), linha, texto))
        resultado[campo] = {
            "em_json": sorted(campos_json.get(campo, [])),
            "total_escritas": len(escritas),
            "total_leituras": len(leituras),
            "por_camada": {k: dict(v) for k, v in por_camada.items()},
        }
    return resultado


def detectar_anomalias(campos):
    tickers = carregar_tickers()
    orfaos, fantasmas = [], []

    for campo, info in campos.items():
        # fix: campos que sao tickers (chaves de dicionario) nao sao orfaos
        if campo in tickers:
            continue

        em_json = bool(info["em_json"])
        n_esc = info["total_escritas"]
        n_lei = info["total_leituras"]

        if em_json and n_esc == 0 and n_lei == 0:
            orfaos.append(campo)
        if not em_json and n_lei > 0 and n_esc == 0:
            fantasmas.append(campo)

    return {"orfaos": sorted(orfaos), "fantasmas": sorted(fantasmas)}


def gerar_markdown(campos, anomalias, campo_filtro=None, camada_filtro=None):
    out = ["# 🗺️ Mapeamento de Dados — Analisador Financeiro", ""]
    out.append(f"**Campos mapeados:** {len(campos)}")
    out.append(f"**Orfaos:** {len(anomalias['orfaos'])} | **Fantasmas:** {len(anomalias['fantasmas'])}")
    out.append("")
    out.append("---\n")

    if anomalias["orfaos"]:
        out.append("## ⚠️ Campos orfaos (coletados, nunca usados)\n")
        for c in anomalias["orfaos"][:80]:
            out.append(f"- `{c}`")
        out.append("")

    if anomalias["fantasmas"]:
        out.append("## 🚨 Campos fantasmas (lidos, nunca coletados)\n")
        for c in anomalias["fantasmas"][:80]:
            out.append(f"- `{c}`")
        out.append("")

    out.append("---\n")
    out.append("## 📋 Inventario por campo\n")

    for campo, info in sorted(campos.items(),
                              key=lambda x: -(x[1]["total_escritas"] + x[1]["total_leituras"])):
        if campo_filtro and campo_filtro not in campo:
            continue
        out.append(f"### `{campo}`")
        out.append(f"- **Escritas:** {info['total_escritas']} | **Leituras:** {info['total_leituras']}")
        if info["em_json"]:
            out.append(f"- **JSONs** ({len(info['em_json'])}):")
            for j in info["em_json"][:4]:
                out.append(f"  - `{j}`")
        for camada in ["coleta", "calculo", "consumo", "outros"]:
            if camada_filtro and camada != camada_filtro:
                continue
            dados = info["por_camada"].get(camada)
            if not dados:
                continue
            out.append(f"- **{camada.title()}**:")
            for tipo in ["escrita", "leitura"]:
                for arq, linha, _ in dados[tipo][:5]:
                    out.append(f"  - [{tipo}] `{arq}:{linha}`")
        out.append("")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campo")
    parser.add_argument("--camada", choices=["coleta", "calculo", "consumo", "outros"])
    parser.add_argument("--orfaos", action="store_true")
    args = parser.parse_args()

    campos = analisar()
    anomalias = detectar_anomalias(campos)

    if args.orfaos:
        print("=== ORFAOS ===")
        for c in anomalias["orfaos"]:
            print(f"  {c}")
        return

    md = gerar_markdown(campos, anomalias, args.campo, args.camada)
    (OUT_DIR / "relatorio_mapeamento.md").write_text(md, encoding="utf-8")
    (OUT_DIR / "mapeamento_dados.json").write_text(
        json.dumps({"campos": campos, "anomalias": anomalias},
                   indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")

    print("=" * 60)
    print(f"  Campos: {len(campos)} | Orfaos: {len(anomalias['orfaos'])} | Fantasmas: {len(anomalias['fantasmas'])}")
    print(f"  Output: {OUT_DIR}/relatorio_mapeamento.md")


if __name__ == "__main__":
    main()