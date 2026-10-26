import os
from pathlib import Path

BASE_DIR = Path(".")
PROMPT_DIR = BASE_DIR / "PromptIA"
DEST_DIR = BASE_DIR / "PromptIATeste"

if not PROMPT_DIR.exists():
    print("❌ Pasta PromptIA não encontrada.")
    exit()

if not DEST_DIR.exists():
    DEST_DIR.mkdir()
    print("📁 Pasta 'PromptIATeste' criada.")

# 1. Junta todo o código Python do projeto em um único texto
codigo_completo = ""
for p in BASE_DIR.rglob("*.py"):
    if ".venv" in str(p) or "Coletas" in str(p) or "PromptIATeste" in str(p):
        continue
    try:
        codigo_completo += p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pass

# 2. Verifica cada arquivo da pasta PromptIA
movidos = []
mantidos = []

for file in PROMPT_DIR.glob("*"):
    if file.is_file():
        # Se o nome exato do arquivo não estiver em NENHUM código Python, ele é lixo.
        if file.name not in codigo_completo:
            dest_file = DEST_DIR / file.name
            file.rename(dest_file)
            movidos.append(file.name)
        else:
            mantidos.append(file.name)

print("\n✅ Prompts em USO (Mantidos em PromptIA/):")
for m in mantidos:
    print(f"  - {m}")

print("\n📦 Prompts NÃO ENCONTRADOS no código (Movidos para PromptIATeste/):")
for m in movidos:
    print(f"  - {m}")

print("\n🎉 Auditoria concluída!")