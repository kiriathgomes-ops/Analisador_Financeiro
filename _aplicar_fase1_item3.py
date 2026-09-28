#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplica o item 3 da Fase 1 (CalculadoraEstimativaAbertura.py)
- corrige indentacao do comentario do preco base (8 -> 4 espacos)
- deduplica pesos (remove defaults redundantes do .get())
Usa regex tolerante a espacamento. Backup em _backup_fase1_item3/.
Uso:  python _aplicar_fase1_item3.py
"""
import re
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent
ALVO = BASE / "CalculadoraEstimativaAbertura.py"
BACKUP = BASE / "_backup_fase1_item3"


def aplicar(caminho: Path, padrao: str, repl: str, descricao: str, flags=0) -> bool:
    texto = caminho.read_text(encoding="utf-8")
    novo, n = re.subn(padrao, repl, texto, count=1, flags=flags)
    if n == 0:
        print(f"  [ATENCAO] {descricao}: padrao NAO encontrado")
        return False
    caminho.write_text(novo, encoding="utf-8")
    print(f"  [OK] {descricao}")
    return True


print("=" * 60)
print(" FASE 1 — item 3 (CalculadoraEstimativaAbertura.py)")
print("=" * 60)

# backup
BACKUP.mkdir(parents=True, exist_ok=True)
shutil.copy2(ALVO, BACKUP / "CalculadoraEstimativaAbertura.py")
print(f"  [backup] -> {BACKUP.relative_to(BASE)}/CalculadoraEstimativaAbertura.py")

# --- 3a. indentacao do comentario (normaliza para 4 espacos) ---
print("\n[3a] indentacao do comentario do preco base")
aplicar(
    ALVO,
    r'^[ \t]*# --- PREÇO BASE DE REFERÊNCIA \(sempre o ajuste oficial\) ---[ \t]*$',
    r'    # --- PREÇO BASE DE REFERÊNCIA (sempre o ajuste oficial) ---',
    "indentacao do comentario",
    flags=re.MULTILINE,
)

# --- 3b. deduplicar pesos (5 chaves, regex com espaco opcional apos virgula) ---
print("\n[3b] deduplicacao de pesos (.get() -> acesso direto)")
substituicoes = [
    (r'pesos\.get\("adr_vale",\s*0\.30\)', 'pesos["adr_vale"]', "peso adr_vale"),
    (r'pesos\.get\("adr_petr",\s*0\.25\)', 'pesos["adr_petr"]', "peso adr_petr"),
    (r'pesos\.get\("ewz",\s*0\.30\)', 'pesos["ewz"]', "peso ewz"),
    (r'pesos\.get\("cesta_adrs",\s*0\.35\)', 'pesos["cesta_adrs"]', "peso cesta_adrs"),
    (r'pesos\.get\("sp500_fut",\s*0\.20\)', 'pesos["sp500_fut"]', "peso sp500_fut"),
]
for padrao, repl, nome in substituicoes:
    aplicar(ALVO, padrao, repl, nome)

print("\n" + "=" * 60)
print(" Concluido.")
print("=" * 60)
