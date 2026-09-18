# -*- coding: utf-8 -*-
"""
Módulo: Gerar_Mapa_Arquivos_OK.py
Versão: 3.0 — Anti-truncamento + Streaming + Relatório

Objetivo:
  1. Mapear a árvore de arquivos/pastas (com filtros de exclusão).
  2. Dump seletivo do conteúdo, com:
     - Limite de tamanho por arquivo
     - Limite total de output
     - Leitura em streaming (chunks)
     - Relatório final do que foi pulado

Uso:
  python Gerar_Mapa_Arquivos_OK.py

Saída:
  consolidado_projeto.txt
"""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Tuple


# ============================================================
# ⚙️ CONFIGURAÇÃO — AJUSTE AQUI
# ============================================================
CONFIG = {
    # Limites de segurança
    "tamanho_max_mb": 1.0,       # Pula arquivo individual > X MB
    "limite_total_mb": 50.0,     # Para o dump após Y MB totais
    "chunk_size": 64 * 1024,     # 64 KB por leitura (streaming)

    # Arquivos de saída
    "pasta_alvo": ".",
    "arquivo_saida": "consolidado_projeto.txt",

    # Extensões que entram no dump
    "extensoes_permitidas": [
        ".py",
        ".txt",
        ".yaml", ".yml",
        ".toml", ".cfg", ".ini",
        ".css", ".html", ".js",
        ".bat", ".ps1", ".sh",
    ],

    # Padrões de exclusão (árvore + dump)
    "excluir": [
        # ---- Sistema / ambiente ----
        ".git", ".gitignore",
        ".env", ".env.*",
        "__pycache__", "*.pyc", "*.pyo", "*.pyd",
        ".venv", "venv", "env",
        ".vscode", ".idea",
        ".mypy_cache", ".pytest_cache", ".ruff_cache",
        "node_modules",
        ".DS_Store",
        "*.egg-info",
        "build", "dist",

        # ---- Documentação ----
        "*.md",

        # ---- Dados pesados (NÃO dumpar) ----
        "Coletas/*.json",
        "Coletas/*.csv",
        "Coletas/*.png",
        "Coletas/*.jpg",
        "Coletas/ArquivosApp.py",        # gerado automaticamente
        "Coletas/App_Completo.*",        # gerado automaticamente
        "Coletas/Historico*",
        "*_rom*.json",
        "Historico*",
        "*Historico*",

        # ---- Mídias e logs ----
        "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.ico",
        "*.log",
        "consolidado_*.txt",

        # ---- Backups / duplicatas ----
        "* copy.py", "* copy 2.py", "* copy *.py",
        "*_old*", "*_backup*",
    ],
}


# ============================================================
# 📊 ESTRUTURAS DE RESULTADO
# ============================================================
@dataclass
class RelatorioDump:
    dumpados: List[str] = field(default_factory=list)
    pulados_tamanho: List[Tuple[str, float]] = field(default_factory=list)
    pulados_limite: List[Tuple[str, float]] = field(default_factory=list)
    erros: List[Tuple[str, str]] = field(default_factory=list)
    total_mb: float = 0.0

    def resumo(self) -> str:
        linhas = [
            "=" * 60,
            "     RELATÓRIO DE GERAÇÃO",
            "=" * 60,
            f"✅ Arquivos dumpados:            {len(self.dumpados)}",
            f"⏭️  Pulados (tamanho > limite): {len(self.pulados_tamanho)}",
            f"⏭️  Pulados (limite total):     {len(self.pulados_limite)}",
            f"❌ Erros de leitura:            {len(self.erros)}",
            f"📦 Total escrito:               {self.total_mb:.2f} MB",
        ]

        if self.pulados_tamanho:
            linhas.append("\n--- Pulados por tamanho ---")
            for rel, mb in self.pulados_tamanho:
                linhas.append(f"  • {rel} ({mb:.2f} MB)")

        if self.pulados_limite:
            linhas.append("\n--- Pulados por limite total ---")
            for rel, mb in self.pulados_limite:
                linhas.append(f"  • {rel} ({mb:.2f} MB)")

        if self.erros:
            linhas.append("\n--- Erros de leitura ---")
            for rel, msg in self.erros:
                linhas.append(f"  • {rel}: {msg}")

        linhas.append("=" * 60)
        return "\n".join(linhas)


