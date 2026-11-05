# _dry_calc_import.py — validacao do CalculadoraEstimativaAbertura.py
import ast
import re
from pathlib import Path

src = Path("CalculadoraEstimativaAbertura.py").read_text(encoding="utf-8")
ast.parse(src)
print("[OK] Sintaxe valida")

# Regex cobre: except:, except Tipo:, except (Tipo1, Tipo2):
# Exclui os que tem ' as ' (já logam)
silenciosos = []
for i, linha in enumerate(src.splitlines(), 1):
    s = linha.strip()
    if not re.match(r"^except\s*(?:\([^)]*\)|[A-Za-z_][\w.]*)?\s*:\s*$", s):
        continue
    if " as " in s:
        continue
    silenciosos.append((i, s))

if silenciosos:
    print(f"[ATENCAO] {len(silenciosos)} except silencioso(s):")
    for ln, txt in silenciosos:
        print(f"   L{ln}: {txt}")
else:
    print("[OK] Nenhum except silencioso restante")

if re.search(r"except[^:]*:\s*pass\b", src):
    print("[ATENCAO] Ainda existe 'except: pass' literal")
else:
    print("[OK] Nenhum 'except: pass' literal")

# Verifica o fix do pivot (checa que o 'if close_d1 <= 0' foi removido)
if "if close_d1 <= 0:" in src:
    print("[ATENCAO] Bug do pivot ainda presente (if close_d1 <= 0)")
else:
    print("[OK] Fix do pivot aplicado (close_d1 substituido incondicionalmente)")
    