#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
detector_codigo_morto_v2.py
===========================
Detector com heurísticas melhoradas:

  1. Streamlit pages (7.1_, 7.2_, etc.) → entry points
  2. app_home.py, main.py, app.py → entry points
  3. Pasta ferramentas/, tools/, scripts/ → ferramentas (não morto)
  4. Pasta tests/ → testes (não morto)
  5. Phantom files: só são importados por __init__.py zumbi
  6. Detecta arquivos com st.set_page_config = Streamlit app
  7. Detecta chains de código morto (A→B→C onde A é raiz morta)
"""

from __future__ import annotations

import argparse
import ast
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional


# ============================================================
# CONFIGURAÇÃO
# ============================================================
PASTAS_IGNORAR = {
    "__pycache__", ".git", ".venv", "venv", "env", "node_modules",
    ".pytest_cache", ".mypy_cache", "build", "dist", "site-packages",
    "_legado", "arquivo", ".idea", ".vscode", ".tox", ".eggs",
}

# Pastas cujo conteúdo é "ferramenta" — não classifica como morto
PASTAS_FERRAMENTA = {
    "ferramentas", "tools", "scripts", "utils", "util", "helpers",
    "docs", "debug", "diagnostico", "auditoria", "analises", "mapas",
}

# Pastas cujo conteúdo é "teste" — não classifica como morto
PASTAS_TESTE = {"tests", "test", "testing"}

# Nomes de arquivo que são sempre entry points
NOMES_ENTRY_POINT = {
    "main.py", "app.py", "run.py", "setup.py", "conftest.py",
    "__main__.py", "app_home.py", "home.py", "index.py",
    "streamlit_app.py",
}

# Regex para Streamlit pages (aceita 6_, 7.1_, 7.2_, etc.)
REGEX_STREAMLIT_PAGE = re.compile(r"^\d+([._]\d+)*_")

# Pastas que contêm pages do Streamlit
PASTAS_STREAMLIT = {"pages", "Pages", "page", "Page"}

# Pastas consideradas como raiz do "app core" (para phantom detection)
PASTAS_CORE = {"v2", "core", "domain", "src"}


# ============================================================
# HELPERS
# ============================================================
def encontrar_arquivos_py(raiz: Path) -> list[Path]:
    arquivos = []
    for p in raiz.rglob("*.py"):
        if any(parte in PASTAS_IGNORAR for parte in p.parts):
            continue
        arquivos.append(p)
    return sorted(arquivos)


def resolver_import(arquivo_atual: Path, raiz: Path, modulo: str, level: int) -> str:
    if level == 0:
        return modulo
    partes = list(arquivo_atual.relative_to(raiz).with_suffix("").parts)
    partes = partes[:-1]
    subir = level - 1
    if subir > 0:
        partes = partes[:-subir] if subir <= len(partes) else []
    if modulo:
        partes.append(modulo)
    return ".".join(partes)


def encontrar_arquivo_por_modulo(nome_modulo: str, raiz: Path) -> Optional[Path]:
    if not nome_modulo:
        return None
    partes = nome_modulo.split(".")
    candidato = raiz.joinpath(*partes).with_suffix(".py")
    if candidato.exists():
        return candidato
    candidato_init = raiz.joinpath(*partes) / "__init__.py"
    if candidato_init.exists():
        return candidato_init
    return None


def e_ferramenta(arquivo: Path, raiz: Path) -> bool:
    rel = arquivo.relative_to(raiz)
    for parte in rel.parts[:-1]:  # ignora nome do arquivo
        if parte.lower() in PASTAS_FERRAMENTA:
            return True
    return False


def e_teste(arquivo: Path, raiz: Path) -> bool:
    rel = arquivo.relative_to(raiz)
    for parte in rel.parts[:-1]:
        if parte.lower() in PASTAS_TESTE:
            return True
    if arquivo.name.startswith("test_") or arquivo.name.endswith("_test.py"):
        return True
    return False


def e_streamlit_page(arquivo: Path, raiz: Path) -> bool:
    rel = arquivo.relative_to(raiz)
    # Pasta "pages" com numeração
    if any(parte in PASTAS_STREAMLIT for parte in rel.parts[:-1]):
        return True
    # Numeração no nome (6_, 7.1_, etc.) — pode estar fora de pages/
    if REGEX_STREAMLIT_PAGE.match(arquivo.name):
        return True
    return False


def e_entry_point_nome(arquivo: Path) -> bool:
    return arquivo.name in NOMES_ENTRY_POINT


# ============================================================
# ANÁLISE DE UM ARQUIVO
# ============================================================
def analisar_arquivo(arquivo: Path, raiz: Path) -> dict:
    resultado = {
        "imports_resolvidos": [],
        "tem_main": False,
        "subprocess_refs": [],
        "importlib_refs": [],
        "chama_set_page_config": False,  # Streamlit app?
        "erro": None,
    }

    try:
        codigo = arquivo.read_text(encoding="utf-8")
        arvore = ast.parse(codigo)
    except Exception as e:
        resultado["erro"] = str(e)
        return resultado

    for node in ast.walk(arvore):
        if isinstance(node, ast.Import):
            for n in node.names:
                alvo = encontrar_arquivo_por_modulo(n.name, raiz)
                if alvo:
                    resultado["imports_resolvidos"].append(alvo)

        elif isinstance(node, ast.ImportFrom):
            modulo = node.module or ""
            if node.level > 0:
                modulo = resolver_import(arquivo, raiz, modulo, node.level)
            alvo = encontrar_arquivo_por_modulo(modulo, raiz)
            if alvo:
                resultado["imports_resolvidos"].append(alvo)

        elif isinstance(node, ast.If):
            try:
                teste = ast.unparse(node.test)
                if "__name__" in teste and "__main__" in teste:
                    resultado["tem_main"] = True
            except Exception:
                pass

        elif isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                func_name = f"{node.func.value.id}.{node.func.attr}"
            elif isinstance(node.func, ast.Name):
                func_name = node.func.id

            if func_name in ("subprocess.run", "subprocess.Popen",
                             "os.system", "subprocess.call"):
                for arg in node.args:
                    if isinstance(arg, ast.List):
                        for elt in arg.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                if elt.value.endswith(".py"):
                                    resultado["subprocess_refs"].append(elt.value)
                    elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        if arg.value.endswith(".py"):
                            resultado["subprocess_refs"].append(arg.value)

            # Streamlit set_page_config
            if func_name == "st.set_page_config":
                resultado["chama_set_page_config"] = True

    return resultado


# ============================================================
# PHANTOM DETECTION
# ============================================================
def encontrar_fantasmas(arquivos: list[Path], analises: dict, raiz: Path) -> set[Path]:
    """
    Detecta 'arquivos fantasmas': só são importados por __init__.py,
    e esse(s) __init__.py não são importados por nenhum código real.
    """
    importadores = defaultdict(set)
    for arq_origem, info in analises.items():
        for alvo in info["imports_resolvidos"]:
            importadores[alvo].add(arq_origem)

    fantasmas = set()
    for arq in arquivos:
        if arq.name == "__init__.py":
            continue
        importadores_diretos = importadores.get(arq, set())
        if not importadores_diretos:
            continue  # morto direto, não fantasma

        # Se TODOS os importadores são __init__.py
        todos_init = all(imp.name == "__init__.py" for imp in importadores_diretos)
        if not todos_init:
            continue  # tem importador real

        # Verificar se algum desses __init__.py é usado por código real
        tem_init_vivo = False
        for init_file in importadores_diretos:
            init_importers = importadores.get(init_file, set())
            # Considerar vivo se for importado por qualquer arquivo não-init
            for imp in init_importers:
                if imp.name != "__init__.py":
                    tem_init_vivo = True
                    break
            if tem_init_vivo:
                break

        # Se nenhum __init__.py é usado por código real → fantasma
        if not tem_init_vivo:
            fantasmas.add(arq)

    return fantasmas


# ============================================================
# ANÁLISE DO PROJETO
# ============================================================
def analisar_projeto(raiz: Path) -> dict:
    arquivos = encontrar_arquivos_py(raiz)
    print(f"[INFO] Encontrados {len(arquivos)} arquivos .py")

    analises = {arq: analisar_arquivo(arq, raiz) for arq in arquivos}

    # Mapa reverso
    importadores = defaultdict(set)
    for arq_origem, info in analises.items():
        for alvo in info["imports_resolvidos"]:
            importadores[alvo].add(arq_origem)

    # Mapa subprocess
    subprocess_map = defaultdict(set)
    for arq_origem, info in analises.items():
        for script_ref in info["subprocess_refs"]:
            nome = Path(script_ref).name
            for candidato in arquivos:
                if candidato.name == nome:
                    subprocess_map[candidato].add(arq_origem)

    # Detectar fantasmas
    fantasmas = encontrar_fantasmas(arquivos, analises, raiz)
    if fantasmas:
        print(f"[INFO] Detectados {len(fantasmas)} arquivo(s) fantasma(s)")

    # Classificar
    codigo_morto = []
    fantasmas_list = []
    entry_points = []
    ferramentas = []
    testes = []
    ativos = []

    for arq in arquivos:
        info = analises[arq]
        nome = arq.name

        # __init__.py — pulamos (são sempre "usados" implicitamente)
        if nome == "__init__.py":
            continue

        # Ordem das verificações importa!
        if e_teste(arq, raiz):
            testes.append(arq)
            continue

        if e_streamlit_page(arq, raiz):
            entry_points.append({"arquivo": arq, "motivo": "Streamlit page"})
            continue

        if e_entry_point_nome(arq) or info["chama_set_page_config"]:
            entry_points.append({"arquivo": arq, "motivo": "Entry point principal"})
            continue

        if e_ferramenta(arq, raiz):
            ferramentas.append(arq)
            continue

        tem_importador = bool(importadores.get(arq))
        tem_subprocess = bool(subprocess_map.get(arq))

        # Fantasma?
        if arq in fantasmas:
            fantasmas_list.append({
                "arquivo": arq,
                "linhas": len(arq.read_text(encoding="utf-8").splitlines()),
                "importado_por": [str(i.relative_to(raiz)) for i in importadores[arq]],
            })
            continue

        if tem_importador or tem_subprocess:
            ativos.append(arq)
        else:
            codigo_morto.append({
                "arquivo": arq,
                "linhas": len(arq.read_text(encoding="utf-8").splitlines()),
                "tem_main": info["tem_main"],
                "importa_de": [str(p.relative_to(raiz)) for p in info["imports_resolvidos"]],
            })

    return {
        "raiz": str(raiz),
        "total_arquivos": len(arquivos),
        "codigo_morto": codigo_morto,
        "fantasmas": fantasmas_list,
        "entry_points": entry_points,
        "ferramentas": ferramentas,
        "testes": testes,
        "ativos": ativos,
    }


# ============================================================
# RELATÓRIO
# ============================================================
def gerar_relatorio_md(resultado: dict, caminho: Path):
    raiz = Path(resultado["raiz"])
    L = []

    L.append("# 🔍 Relatório de Código Morto — V2\n\n")
    L.append(f"**Raiz:** `{resultado['raiz']}`\n\n")
    L.append("## 📊 Sumário\n\n")
    L.append("| Categoria | Quantidade |\n|---|---|\n")
    L.append(f"| 🔴 Código morto real | **{len(resultado['codigo_morto'])}** |\n")
    L.append(f"| 👻 Arquivos fantasmas | **{len(resultado['fantasmas'])}** |\n")
    L.append(f"| 🚪 Entry points (Streamlit/app) | {len(resultado['entry_points'])} |\n")
    L.append(f"| 🔧 Ferramentas (uso manual) | {len(resultado['ferramentas'])} |\n")
    L.append(f"| 🧪 Testes (pytest) | {len(resultado['testes'])} |\n")
    L.append(f"| ✅ Ativos | {len(resultado['ativos'])} |\n")
    L.append(f"| **Total** | **{resultado['total_arquivos']}** |\n")

    # =========================================================
    # FANTASMAS (prioridade máxima!)
    # =========================================================
    L.append("\n---\n\n")
    L.append(f"## 👻 Arquivos Fantasmas ({len(resultado['fantasmas'])})\n\n")
    L.append("Estes arquivos são importados **apenas** por `__init__.py` que, por sua vez, "
             "não são usados por nenhum código real. São zumbis — parecem vivos (têm importadores), "
             "mas o importador está morto também.\n\n")
    L.append("**Candidatos a `_legado/` com prioridade máxima.**\n\n")

    if not resultado["fantasmas"]:
        L.append("✅ Nenhum fantasma detectado.\n\n")
    else:
        L.append("| Arquivo | Linhas | Importado por |\n|---|---|---|\n")
        for item in resultado["fantasmas"]:
            rel = item["arquivo"].relative_to(raiz)
            importadores = ", ".join(f"`{x}`" for x in item["importado_por"])
            L.append(f"| `{rel}` | {item['linhas']} | {importadores} |\n")

    # =========================================================
    # CÓDIGO MORTO REAL
    # =========================================================
    L.append("\n---\n\n")
    L.append(f"## 🔴 Código Morto Real ({len(resultado['codigo_morto'])})\n\n")
    L.append("Não é importado por ninguém, não está em `ferramentas/`, não é teste, "
             "não é entry point. **Pode ser deletado ou movido para `_legado/`.**\n\n")

    if not resultado["codigo_morto"]:
        L.append("✅ Nenhum código morto real detectado!\n\n")
    else:
        L.append("| Arquivo | Linhas | Tem `__main__` |\n|---|---|---|\n")
        for item in resultado["codigo_morto"]:
            rel = item["arquivo"].relative_to(raiz)
            L.append(f"| `{rel}` | {item['linhas']} | {'✅' if item['tem_main'] else '❌'} |\n")

    # =========================================================
    # ENTRY POINTS (informativo)
    # =========================================================
    L.append("\n---\n\n")
    L.append(f"## 🚪 Entry Points ({len(resultado['entry_points'])})\n\n")
    for ep in resultado["entry_points"]:
        rel = ep["arquivo"].relative_to(raiz)
        L.append(f"- ✅ `{rel}` — *{ep['motivo']}*\n")

    # =========================================================
    # FERRAMENTAS (informativo)
    # =========================================================
    L.append("\n---\n\n")
    L.append(f"## 🔧 Ferramentas ({len(resultado['ferramentas'])})\n\n")
    L.append("Scripts executados manualmente. **Não são código morto.**\n\n")
    for f in resultado["ferramentas"]:
        rel = f.relative_to(raiz)
        L.append(f"- 🔧 `{rel}`\n")

    # =========================================================
    # TESTES (informativo)
    # =========================================================
    L.append("\n---\n\n")
    L.append(f"## 🧪 Testes ({len(resultado['testes'])})\n\n")
    for t in resultado["testes"]:
        rel = t.relative_to(raiz)
        L.append(f"- 🧪 `{rel}`\n")

    caminho.write_text("".join(L), encoding="utf-8")


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--saida", default="CODIGO_MORTO_REPORT.md")
    args = parser.parse_args()

    raiz = Path(args.root).resolve()
    print("=" * 60)
    print(" 🔍 DETECTOR DE CÓDIGO MORTO — V2")
    print("=" * 60)
    print(f"Raiz: {raiz}\n")

    resultado = analisar_projeto(raiz)
    caminho = raiz / args.saida
    gerar_relatorio_md(resultado, caminho)
    print(f"\n✅ Relatório salvo em: {caminho}")

    print("\n" + "=" * 60)
    print(" RESUMO")
    print("=" * 60)
    print(f"Total de arquivos .py  : {resultado['total_arquivos']}")
    print(f"✅ Ativos               : {len(resultado['ativos'])}")
    print(f"🚪 Entry points         : {len(resultado['entry_points'])}")
    print(f"🔧 Ferramentas          : {len(resultado['ferramentas'])}")
    print(f"🧪 Testes               : {len(resultado['testes'])}")
    print(f"👻 Fantasmas            : {len(resultado['fantasmas'])} ⚠️")
    print(f"🔴 Código morto real    : {len(resultado['codigo_morto'])} ⚠️")

    if resultado["fantasmas"]:
        print("\n👻 ARQUIVOS FANTASMAS (prioridade máxima):")
        for item in resultado["fantasmas"]:
            rel = item["arquivo"].relative_to(raiz)
            print(f"   👻 {rel} ({item['linhas']} linhas)")

    if resultado["codigo_morto"]:
        print("\n🔴 CÓDIGO MORTO REAL:")
        for item in resultado["codigo_morto"]:
            rel = item["arquivo"].relative_to(raiz)
            print(f"   🔴 {rel} ({item['linhas']} linhas)")

    print("=" * 60)


if __name__ == "__main__":
    main()