# _dry_coletor_import.py — dry-run de validacao do Coletor_MT5_v2_2.py
import ast
import re
from pathlib import Path

src = Path("Coletor_MT5_v2_2.py").read_text(encoding="utf-8")
ast.parse(src)
print("[OK] Sintaxe valida")

# Procura except sem 'as e' (silenciosos) e except:pass cru
silenciosos = []
for i, linha in enumerate(src.splitlines(), 1):
    stripped = linha.strip()
    # except: ou except Tipo:  (sem 'as')
    if re.match(r"^except\s*:", stripped):
        silenciosos.append((i, "except: cru", stripped))
    elif re.match(r"^except\s+\w+(\s*,\s*\w+)?\s*:", stripped):
        silenciosos.append((i, "except sem 'as'", stripped))

if silenciosos:
    print(f"[ATENCAO] {len(silenciosos)} except silencioso(s) restante(s):")
    for ln, tipo, txt in silenciosos:
        print(f"   linha {ln} ({tipo}): {txt}")
else:
    print("[OK] Nenhum except silencioso restante")

# Confirma que o pass literal nao existe
if re.search(r"except[^:]*:\s*pass\b", src):
    print("[ATENCAO] Ainda existe except: pass literal")
else:
    print("[OK] Nenhum 'except: pass' literal")