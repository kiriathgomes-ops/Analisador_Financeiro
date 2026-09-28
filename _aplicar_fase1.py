#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplica as alterações da Fase 1 (quick wins) com backup automático.
Uso:  python _aplicar_fase1.py
"""
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent
BACKUP = BASE / "_backup_fase1"

# Arquivos alvo
ALVO_1 = BASE / "v2" / "core" / "__init__.py"
ALVO_2 = BASE / "utils" / "KeyManager.py"
ALVO_3 = BASE / "CalculadoraEstimativaAbertura.py"


def backup(caminho: Path):
    destino = BACKUP / caminho.relative_to(BASE)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(caminho, destino)
    print(f"  [backup] {caminho.relative_to(BASE)}")


def replace_uma_vez(caminho: Path, de: str, para: str, descricao: str) -> bool:
    texto = caminho.read_text(encoding="utf-8")
    if de not in texto:
        print(f"  [ATENCAO] '{descricao}': padrao NAO encontrado em {caminho.relative_to(BASE)}")
        return False
    caminho.write_text(texto.replace(de, para, 1), encoding="utf-8")
    print(f"  [OK] {descricao}")
    return True


print("=" * 60)
print(" FASE 1 — quick wins")
print("=" * 60)

# ------------------------------------------------------------
# 1. v2/core/__init__.py  -> substituir arquivo inteiro
# ------------------------------------------------------------
print("\n[1/3] v2/core/__init__.py (substituicao total)")
backup(ALVO_1)
ALVO_1.write_text(
    '# v2/core/__init__.py\n'
    '"""Pacote core da versão 2 (contratos, engines e services)."""\n',
    encoding="utf-8",
)
print("  [OK] arquivo substituido (stub PredictionService removido)")

# ------------------------------------------------------------
# 2. utils/KeyManager.py  -> corrigir alias
# ------------------------------------------------------------
print("\n[2/3] utils/KeyManager.py (alias get_groq_client)")
backup(ALVO_2)
replace_uma_vez(
    ALVO_2,
    "get_groq_client = key_manager.get_groq_client if hasattr(key_manager, 'get_groq_client') else key_manager.obter_cliente_groq",
    "get_groq_client = key_manager.obter_cliente_groq",
    "alias get_groq_client",
)

# ------------------------------------------------------------
# 3. CalculadoraEstimativaAbertura.py -> indentacao + pesos
# ------------------------------------------------------------
print("\n[3/3] CalculadoraEstimativaAbertura.py (2 ajustes)")
backup(ALVO_3)

# 3a. indentacao do comentario
replace_uma_vez(
    ALVO_3,
    "            # --- PREÇO BASE DE REFERÊNCIA (sempre o ajuste oficial) ---",
    "        # --- PREÇO BASE DE REFERÊNCIA (sempre o ajuste oficial) ---",
    "indentacao do comentario do preco base",
)

# 3b. deduplicar pesos
replace_uma_vez(
    ALVO_3,
    '        cesta_adrs = (vale * pesos.get("adr_vale", 0.30)) + (petr * pesos.get("adr_petr", 0.25))\n'
    '        var_pct = (ewz * pesos.get("ewz", 0.30)) + (cesta_adrs * pesos.get("cesta_adrs", 0.35)) + (sp500 * pesos.get("sp500_fut", 0.20))',
    '        cesta_adrs = (vale * pesos["adr_vale"]) + (petr * pesos["adr_petr"])\n'
    '        var_pct = (\n'
    '            (ewz * pesos["ewz"])\n'
    '            + (cesta_adrs * pesos["cesta_adrs"])\n'
    '            + (sp500 * pesos["sp500_fut"])\n'
    '        )',
    "deduplicacao de pesos",
)

print("\n" + "=" * 60)
print(" Concluido. Backup em: _backup_fase1/")
print("=" * 60)