# ============================================================
# 🔍 FILTRO DE EXCLUSÃO
# ============================================================
def deve_ignorar(
    caminho_relativo: str,
    nome_item: str,
    lista_ignorar: Iterable[str],
) -> bool:
    """
    Retorna True se o item deve ser ignorado.

    Regras (em ordem de prioridade):
      1. Match exato pelo NOME (ex: '__pycache__', '*.pyc')
      2. Match exato pelo CAMINHO relativo (ex: 'Coletas/ArquivosApp.py')
      3. Match por PADRÃO DE PASTA (ex: 'Coletas/*.json' → só afeta itens dentro de Coletas/)
    """
    caminho_norm = caminho_relativo.replace("\\", "/")
    nome_lower = nome_item.lower()
    caminho_lower = caminho_norm.lower()

    for padrao in lista_ignorar:
        padrao_norm = padrao.strip("/").strip("\\").lower()

        if not padrao_norm:
            continue

        # 1) Match pelo nome do item (ex: *.pyc, __pycache__)
        if fnmatch.fnmatch(nome_lower, padrao_norm):
            return True

        # 2) Match pelo caminho relativo inteiro (ex: Coletas/ArquivosApp.py)
        if fnmatch.fnmatch(caminho_lower, padrao_norm):
            return True

        # 3) Match por prefixo de pasta (ex: 'Coletas/*.json' → 'Coletas/foo.json')
        #    Só aplica quando o padrão contém '/' (senão vira filtro global perigoso)
        if "/" in padrao_norm:
            if fnmatch.fnmatch(caminho_lower, padrao_norm):
                return True

    return False


# ============================================================
# 🌳 GERAÇÃO DA ÁRVORE
# ============================================================
def gerar_arvore(
    diretorio: str,
    prefixo: str = "",
    caminho_base: Optional[str] = None,
    lista_ignorar: Optional[List[str]] = None,
) -> List[str]:
    """Gera representação textual da árvore, respeitando os filtros."""
    if caminho_base is None:
        caminho_base = diretorio
    if lista_ignorar is None:
        lista_ignorar = []

    linhas: List[str] = []

    try:
        elementos = sorted(os.listdir(diretorio))
    except PermissionError:
        return [f"{prefixo}[Acesso Negado]"]
    except OSError as e:
        return [f"{prefixo}[Erro: {e}]"]

    # Filtra ANTES de contar — pra o '└── ' ficar correto no último visível
    elementos = [
        e for e in elementos
        if not deve_ignorar(
            os.path.relpath(os.path.join(diretorio, e), caminho_base),
            e,
            lista_ignorar,
        )
    ]

    total = len(elementos)

    for i, elemento in enumerate(elementos):
        caminho_completo = os.path.join(diretorio, elemento)
        eh_ultimo = (i == total - 1)
        ramo = "└── " if eh_ultimo else "├── "

        linhas.append(f"{prefixo}{ramo}{elemento}")

        if os.path.isdir(caminho_completo):
            ext_prefixo = "    " if eh_ultimo else "│   "
            linhas.extend(
                gerar_arvore(
                    caminho_completo,
                    prefixo + ext_prefixo,
                    caminho_base,
                    lista_ignorar,
                )
            )

    return linhas


# ============================================================
# 📝 DUMP DE ARQUIVO (STREAMING)
# ============================================================
def dump_arquivo(
    f_out,
    caminho_completo: str,
    caminho_relativo: str,
    chunk_size: int,
    tamanho_mb: float,
) -> Tuple[bool, float, Optional[str]]:
    """
    Copia o conteúdo do arquivo para f_out em chunks.

    Retorna:
      (sucesso, mb_escrito, erro_msg)
    """
    try:
        mb_escrito = 0.0
        with open(caminho_completo, "r", encoding="utf-8", errors="replace") as f_in:
            while True:
                chunk = f_in.read(chunk_size)
                if not chunk:
                    break
                f_out.write(chunk)
                mb_escrito += len(chunk.encode("utf-8")) / (1024 * 1024)

        # Garante quebra de linha final
        f_out.write("\n\n")
        return True, mb_escrito, None

    except Exception as e:
        return False, 0.0, str(e)


def escrever_cabecalho_arquivo(f_out, caminho_relativo: str) -> None:
    f_out.write("=" * 60 + "\n")
    f_out.write(f"ARQUIVO: {caminho_relativo}\n")
    f_out.write("=" * 60 + "\n\n")


