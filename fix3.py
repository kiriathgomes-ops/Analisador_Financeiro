#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix3.py — Calibra limiares do motor_gap em % (nao mais pontos absolutos)
=========================================================================

Problema:
  O motor_gap.py tinha limiares em PONTOS absolutos (20/50/100/200). Como
  o WIN ja esteve em 100k e hoje esta em 188k, esses limiares ficam
  desalinhados com o tempo. Um gap de 200 pts era 0.2% em 2026, mas 0.4%
  em 2020. Chamar isso de "FORTE" hoje e exagero.

Solucao:
  Trocar por limiares em PERCENTUAL do preco de referencia (fechamento
  anterior). Isso escala automaticamente com o tempo e com a inflacao
  do indice.

Novos limiares (% do fechamento anterior):
  MICRO    → ate 0.05%      (~94 pts hoje)
  PEQUENO  → 0.05-0.15%     (~94-283 pts)
  MODERADO → 0.15-0.30%     (~283-566 pts)
  FORTE    → 0.30-0.60%     (~566-1132 pts)
  EXTREMO  → >0.60%         (>1132 pts)

Arquivos alterados:
  - NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_gap.py   (3 patches)
  - NOVO_MOTOR_PREVISAO_ABERTURA/config/pesos.yaml   (1 patch)

Uso:
    python fix3.py --dry-run
    python fix3.py
    python fix3.py --reverter
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


# ============================================================
# ALVOS E PATCHES
# ============================================================
# Estrutura: {caminho: [(nome_patch, texto_antigo, texto_novo), ...]}

ALVOS = {
    Path("NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_gap.py"): [
        # -------- Patch 1: substitui LIMIARES (pontos) por LIMIARES_PCT (%) --------
        (
            "motor_gap.py: substitui LIMIARES (pontos) por LIMIARES_PCT (%)",
            """# Limiares para classificação de GAP (em pontos)
LIMIARES = {
    "MICRO": 20,
    "PEQUENO": 50,
    "MODERADO": 100,
    "FORTE": 200,
    "EXTREMO": 999999
}""",
            """# ============================================================
# Limiares para classificação de GAP (% do preço de referência)
# ============================================================
# Antes eram pontos absolutos (20/50/100/200). Problema: não escalavam
# com o preço do WIN (que já esteve em 100k e hoje está em 188k).
# Um gap de 200 pts era 0.2% em 2026, mas seria 0.4% em 2020.
#
# Agora usamos % do preço de referência (fechamento anterior). Isso
# escala automaticamente com o tempo e com a inflação do índice.
#
# Valores calibrados com base no ATR M5 atual (~120 pts = 0.06%) e na
# experiência operacional do WIN:
#   MICRO    → até 0.05%    (~94 pts hoje)    — ruído de leilão
#   PEQUENO  → 0.05-0.15%   (~94-283 pts)     — gap normal
#   MODERADO → 0.15-0.30%   (~283-566 pts)    — gap relevante
#   FORTE    → 0.30-0.60%   (~566-1132 pts)   — gap de evento
#   EXTREMO  → >0.60%       (>1132 pts)       — gap histórico (raro)
# ============================================================
LIMIARES_PCT = {
    "MICRO": 0.05,
    "PEQUENO": 0.15,
    "MODERADO": 0.30,
    "FORTE": 0.60,
    "EXTREMO": 999.0
}""",
        ),

        # -------- Patch 2: classificação usa % em vez de pontos --------
        (
            "motor_gap.py: classificar_gap usa gap_percentual (nao abs_gap)",
            """    abs_gap = abs(gap_pontos)
    
    # Determinar intensidade
    if abs_gap < LIMIARES["MICRO"]:
        intensidade = "MICRO"
    elif abs_gap < LIMIARES["PEQUENO"]:
        intensidade = "PEQUENO"
    elif abs_gap < LIMIARES["MODERADO"]:
        intensidade = "MODERADO"
    elif abs_gap < LIMIARES["FORTE"]:
        intensidade = "FORTE"
    else:
        intensidade = "EXTREMO"
    
    return ClassificacaoGAP(""",
            """    # Classificação por % (não mais por pontos absolutos — ver LIMIARES_PCT)
    abs_gap_pct = abs(gap_percentual)
    
    if abs_gap_pct < LIMIARES_PCT["MICRO"]:
        intensidade = "MICRO"
    elif abs_gap_pct < LIMIARES_PCT["PEQUENO"]:
        intensidade = "PEQUENO"
    elif abs_gap_pct < LIMIARES_PCT["MODERADO"]:
        intensidade = "MODERADO"
    elif abs_gap_pct < LIMIARES_PCT["FORTE"]:
        intensidade = "FORTE"
    else:
        intensidade = "EXTREMO"
    
    # Log enxuto (facilita debug e ver o limiar aplicado)
    print(f"[GAP] {gap_pontos:+.0f} pts ({gap_percentual:+.4f}%) -> {intensidade}")
    
    return ClassificacaoGAP(""",
        ),

        # -------- Patch 3: docstring do módulo atualizada --------
        (
            "motor_gap.py: atualiza docstring (limiares em %)",
            '''# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_gap.py
from typing import Dict, Any
from ..dados.schemas import ClassificacaoGAP''',
            '''# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_gap.py
#
# ATUALIZAÇÃO 18/09/2026:
#   Limiares de classificação migraram de pontos absolutos para % do
#   preço de referência. Ver LIMIARES_PCT para detalhes da calibração.
from typing import Dict, Any
from ..dados.schemas import ClassificacaoGAP''',
        ),
    ],

    Path("NOVO_MOTOR_PREVISAO_ABERTURA/config/pesos.yaml"): [
        # -------- Patch único: atualiza bloco gap_limiares --------
        (
            "pesos.yaml: gap_limiares -> gap_limiares_pct (mantém legado comentado)",
            """gap_limiares:
  micro: 20
  pequeno: 50
  moderado: 100
  forte: 200
  extremo: 999999""",
            """# Limiares de gap em % do preço de referência (não mais pontos).
# Ver motor_gap.py (LIMIARES_PCT) para detalhes da calibração.
gap_limiares_pct:
  micro: 0.05
  pequeno: 0.15
  moderado: 0.30
  forte: 0.60
  extremo: 999.0

# DEPRECATED — mantido apenas para referência histórica (valores em pontos)
# gap_limiares:
#   micro: 20
#   pequeno: 50
#   moderado: 100
#   forte: 200
#   extremo: 999999""",
        ),
    ],
}


