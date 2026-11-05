#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
varrer_except_pass.py — Auditoria de except: pass no projeto (READ-ONLY)

Escaneia todos os arquivos .py do projeto via AST e reporta handlers
silenciosos: `except [Tipo]: pass` e `except [Tipo]: continue`.
Opcionalmente, com --incluir-return-none, também reporta
`except [Tipo]: return None` (pode ser contrato legítimo de API).

Não modifica nada no disco. Seguro para rodar a qualquer momento.

Uso:
    python varrer_except_pass.py
    python varrer_except_pass.py --json
    python varrer_except_pass.py --check
    python varrer_except_pass.py --path .\\pages
    python varrer_except_pass.py --incluir-return-none

Exit codes:
    0 = sem ocorrências (ou só warnings)
    1 = ocorrências encontradas com --check
    2 = erro de execução (caminho inválido)
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

IGNORAR_DIRS = {
    "lixeira_analise",
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
}


def _nome_tipo_exc(handler: ast.ExceptHandler) -> str:
    if handler.type is None:
        return "bare_except"
    try:
        return ast.unparse(handler.type)
    except Exception:
        return "<tipo_desconhecido>"


def _classificar_handler(
    handler: ast.ExceptHandler, incluir_return_none: bool
) -> str | None:
    body = handler.body
    if not body:
        return None

    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return "pass"

    if len(body) == 1 and isinstance(body[0], ast.Continue):
        return "continue"

    if incluir_return_none and len(body) == 1 and isinstance(body[0], ast.Return):
        ret = body[0]
        if ret.value is None or (
            isinstance(ret.value, ast.Constant) and ret.value.value is None
        ):
            return "return_none"

    return None


def _contexto(linhas: list[str], num_linha: int, janela: int = 1) -> str:
    ini = max(0, num_linha - 1 - janela)
    fim = min(len(linhas), num_linha + janela)
    return "\n".join(
        f"    {i + 1:4d} | {linhas[i].rstrip()}"
        for i in range(ini, fim)
    )


def varrer_arquivo(path: Path, incluir_return_none: bool) -> list[dict[str, Any]]:
    try:
        src = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        return [{
            "arquivo": str(path),
            "linha": 0,
            "tipo_exc": "-",
            "categoria": "ERRO_LEITURA",
            "detalhe": f"{type(e).__name__}: {e}",
        }]

    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError as e:
        return [{
            "arquivo": str(path),
            "linha": e.lineno or 0,
            "tipo_exc": "-",
            "categoria": "ERRO_SINTAXE",
            "detalhe": str(e),
        }]

    linhas = src.splitlines()
    achados: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            categoria = _classificar_handler(node, incluir_return_none)
            if categoria is None:
                continue
            achados.append({
                "arquivo": str(path),
                "linha": node.lineno,
                "tipo_exc": _nome_tipo_exc(node),
                "categoria": categoria,
                "contexto": _contexto(linhas, node.lineno),
            })

    return achados


def varrer_projeto(raiz: Path, incluir_return_none: bool) -> list[dict[str, Any]]:
    resultados: list[dict[str, Any]] = []
    for arq in sorted(raiz.rglob("*.py")):
        partes = set(arq.relative_to(raiz).parts[:-1])
        if partes & IGNORAR_DIRS:
            continue
        resultados.extend(varrer_arquivo(arq, incluir_return_none))
    return resultados


def imprimir_relatorio(resultados: list[dict[str, Any]], raiz: Path) -> None:
    print("=" * 72)
    print(" VARREDURA DE except: pass  —  RELATÓRIO (read-only)")
    print("=" * 72)
    print(f" Raiz varrida: {raiz}")
    print()

    if not resultados:
        print(" ✅ Nenhuma ocorrência encontrada.")
        return

    por_arquivo: dict[str, list[dict[str, Any]]] = {}
    por_cat: dict[str, int] = {}
    for r in resultados:
        por_arquivo.setdefault(r["arquivo"], []).append(r)
        por_cat[r["categoria"]] = por_cat.get(r["categoria"], 0) + 1

    print(f" 📊 Total de ocorrências: {len(resultados)}")
    for cat, n in sorted(por_cat.items()):
        print(f"    • {cat:<12} : {n}")
    print()

    for arq, lista in sorted(por_arquivo.items()):
        try:
            rel = arq.replace(str(raiz), ".").lstrip("\\").lstrip("/")
        except Exception:
            rel = arq
        print(f"\n 📄 {rel}  ({len(lista)} ocorrência(s))")
        print("-" * 72)
        for item in sorted(lista, key=lambda x: x["linha"]):
            print(
                f"   linha {item['linha']:>4} | "
                f"{item['tipo_exc']:<22} | {item['categoria']}"
            )
            if "contexto" in item:
                print(item["contexto"])
            if "detalhe" in item:
                print(f"      ↳ {item['detalhe']}")
            print()

    print("=" * 72)


def main() -> int:
    ap = argparse.ArgumentParser(description="Auditoria de except: pass (read-only)")
    ap.add_argument("--json", action="store_true", help="Saída JSON")
    ap.add_argument("--check", action="store_true", help="Exit 1 se encontrar")
    ap.add_argument("--path", type=str, default=None, help="Diretório a varrer")
    ap.add_argument(
        "--incluir-return-none",
        action="store_true",
        help="Também reporta `except: return None` (pode ser falso positivo)",
    )
    args = ap.parse_args()

    raiz = Path(args.path) if args.path else Path(__file__).resolve().parent
    if not raiz.exists():
        print(f"❌ Caminho não existe: {raiz}", file=sys.stderr)
        return 2

    resultados = varrer_projeto(raiz, incluir_return_none=args.incluir_return_none)

    if args.json:
        print(json.dumps(resultados, ensure_ascii=False, indent=2))
    else:
        imprimir_relatorio(resultados, raiz)

    if args.check and resultados:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())