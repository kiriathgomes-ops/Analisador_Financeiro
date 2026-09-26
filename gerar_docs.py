# -*- coding: utf-8 -*-
"""
gerar_docs.py - Gera docs/arvore.md e docs/inventario.md a partir do disco

Uso:
    python gerar_docs.py

Saida:
    docs/arvore.md       - estrutura de diretorios (arvore)
    docs/inventario.md   - tabela de todos os .py (path, linhas, bytes, mtime)

Sempre roda a partir da raiz do projeto (onde este arquivo esta).
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DOCS = RAIZ / "docs"

# Diretorios ignorados (checados em QUALQUER nivel do path)
IGNORAR_DIRS = {
    ".git", "__pycache__", "lixeira_analise", ".venv", "venv",
    "node_modules", ".pytest_cache", ".mypy_cache", ".idea", ".vscode",
}

# Caminhos relativos a ignorar (com / no meio)
IGNORAR_CAMINHOS = {
    "Coletas/cache/_arquivo",
}

# Pastas onde listamos so o arquivo mais recente (evita poluir a arvore)
# Prefixos onde listamos so o arquivo mais recente
PASTAS_COMPACTAS_PREFIXOS = (
    "Coletas/Historico_",
    "Coletas/coleta_preco_teorico_historico",
    "Coletas/cache",
)


def _e_pasta_compacta(rel_base: str) -> bool:
    if not rel_base:
        return False
    for pref in PASTAS_COMPACTAS_PREFIXOS:
        if rel_base == pref or rel_base.startswith(pref):
            return True
    return False

# Extensoes consideradas no inventario
EXT_INVENTARIO = {".py"}


def _ignorar(path: Path) -> bool:
    """True se o path (ou qualquer ancestral) deve ser ignorado."""
    try:
        rel = path.relative_to(RAIZ).as_posix()
    except ValueError:
        return False

    # Ignora por componente exato (pega qualquer nivel)
    parts = rel.split("/")
    for ig in IGNORAR_DIRS:
        if ig in parts:
            return True

    # Ignora caminhos especificos (com /)
    for ig in IGNORAR_CAMINHOS:
        if rel == ig or rel.startswith(ig + "/"):
            return True

    return False


def _walk_dir(base: Path):
    """Itera arquivos e subdirs de base, respeitando IGNORAR_DIRS."""
    try:
        entries = sorted(base.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return
    for p in entries:
        if _ignorar(p):
            continue
        if p.name.startswith(".") and p.name not in (".gitignore", ".env.example"):
            continue
        yield p


def gerar_arvore() -> str:
    linhas = ["# Arvore de Arquivos", ""]
    linhas.append(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    linhas.append("")
    linhas.append("```")
    linhas.append(".")
    _arvore_rec(RAIZ, "", linhas)
    linhas.append("```")
    return "\n".join(linhas)


def _arvore_rec(base: Path, prefixo: str, linhas: list):
    """Recursao pra desenhar arvore. Pastas em PASTAS_COMPACTAS so mostram
    o arquivo mais recente + contador."""
    try:
        rel_base = base.relative_to(RAIZ).as_posix() if base != RAIZ else ""
    except ValueError:
        rel_base = ""

    compacto = _e_pasta_compacta(rel_base)

    if compacto:
        # So lista arquivos (ignora subdirs)
        try:
            arquivos = [p for p in base.iterdir() if p.is_file() and not _ignorar(p)]
        except (PermissionError, FileNotFoundError):
            arquivos = []

        if arquivos:
            try:
                mais_recente = max(arquivos, key=lambda p: p.stat().st_mtime)
            except (PermissionError, FileNotFoundError):
                mais_recente = arquivos[0]

            outros = len(arquivos) - 1
            linhas.append(f"{prefixo}`-- {mais_recente.name}")
            if outros > 0:
                linhas.append(f"{prefixo}    (+{outros} arquivos semelhantes)")
        return

    filhos = list(_walk_dir(base))
    for i, p in enumerate(filhos):
        ultimo = i == len(filhos) - 1
        conector = "`-- " if ultimo else "|-- "
        linhas.append(f"{prefixo}{conector}{p.name}")

        if p.is_dir():
            novo_prefixo = prefixo + ("    " if ultimo else "|   ")
            _arvore_rec(p, novo_prefixo, linhas)


def gerar_inventario() -> str:
    linhas = ["# Inventario de Arquivos", ""]
    linhas.append(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    linhas.append("")

    # Coleta
    itens = []
    for arq in RAIZ.rglob("*"):
        if not arq.is_file():
            continue
        if _ignorar(arq):
            continue
        if arq.suffix.lower() not in EXT_INVENTARIO:
            continue
        if arq.name == "gerar_docs.py":
            continue

        try:
            st = arq.stat()
            with arq.open("r", encoding="utf-8", errors="ignore") as f:
                linhas_arq = sum(1 for _ in f)
        except Exception:
            continue

        itens.append({
            "path": arq.relative_to(RAIZ).as_posix(),
            "linhas": linhas_arq,
            "bytes": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
        })

    itens.sort(key=lambda x: x["path"])

    # Resumo
    total_arq = len(itens)
    total_linhas = sum(i["linhas"] for i in itens)
    total_bytes = sum(i["bytes"] for i in itens)

    linhas.append(f"**Total:** {total_arq} arquivos .py | "
                  f"{total_linhas:,} linhas | {total_bytes:,} bytes")
    linhas.append("")

    # Distribuicao por pasta top-level
    por_pasta = {}
    for it in itens:
        parts = it["path"].split("/")
        pasta = parts[0] if len(parts) > 1 else "(raiz)"
        por_pasta.setdefault(pasta, {"n": 0, "linhas": 0})
        por_pasta[pasta]["n"] += 1
        por_pasta[pasta]["linhas"] += it["linhas"]

    linhas.append("## Distribuicao por pasta")
    linhas.append("")
    linhas.append("| Pasta | Arquivos | Linhas |")
    linhas.append("|---|---:|---:|")
    for pasta in sorted(por_pasta.keys()):
        d = por_pasta[pasta]
        linhas.append(f"| `{pasta}` | {d['n']} | {d['linhas']:,} |")
    linhas.append("")

    # Tabela completa
    linhas.append("## Inventario completo")
    linhas.append("")
    linhas.append("| Path | Linhas | Bytes | Ultima mod. |")
    linhas.append("|---|---:|---:|---|")
    for it in itens:
        linhas.append(f"| `{it['path']}` | {it['linhas']:,} | {it['bytes']:,} | {it['mtime']} |")

    return "\n".join(linhas)


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(" GERADOR DE DOCS")
    print("=" * 60)

    print("\n-> Gerando arvore...")
    arvore = gerar_arvore()
    out_arvore = DOCS / "arvore.md"
    out_arvore.write_text(arvore, encoding="utf-8")
    print(f"   [OK] {out_arvore} ({len(arvore):,} chars)")

    print("\n-> Gerando inventario...")
    inventario = gerar_inventario()
    out_inventario = DOCS / "inventario.md"
    out_inventario.write_text(inventario, encoding="utf-8")
    print(f"   [OK] {out_inventario} ({len(inventario):,} chars)")

    print()
    print("=" * 60)
    print(" CONCLUIDO")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())