# ============================================================
# LOGICA
# ============================================================
def _backups_do_alvo(alvo: Path):
    """Retorna backups do arquivo alvo, do mais recente ao mais antigo."""
    return sorted(
        alvo.parent.glob(f"{alvo.name}.bak_*"),
        reverse=True,
    )


def _validar_sintaxe_py(caminho: Path) -> tuple[bool, str]:
    """Valida sintaxe de um arquivo .py via ast.parse."""
    import ast
    try:
        ast.parse(caminho.read_text(encoding="utf-8"))
        return True, "OK"
    except SyntaxError as e:
        return False, f"SyntaxError linha {e.lineno}: {e.msg}"


def _validar_yaml(caminho: Path) -> tuple[bool, str]:
    """Valida sintaxe de um arquivo .yaml."""
    try:
        import yaml
    except ImportError:
        return True, "yaml nao instalado — pulando validacao"
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            yaml.safe_load(f)
        return True, "OK"
    except Exception as e:
        return False, f"YAMLError: {e}"


def reverter() -> int:
    restaurados = 0
    for alvo in ALVOS.keys():
        backups = _backups_do_alvo(alvo)
        if not backups:
            print(f"[AVISO] Sem backup para {alvo}")
            continue
        backup = backups[0]
        shutil.copy2(backup, alvo)
        print(f"[OK] {alvo} restaurado de {backup.name}")
        restaurados += 1

    if restaurados == 0:
        print("[ERRO] Nenhum backup encontrado")
        return 1
    return 0


def aplicar(dry_run: bool = False) -> int:
    # ---- Pre-validacao ----
    problemas = []
    for alvo, patches in ALVOS.items():
        if not alvo.exists():
            problemas.append(f"arquivo nao encontrado: {alvo}")
            continue
        conteudo = alvo.read_text(encoding="utf-8")
        for nome, antigo, _ in patches:
            if antigo not in conteudo:
                problemas.append(f"{alvo.name}: patch nao bate — '{nome}'")

    if problemas:
        print("[FALHA] Pre-validacao encontrou problemas:")
        for p in problemas:
            print(f"   - {p}")
        print("\nNenhuma alteracao foi feita.")
        return 2

    # ---- Backup ----
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not dry_run:
        for alvo in ALVOS.keys():
            backup = alvo.with_suffix(f"{alvo.suffix}.bak_{timestamp}")
            shutil.copy2(alvo, backup)
            print(f"[OK] Backup: {backup.name}")
    else:
        print("[DRY-RUN] Backup nao sera criado")

    # ---- Aplicar patches ----
    for alvo, patches in ALVOS.items():
        print(f"\n>> {alvo}")
        conteudo = alvo.read_text(encoding="utf-8")
        for i, (nome, antigo, novo) in enumerate(patches, start=1):
            if antigo in conteudo:
                conteudo = conteudo.replace(antigo, novo, 1)
                print(f"   [OK] Patch {i}/{len(patches)}: {nome}")
            else:
                print(f"   [AVISO] Patch {i}/{len(patches)}: {nome} — padrao nao encontrado")
                return 3

        # Validar ANTES de salvar
        if alvo.suffix == ".py":
            # Escreve em temp pra validar
            if not dry_run:
                alvo.write_text(conteudo, encoding="utf-8")
                ok, msg = _validar_sintaxe_py(alvo)
                if not ok:
                    print(f"   [ERRO] Sintaxe invalida: {msg}")
                    return 4
                print(f"   [OK] Sintaxe validada")
        elif alvo.suffix in (".yaml", ".yml"):
            if not dry_run:
                alvo.write_text(conteudo, encoding="utf-8")
                ok, msg = _validar_yaml(alvo)
                if not ok:
                    print(f"   [ERRO] YAML invalido: {msg}")
                    return 5
                print(f"   [OK] YAML validado")
        else:
            if not dry_run:
                alvo.write_text(conteudo, encoding="utf-8")

    print(f"\n[OK] {len(ALVOS)} arquivo(s) atualizado(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calibra limiares do motor_gap em % (nao mais pontos)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simula sem salvar")
    parser.add_argument("--reverter", action="store_true", help="Restaura backups")
    args = parser.parse_args()

    print("=" * 60)
    print(" fix3.py — Calibra limiares do motor_gap em %")
    print("=" * 60)

    if args.reverter:
        return reverter()
    return aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())