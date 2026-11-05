#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
detector_codigo_morto_v3.py
===========================
Análise de ALCANCE (reachability): parte dos entry points reais e propaga
pelos imports. O que não for alcançável = código morto.

Correções vs V2:
  1. Qualquer arquivo NA RAIZ com __main__ = entry point
  2. Qualquer arquivo começando com _ com __main__ = ferramenta
  3. main_pipeline.py, Agendador.py, sniper, etc. = entry points
  4. Detecção de fantasmas por ALCANCE, não por "tem importador"
  5. Detecta arquivos "ativos-mas-fantasmas" (só são carregados via __init__)

Uso:
    python detector_codigo_morto_v3.py
"""

from __future__ import annotations
import argparse
import ast
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Optional

# ============================================================
PASTAS_IGNORAR = {
    "__pycache__", ".git", ".venv", "venv", "env", "node_modules",
    ".pytest_cache", ".mypy_cache", "build", "dist", "site-packages",
    "_legado", "arquivo", ".idea", ".vscode", ".tox", ".eggs",
}

NOMES_ENTRY_POINT_RAIZ = {
    "main.py", "app.py", "run.py", "setup.py", "conftest.py",
    "__main__.py", "app_home.py", "home.py", "index.py",
    "streamlit_app.py", "main_pipeline.py", "agendador.py",
    "win_abertura_sniper.py", "win_abertura.py",
}

REGEX_STREAMLIT_PAGE = re.compile(r"^\d+([._]\d+)*_")
PASTAS_STREAMLIT = {"pages", "page", "Pages", "Page"}
PASTAS_FERRAMENTA = {
    "ferramentas", "tools", "scripts", "helpers", "docs",
    "debug", "diagnostico", "auditoria", "analises", "mapas",
}
PASTAS_TESTE = {"tests", "test", "testing"}


# ============================================================
def encontrar_arquivos(raiz: Path) -> list[Path]:
    out = []
    for p in raiz.rglob("*.py"):
        if any(parte in PASTAS_IGNORAR for parte in p.parts):
            continue
        out.append(p)
    return sorted(out)


def resolver_modulo(arquivo: Path, raiz: Path, modulo: str, level: int) -> str:
    if level == 0:
        return modulo
    partes = list(arquivo.relative_to(raiz).with_suffix("").parts)[:-1]
    subir = level - 1
    if subir > 0:
        partes = partes[:-subir] if subir <= len(partes) else []
    if modulo:
        partes.append(modulo)
    return ".".join(partes)


def resolver_arquivo(modulo: str, raiz: Path) -> Optional[Path]:
    if not modulo:
        return None
    partes = modulo.split(".")
    p = raiz.joinpath(*partes).with_suffix(".py")
    if p.exists():
        return p
    p_init = raiz.joinpath(*partes) / "__init__.py"
    if p_init.exists():
        return p_init
    return None


# ============================================================
def analisar_arquivo(arq: Path, raiz: Path) -> dict:
    r = {
        "imports": [],
        "tem_main": False,
        "chama_set_page_config": False,
        "erro": None,
    }
    try:
        arvore = ast.parse(arq.read_text(encoding="utf-8"))
    except Exception as e:
        r["erro"] = str(e)
        return r

    for node in ast.walk(arvore):
        if isinstance(node, ast.Import):
            for n in node.names:
                alvo = resolver_arquivo(n.name, raiz)
                if alvo:
                    r["imports"].append(alvo)
        elif isinstance(node, ast.ImportFrom):
            modulo = node.module or ""
            if node.level > 0:
                modulo = resolver_modulo(arq, raiz, modulo, node.level)
            alvo = resolver_arquivo(modulo, raiz)
            if alvo:
                r["imports"].append(alvo)
        elif isinstance(node, ast.If):
            try:
                t = ast.unparse(node.test)
                if "__name__" in t and "__main__" in t:
                    r["tem_main"] = True
            except Exception:
                pass
        elif isinstance(node, ast.Call):
            fn = ""
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                fn = f"{node.func.value.id}.{node.func.attr}"
            if fn == "st.set_page_config":
                r["chama_set_page_config"] = True
    return r


# ============================================================
def classificar_entry_point(arq: Path, info: dict, raiz: Path) -> Optional[str]:
    """Retorna motivo do entry point ou None."""
    rel = arq.relative_to(raiz)
    nome = arq.name

    if nome == "__init__.py":
        return None

    # 1. Streamlit page (7.1_, 6_, etc.) — em qualquer lugar
    if REGEX_STREAMLIT_PAGE.match(nome):
        return "Streamlit page"

    # 2. Pasta pages/
    if any(p in PASTAS_STREAMLIT for p in rel.parts[:-1]):
        return "Streamlit page (pasta)"

    # 3. Nome explícito de entry point (mesmo em subpastas)
    if nome.lower() in NOMES_ENTRY_POINT_RAIZ:
        return "Entry point (nome)"

    # 4. Arquivo NA RAIZ com __main__ = script principal
    if len(rel.parts) == 1 and info["tem_main"]:
        return "Script raiz com __main__"

    # 5. Arquivo começando com _ com __main__ = ferramenta interna
    if nome.startswith("_") and info["tem_main"]:
        return "Ferramenta interna (_*.py com __main__)"

    # 6. Streamlit app via st.set_page_config
    if info["chama_set_page_config"]:
        return "Streamlit app (set_page_config)"

    return None


def e_ferramenta(arq: Path, raiz: Path) -> bool:
    rel = arq.relative_to(raiz)
    return any(p.lower() in PASTAS_FERRAMENTA for p in rel.parts[:-1])


def e_teste(arq: Path, raiz: Path) -> bool:
    rel = arq.relative_to(raiz)
    if any(p.lower() in PASTAS_TESTE for p in rel.parts[:-1]):
        return True
    return arq.name.startswith("test_") or arq.name.endswith("_test.py")


# ============================================================
def alcancaveis_de(raizes_alcance: set[Path], analises: dict, raiz: Path) -> set[Path]:
    """
    BFS simulado — considera que importar um submodulo carrega também
    todos os __init__.py dos pacotes pais.
    """
    visitados: set[Path] = set()
    fila = deque(raizes_alcance)

    def _marcar_pacotes_pais(arquivo: Path):
        """Adiciona __init__.py dos pacotes pais ao BFS."""
        try:
            rel = arquivo.relative_to(raiz)
        except ValueError:
            return
        for i in range(1, len(rel.parts)):
            pasta = raiz.joinpath(*rel.parts[:i])
            init = pasta / "__init__.py"
            if init.exists() and init != arquivo and init not in visitados:
                fila.append(init)

    while fila:
        atual = fila.popleft()
        if atual in visitados:
            continue
        visitados.add(atual)

        # Se importamos esse arquivo, carregamos também os __init__.py pais
        _marcar_pacotes_pais(atual)

        info = analises.get(atual)
        if not info:
            continue
        for dep in info["imports"]:
            if dep not in visitados:
                fila.append(dep)

    return visitados


# ============================================================
def analisar_projeto(raiz: Path) -> dict:
    arquivos = encontrar_arquivos(raiz)
    print(f"[INFO] {len(arquivos)} arquivos .py")

    analises = {a: analisar_arquivo(a, raiz) for a in arquivos}

    # 1. Identificar entry points + ferramentas + testes
    entry_points: dict[Path, str] = {}
    ferramentas: list[Path] = []
    testes: list[Path] = []

    for arq in arquivos:
        info = analises[arq]
        if arq.name == "__init__.py":
            continue
        if e_teste(arq, raiz):
            testes.append(arq)
            continue
        motivo = classificar_entry_point(arq, info, raiz)
        if motivo:
            entry_points[arq] = motivo
            continue
        if e_ferramenta(arq, raiz):
            ferramentas.append(arq)

    # 2. Raízes de alcance = entry points + ferramentas + testes
    raizes_alcance = set(entry_points.keys()) | set(ferramentas) | set(testes)
    print(f"[INFO] {len(raizes_alcance)} raízes de alcance")

    # 3. BFS
    alcancaveis = alcancaveis_de(raizes_alcance, analises, raiz)
    print(f"[INFO] {len(alcancaveis)} arquivos alcançáveis")

    # 4. Quem não foi alcançado = suspeito
    nao_alcancados = [a for a in arquivos if a not in alcancaveis and a.name != "__init__.py"]

    # 5. Separar em "mortos" vs "fantasmas"
    #   Morto total: ninguém importa E ele não importa ninguém
    #   Fantasma:     alguém importa (mas o importador está morto)
    importadores = defaultdict(set)
    for origem, info in analises.items():
        for dep in info["imports"]:
            importadores[dep].add(origem)

    codigo_morto_real = []
    fantasmas = []

    for arq in nao_alcancados:
        info = analises[arq]
        linhas = len(arq.read_text(encoding="utf-8").splitlines())
        imps = importadores.get(arq, set())
        # Filtrar quem importa: excluir __init__.py
        imps_nao_init = [i for i in imps if i.name != "__init__.py"]
        if imps_nao_init:
            # Tem importadores reais (mas eles estão mortos) → fantasma
            fantasmas.append({
                "arquivo": arq, "linhas": linhas,
                "importado_por": [str(i.relative_to(raiz)) for i in imps],
            })
        else:
            codigo_morto_real.append({
                "arquivo": arq, "linhas": linhas,
                "tem_main": info["tem_main"],
            })

    return {
        "raiz": str(raiz),
        "total": len(arquivos),
        "entry_points": entry_points,
        "ferramentas": ferramentas,
        "testes": testes,
        "alcancaveis": [a for a in alcancaveis if a.name != "__init__.py"],
        "codigo_morto_real": codigo_morto_real,
        "fantasmas": fantasmas,
    }


# ============================================================
def gerar_relatorio(r: dict, caminho: Path):
    raiz = Path(r["raiz"])
    L = []
    L.append("# 🔍 Relatório de Código Morto — V3 (Alcance)\n\n")
    L.append(f"**Raiz:** `{r['raiz']}`\n\n")
    L.append("## 📊 Sumário\n\n")
    L.append("| Categoria | Quantidade |\n|---|---|\n")
    L.append(f"| ✅ Ativos (alcançáveis) | {len(r['alcancaveis'])} |\n")
    L.append(f"| 🚪 Entry points | {len(r['entry_points'])} |\n")
    L.append(f"| 🔧 Ferramentas | {len(r['ferramentas'])} |\n")
    L.append(f"| 🧪 Testes | {len(r['testes'])} |\n")
    L.append(f"| 👻 Fantasmas | **{len(r['fantasmas'])}** |\n")
    L.append(f"| 🔴 Código morto real | **{len(r['codigo_morto_real'])}** |\n")

    # Fantasmas
    L.append("\n---\n\n")
    L.append(f"## 👻 Fantasmas ({len(r['fantasmas'])})\n\n")
    L.append("**São carregados (via imports) mas nunca alcançados a partir dos entry points.**\n\n")
    L.append("Candidatos a `_legado/`.\n\n")
    if r["fantasmas"]:
        L.append("| Arquivo | Linhas | Importadores |\n|---|---|---|\n")
        for f in r["fantasmas"]:
            rel = f["arquivo"].relative_to(raiz)
            imps = ", ".join(f"`{i}`" for i in f["importado_por"]) or "—"
            L.append(f"| `{rel}` | {f['linhas']} | {imps} |\n")
    else:
        L.append("✅ Nenhum fantasma detectado.\n\n")

    # Mortos reais
    L.append("\n---\n\n")
    L.append(f"## 🔴 Código Morto Real ({len(r['codigo_morto_real'])})\n\n")
    L.append("**Ninguém importa, não são entry points, não são ferramentas.**\n\n")
    if r["codigo_morto_real"]:
        L.append("| Arquivo | Linhas | `__main__` |\n|---|---|---|\n")
        for c in r["codigo_morto_real"]:
            rel = c["arquivo"].relative_to(raiz)
            L.append(f"| `{rel}` | {c['linhas']} | {'✅' if c['tem_main'] else '❌'} |\n")
    else:
        L.append("✅ Nenhum código morto real!\n\n")

    # Entry points
    L.append("\n---\n\n")
    L.append(f"## 🚪 Entry Points ({len(r['entry_points'])})\n\n")
    for arq, motivo in sorted(r["entry_points"].items()):
        rel = arq.relative_to(raiz)
        L.append(f"- ✅ `{rel}` — *{motivo}*\n")

    caminho.write_text("".join(L), encoding="utf-8")


# ============================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--saida", default="CODIGO_MORTO_REPORT_V3.md")
    args = ap.parse_args()

    raiz = Path(args.root).resolve()
    print("=" * 60)
    print(" 🔍 DETECTOR V3 — Análise de Alcance")
    print("=" * 60)
    print(f"Raiz: {raiz}\n")

    r = analisar_projeto(raiz)
    saida = raiz / args.saida
    gerar_relatorio(r, saida)

    print(f"\n✅ Relatório: {saida}")
    print("\n" + "=" * 60)
    print(" RESUMO")
    print("=" * 60)
    print(f"Total                : {r['total']}")
    print(f"✅ Ativos             : {len(r['alcancaveis'])}")
    print(f"🚪 Entry points       : {len(r['entry_points'])}")
    print(f"🔧 Ferramentas        : {len(r['ferramentas'])}")
    print(f"🧪 Testes             : {len(r['testes'])}")
    print(f"👻 Fantasmas          : {len(r['fantasmas'])} ⚠️")
    print(f"🔴 Código morto real  : {len(r['codigo_morto_real'])} ⚠️")

    if r["fantasmas"]:
        print("\n👻 FANTASMAS:")
        for f in r["fantasmas"]:
            rel = f["arquivo"].relative_to(raiz)
            print(f"   👻 {rel} ({f['linhas']} linhas)")

    if r["codigo_morto_real"]:
        print("\n🔴 CÓDIGO MORTO REAL:")
        for c in r["codigo_morto_real"]:
            rel = c["arquivo"].relative_to(raiz)
            print(f"   🔴 {rel} ({c['linhas']} linhas)")


if __name__ == "__main__":
    main()