import os
from pathlib import Path

# Padrões suspeitos (trava de segurança de mercado calmo)
PADROES = [
    "abs(", 
    "> 15", "> 20", "> 10", "> 5", 
    "< -15", "< -20", "< -10", "< -5",
    "change_percent", "variacao", "pct_val", "dp_absurdo"
]

IGNORAR = ["__pycache__", ".git", "Coletas", ".venv", "lixo", "test", "teste", "PromptIA", "docs", "ferramentas/fixes", "auditoria"]

def auditar():
    print("=" * 70)
    print(" 🕵️ AUDITORIA DE LIMITES E TRAVAS DE SEGURANÇA")
    print("=" * 70)

    for p in Path(".").rglob("*.py"):
        if any(ign in str(p).lower() for ign in IGNORAR):
            continue

        try:
            linhas = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue

        achados = []
        for i, linha in enumerate(linhas, 1):
            linha_limpa = linha.strip()
            
            # Pula comentários
            if linha_limpa.startswith("#"):
                continue

            # Procura por validações de limites (ex: abs(x) > 15)
            if "abs(" in linha_limpa and (">" in linha_limpa or "<" in linha_limpa):
                achados.append((i, linha_limpa, "Limite Percentual Absoluto"))
            elif "change_percent" in linha_limpa and (">" in linha_limpa or "<" in linha_limpa):
                 achados.append((i, linha_limpa, "Validação de Change Percent"))
            elif "stale" in linha_limpa.lower() and ">" in linha_limpa:
                 achados.append((i, linha_limpa, "Validação de Stale (Idade do Candle)"))

        if achados:
            print(f"\n📄 Arquivo: {p}")
            for linha_num, linha_txt, tipo in achados:
                print(f"   L{linha_num:03d} | [{tipo}] {linha_txt}")

    print("\n" + "=" * 70)
    print(" ✅ Auditoria concluída.")
    print(" Verifique se as linhas acima foram feitas para 'mercado normal'")
    print(" e podem estar bloqueando dados reais em dias de pânico.")
    print("=" * 70)

if __name__ == "__main__":
    auditar()