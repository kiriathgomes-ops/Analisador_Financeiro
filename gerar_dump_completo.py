# -*- coding: utf-8 -*-
"""
gerar_dump_completo.py - Gera um .md por categoria (pasta de 1o nivel) do
projeto, contendo a arvore da categoria + conteudo integral de cada arquivo
de texto (codigo, config, etc).

Uso:
    python gerar_dump_completo.py

Saida:
    docs/dump_completo/<categoria>.md   - um arquivo por pasta de 1o nivel
    docs/dump_completo/_raiz.md         - arquivos soltos na raiz do projeto

Nunca inclui: .env, .git, __pycache__, venv/.venv, backups (*bak*), docs/.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "docs" / "dump_completo"

IGNORAR_DIRS = {
    ".git", "__pycache__", "lixeira_analise", ".venv", "venv",
    "node_modules", ".pytest_cache", ".mypy_cache", ".idea", ".vscode",
    "docs", "dump_completo",
}

IGNORAR_ARQUIVOS_EXATOS = {".env"}

# Padroes de nome ignorados (case-insensitive), casados com "in"
IGNORAR_PADROES_NOME = ("bak", ".bak_")

EXT_TEXTO = {".py", ".md", ".toml", ".cfg", ".ini", ".json", ".txt"}

# Pastas onde so entra o arquivo mais recente (evita dump gigante)
PASTAS_COMPACTAS_PREFIXOS = (
    "Coletas/Historico_Decisoes_V2",
    "Coletas/Historico_MT5",
)


def _e_pasta_compacta(rel: str) -> bool:
    for pref in PASTAS_COMPACTAS_PREFIXOS:
        if rel == pref or rel.startswith(pref + "/"):
            return True
    return False


def _ignorar_dir(path: Path) -> bool:
    try:
        rel = path.relative_to(RAIZ).as_posix()
    except ValueError:
        return False
    parts = rel.split("/")
    return any(p in IGNORAR_DIRS for p in parts)


def _ignorar_arquivo(path: Path) -> bool:
    if _ignorar_dir(path.parent):
        return True
    nome_lower = path.name.lower()
    if path.name in IGNORAR_ARQUIVOS_EXATOS:
        return True
    if any(pad in nome_lower for pad in IGNORAR_PADROES_NOME):
        return True
    if path.name.startswith(".") and path.name not in (".gitignore",):
        return True
    return False


def _listar_arquivos(base: Path) -> list[Path]:
    """Lista recursivamente arquivos de texto validos dentro de base.

    Pastas marcadas como compactas (PASTAS_COMPACTAS_PREFIXOS) so contribuem
    com o arquivo mais recente (por mtime).
    """
    candidatos = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        if _ignorar_arquivo(p):
            continue
        if p.suffix.lower() not in EXT_TEXTO:
            continue
        candidatos.append(p)

    resultado = []
    compactos_por_pasta: dict[str, list[Path]] = {}

    for p in candidatos:
        rel_pasta = p.parent.relative_to(RAIZ).as_posix()
        if _e_pasta_compacta(rel_pasta):
            compactos_por_pasta.setdefault(rel_pasta, []).append(p)
        else:
            resultado.append(p)

    for rel_pasta, arquivos in compactos_por_pasta.items():
        try:
            mais_recente = max(arquivos, key=lambda p: p.stat().st_mtime)
        except (PermissionError, FileNotFoundError):
            mais_recente = arquivos[0]
        resultado.append(mais_recente)

    return resultado


def _arvore_categoria(base: Path, arquivos: list[Path]) -> str:
    """Desenha arvore simples baseada na lista de arquivos ja filtrada."""
    linhas = ["```"]
    linhas.append(base.name if base != RAIZ else ".")
    rels = sorted(a.relative_to(base).as_posix() for a in arquivos)
    for i, rel in enumerate(rels):
        ultimo = i == len(rels) - 1
        conector = "`-- " if ultimo else "|-- "
        linhas.append(f"{conector}{rel}")
    linhas.append("```")
    return "\n".join(linhas)


def _bloco_arquivo(path_rel: str, conteudo: str, ext: str) -> str:
    lang = {"py": "python", "md": "markdown", "json": "json",
            "toml": "toml", "cfg": "ini", "ini": "ini", "txt": "text"}.get(ext.lstrip("."), "")
    return (
        f"### `{path_rel}`\n\n"
        f"```{lang}\n{conteudo}\n```\n"
    )


def gerar_categoria(nome_categoria: str, base: Path, arquivos: list[Path]) -> str:
    linhas = [f"# Dump completo - {nome_categoria}", ""]
    linhas.append(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    linhas.append(f"Total de arquivos: {len(arquivos)}")
    linhas.append("")
    linhas.append("## Arvore")
    linhas.append("")
    linhas.append(_arvore_categoria(base, arquivos))
    linhas.append("")
    linhas.append("## Conteudo dos arquivos")
    linhas.append("")

    for arq in sorted(arquivos, key=lambda p: p.relative_to(RAIZ).as_posix()):
        rel = arq.relative_to(RAIZ).as_posix()
        try:
            conteudo = arq.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            conteudo = f"[ERRO AO LER ARQUIVO: {e}]"
        linhas.append(_bloco_arquivo(rel, conteudo, arq.suffix))

    return "\n".join(linhas)


def main() -> int:
    SAIDA.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(" GERADOR DE DUMP COMPLETO POR CATEGORIA")
    print("=" * 60)

    # Categorias = pastas de 1o nivel (nao ignoradas)
    categorias = [
        p for p in sorted(RAIZ.iterdir())
        if p.is_dir() and not _ignorar_dir(p)
    ]

    total_geral = 0

    # Raiz (arquivos soltos, sem subpasta)
    arquivos_raiz = [
        p for p in RAIZ.iterdir()
        if p.is_file() and not _ignorar_arquivo(p) and p.suffix.lower() in EXT_TEXTO
    ]
    if arquivos_raiz:
        conteudo = gerar_categoria("_raiz", RAIZ, arquivos_raiz)
        out = SAIDA / "_raiz.md"
        out.write_text(conteudo, encoding="utf-8")
        print(f"-> {out} ({len(arquivos_raiz)} arquivos)")
        total_geral += len(arquivos_raiz)

    for cat in categorias:
        arquivos = _listar_arquivos(cat)
        if not arquivos:
            continue
        conteudo = gerar_categoria(cat.name, cat, arquivos)
        out = SAIDA / f"{cat.name}.md"
        out.write_text(conteudo, encoding="utf-8")
        print(f"-> {out} ({len(arquivos)} arquivos)")
        total_geral += len(arquivos)

    print()
    print(f"Total de arquivos processados: {total_geral}")
    print("=" * 60)
    print(" CONCLUIDO")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
