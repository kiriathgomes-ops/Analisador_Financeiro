import ast, re
from pathlib import Path

src = Path("CalculadoraEstimativaAbertura.py").read_text(encoding="utf-8")
ast.parse(src)
print("[OK] Sintaxe valida")

# Confirma que LastTick é fonte primária
if "LastTick_Congelado" in src and "_carregar_ohlc_ontem_lasttick" in src:
    print("[OK] Fix pivot: LastTick_Congelado como fonte primaria")
else:
    print("[ATENCAO] Fix pivot ausente")

# Confirma que o bug antigo sumiu
if "if close_d1 <= 0:" in src:
    print("[ATENCAO] Bug antigo (if close_d1 <= 0) ainda presente")
else:
    print("[OK] Bug antigo (if close_d1 <= 0) removido")

# Except silenciosos (cobre except:, except Tipo:, except (T1, T2):)
sil = []
for i, ln in enumerate(src.splitlines(), 1):
    s = ln.strip()
    if re.match(r"^except\s*(?:\([^)]*\)|[A-Za-z_][\w.]*)?\s*:\s*$", s) and " as " not in s:
        sil.append((i, s))
if sil:
    print(f"[ATENCAO] {len(sil)} except silencioso(s):")
    for ln, t in sil:
        print(f"   L{ln}: {t}")
else:
    print("[OK] Nenhum except silencioso restante")

if re.search(r"except[^:]*:\s*pass\b", src):
    print("[ATENCAO] Ainda existe 'except: pass' literal")
else:
    print("[OK] Nenhum 'except: pass' literal")