# ============================================================
# 🎯 CONSOLIDAÇÃO PRINCIPAL
# ============================================================
def consolidar_arquivos(
    diretorio_raiz: str,
    arquivo_saida: str,
    ignorar: List[str],
    extensoes_permitidas: Optional[List[str]] = None,
    tamanho_max_mb: float = 1.0,
    limite_total_mb: float = 50.0,
    chunk_size: int = 64 * 1024,
) -> RelatorioDump:
    """Consolida árvore + dump, com limites e relatório."""

    caminho_raiz = os.path.abspath(diretorio_raiz)
    arquivo_saida_abs = os.path.abspath(arquivo_saida)
    relatorio = RelatorioDump()

    with open(arquivo_saida, "w", encoding="utf-8") as f_out:

        # ----------------------------------------------------
        # ETAPA 1 — ÁRVORE
        # ----------------------------------------------------
        f_out.write("=" * 60 + "\n")
        f_out.write("     MAPA DA ÁRVORE DE ARQUIVOS (FILTRADO)\n")
        f_out.write("=" * 60 + "\n")
        f_out.write(f"{os.path.basename(caminho_raiz)}/\n\n")

        linhas_arvore = gerar_arvore(
            caminho_raiz, caminho_base=caminho_raiz, lista_ignorar=ignorar
        )
        f_out.write("\n".join(linhas_arvore))
        f_out.write("\n\n" + "=" * 60 + "\n\n")

        # ----------------------------------------------------
        # ETAPA 2 — DUMP
        # ----------------------------------------------------
        f_out.write("=" * 60 + "\n")
        f_out.write("     DUMP DO CONTEÚDO DOS ARQUIVOS\n")
        f_out.write(f"     Limite por arquivo : {tamanho_max_mb:.1f} MB\n")
        f_out.write(f"     Limite total       : {limite_total_mb:.1f} MB\n")
        f_out.write("=" * 60 + "\n\n")

        for raiz, pastas, arquivos in os.walk(caminho_raiz):
            rel_raiz = os.path.relpath(raiz, caminho_raiz)

            # Poda subpastas indesejadas ANTES de descer
            pastas[:] = [
                p for p in pastas
                if not deve_ignorar(os.path.join(rel_raiz, p), p, ignorar)
            ]

            for arquivo in sorted(arquivos):
                caminho_completo = os.path.join(raiz, arquivo)
                caminho_relativo = os.path.relpath(caminho_completo, caminho_raiz)

                # Não dumpar o próprio arquivo de saída
                if os.path.abspath(caminho_completo) == arquivo_saida_abs:
                    continue

                # Filtro de exclusão
                if deve_ignorar(caminho_relativo, arquivo, ignorar):
                    continue

                # Filtro de extensão
                if extensoes_permitidas:
                    if not any(arquivo.lower().endswith(ext.lower()) for ext in extensoes_permitidas):
                        continue

                # Tamanho do arquivo
                try:
                    tamanho_mb = os.path.getsize(caminho_completo) / (1024 * 1024)
                except OSError:
                    continue

                # Limite por arquivo
                if tamanho_mb > tamanho_max_mb:
                    relatorio.pulados_tamanho.append((caminho_relativo, tamanho_mb))
                    escrever_cabecalho_arquivo(f_out, caminho_relativo)
                    f_out.write(
                        f"[PULADO: {tamanho_mb:.2f} MB > limite {tamanho_max_mb:.1f} MB]\n\n"
                    )
                    continue

                # Limite total
                if relatorio.total_mb >= limite_total_mb:
                    relatorio.pulados_limite.append((caminho_relativo, tamanho_mb))
                    continue

                # Dump
                escrever_cabecalho_arquivo(f_out, caminho_relativo)
                sucesso, mb_escrito, erro = dump_arquivo(
                    f_out, caminho_completo, caminho_relativo, chunk_size, tamanho_mb
                )

                if sucesso:
                    relatorio.dumpados.append(caminho_relativo)
                    relatorio.total_mb += mb_escrito
                else:
                    relatorio.erros.append((caminho_relativo, erro or "erro desconhecido"))
                    f_out.write(f"[ERRO AO LER: {erro}]\n\n")

        # ----------------------------------------------------
        # ETAPA 3 — RELATÓRIO
        # ----------------------------------------------------
        f_out.write("\n\n")
        f_out.write(relatorio.resumo())

    return relatorio


# ============================================================
# 🚀 EXECUÇÃO
# ============================================================
if __name__ == "__main__":
    cfg = CONFIG

    print("=" * 60)
    print(" GERADOR DE MAPA DE ARQUIVOS — v3.0")
    print("=" * 60)
    print(f" Pasta alvo      : {os.path.abspath(cfg['pasta_alvo'])}")
    print(f" Arquivo saída   : {cfg['arquivo_saida']}")
    print(f" Limite/arquivo  : {cfg['tamanho_max_mb']} MB")
    print(f" Limite total    : {cfg['limite_total_mb']} MB")
    print("=" * 60)

    relatorio = consolidar_arquivos(
        diretorio_raiz=cfg["pasta_alvo"],
        arquivo_saida=cfg["arquivo_saida"],
        ignorar=cfg["excluir"],
        extensoes_permitidas=cfg["extensoes_permitidas"],
        tamanho_max_mb=cfg["tamanho_max_mb"],
        limite_total_mb=cfg["limite_total_mb"],
        chunk_size=cfg["chunk_size"],
    )

    print("\n" + relatorio.resumo())
    print(f"\n✅ Concluído: {cfg['arquivo_saida']}")