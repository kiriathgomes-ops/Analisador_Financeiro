#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
varrer_tudo_spike.py — Auditoria read-only TOTAL da pasta Coletas.
Mapeia todos os JSON, CSV e TXT disponíveis para alimentar o contexto do Spike.
"""

import json
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
COLETAS_DIR = BASE_DIR / "Coletas"
LIMITE_PREVIEW_LISTA = 2  # Quantos itens mostrar de uma lista/dict

def _resumir_valor(val):
    """Resume um valor de JSON para não imprimir 500 linhas."""
    if isinstance(val, dict):
        chaves = list(val.keys())
        preview = ", ".join(chaves[:5])
        if len(chaves) > 5:
            preview += "..."
        return f"dict({len(val)} chaves: {preview})"
    elif isinstance(val, list):
        if not val:
            return "list(0 itens)"
        primeiro = str(val[0])
        if len(primeiro) > 60: primeiro = primeiro[:60] + "..."
        return f"list({len(val)} itens, ex: {primeiro})"
    elif isinstance(val, str):
        if len(val) > 60: return val[:60] + "..."
        return val
    else:
        return str(val)

def ler_json(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            dados = json.load(f)
        print(f"  📄 {path.name} ({path.stat().st_size/1024:.1f} KB)")
        
        if isinstance(dados, dict):
            for k, v in dados.items():
                print(f"     └─ {k}: {_resumir_valor(v)}")
        elif isinstance(dados, list):
            print(f"     └─ [Lista com {len(dados)} itens]")
            if dados:
                print(f"        Exemplo do item [0]: {_resumir_valor(dados[0])}")
    except Exception as e:
        print(f"  ⚠️ Erro lendo JSON {path.name}: {e}")

def ler_csv(path: Path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            linhas = f.readlines()
        print(f"  📄 {path.name} ({path.stat().st_size/1024:.1f} KB, {len(linhas)} linhas)")
        if linhas:
            print(f"     └─ Cabeçalho: {linhas[0].strip()}")
            print(f"     └─ Última linha: {linhas[-1].strip()}")
    except Exception as e:
        print(f"  ⚠️ Erro lendo CSV {path.name}: {e}")

def ler_txt(path: Path):
    try:
        tamanho = path.stat().st_size / 1024
        with open(path, "r", encoding="utf-8") as f:
            linhas = f.readlines()
        print(f"  📄 {path.name} ({tamanho:.1f} KB, {len(linhas)} linhas)")
        if linhas:
            print(f"     └─ Linha 1: {linhas[0].strip()}")
            if len(linhas) > 1:
                print(f"     └─ Linha 2: {linhas[1].strip()}")
    except Exception as e:
        print(f"  ⚠️ Erro lendo TXT {path.name}: {e}")

def main():
    print("🔍 VARREDURA TOTAL DA PASTA COLETAS (Read-Only)")
    print(f"📍 Raiz: {COLETAS_DIR}\n")

    if not COLETAS_DIR.exists():
        print("❌ Pasta Coletas não encontrada.")
        return

    # Lista todos os diretórios (inclusive os de histórico) e ordena
    diretorios = [COLETAS_DIR]
    for d in COLETAS_DIR.iterdir():
        if d.is_dir():
            diretorios.append(d)

    for diretorio in sorted(diretorios):
        print(f"\n{'='*70}")
        print(f" 📁 PASTA: {diretorio.relative_to(BASE_DIR)}")
        print(f"{'='*70}")

        arquivos = sorted(diretorio.glob("*"))
        if not arquivos:
            print("  (vazia)")
            continue

        # Limita a exibição se for histórico (pode ter centenas de arquivos)
        if "Historico" in diretorio.name and len(arquivos) > 5:
            print(f"  (Mostrando os 5 mais recentes de {len(arquivos)} arquivos)")
            arquivos = sorted(arquivos, key=lambda x: x.stat().st_mtime, reverse=True)[:5]

        for arq in arquivos:
            if arq.is_file():
                sufixo = arq.suffix.lower()
                if sufixo == ".json":
                    ler_json(arq)
                elif sufixo == ".csv":
                    ler_csv(arq)
                elif sufixo == ".txt":
                    ler_txt(arq)
                else:
                    print(f"  📄 {arq.name} ({arq.stat().st_size/1024:.1f} KB) - Ignorado (extensão {sufixo})")

    print("\n" + "="*70)
    print(" ✅ FIM DA VARREDURA TOTAL.")
    print("="*70)

if __name__ == "__main__":
    main()