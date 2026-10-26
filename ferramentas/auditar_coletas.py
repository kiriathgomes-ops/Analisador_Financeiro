import os
import time
from pathlib import Path
from datetime import datetime

# ✅ FIX: Resolve o caminho da raiz do projeto (sobe 1 nível a partir de ferramentas/)
BASE_DIR = Path(__file__).resolve().parent.parent
COLETAS_DIR = BASE_DIR / "Coletas"

def formatar_idade(segundos):
    dias = int(segundos // (24 * 3600))
    horas = int((segundos % (24 * 3600)) // 3600)
    minutos = int((segundos % 3600) // 60)
    
    if dias > 0:
        return f"{dias}d {horas}h"
    elif horas > 0:
        return f"{horas}h {minutos}m"
    else:
        return f"{minutos}m"

def auditar_coletas():
    print("=" * 70)
    print(" 🕵️ AUDITORIA DE TEMPO DOS ARQUIVOS (COLETAS)")
    print("=" * 70)

    if not COLETAS_DIR.exists():
        print(f"❌ Pasta Coletas não encontrada em: {COLETAS_DIR}")
        return

    agora = time.time()
    arquivos = []
    pastas_historico = {}

    # 1. Separa arquivos soltos e pastas
    for p in COLETAS_DIR.glob("*"):
        if p.is_file():
            idade_segundos = agora - p.stat().st_mtime
            data_mod = datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
            arquivos.append({
                "nome": p.name,
                "idade_seg": idade_segundos,
                "idade_fmt": formatar_idade(idade_segundos),
                "data_mod": data_mod
            })
        elif p.is_dir() and p.name.startswith("Historico"):
            # Resumo das pastas de histórico
            qtd = len(list(p.glob("*.json")))
            if qtd > 0:
                mais_recente = max(p.glob("*.json"), key=os.path.getmtime)
                idade_hist = agora - mais_recente.stat().st_mtime
                pastas_historico[p.name] = {
                    "qtd": qtd,
                    "ultimo": mais_recente.name,
                    "idade_fmt": formatar_idade(idade_hist)
                }

    # Ordena do mais antigo para o mais recente
    arquivos.sort(key=lambda x: x["idade_seg"], reverse=True)

    # 2. Imprime os arquivos soltos
    print(f"\n📄 Arquivos na RAIZ da pasta Coletas ({len(arquivos)} arquivos):")
    print(f"{'ARQUIVO':<45} | {'ÚLTIMA MODIFICAÇÃO':<16} | {'IDADE':<10}")
    print("-" * 80)

    for arq in arquivos:
        # Alerta visual para arquivos com mais de 24h
        if arq["idade_seg"] > 24 * 3600:
            status = "🔴"
        elif arq["idade_seg"] > 2 * 3600:
            status = "🟡"
        else:
            status = "🟢"
            
        print(f"{status} {arq['nome']:<43} | {arq['data_mod']:<16} | {arq['idade_fmt']:<10}")

    # 3. Imprime o resumo dos históricos
    if pastas_historico:
        print("\n" + "=" * 70)
        print(" 📚 Resumo das Pastas de Histórico (Arquivos antigos são esperados)")
        print("=" * 70)
        for pasta, info in pastas_historico.items():
            print(f"📁 {pasta}")
            print(f"   └─ Qtd arquivos: {info['qtd']} | Último arquivo: {info['ultimo']} (há {info['idade_fmt']})")

    print("\n" + "=" * 70)
    print(" Legenda: 🟢 Recente (< 2h) | 🟡 Hoje (> 2h) | 🔴 Esquecido (> 24h)")
    print("=" * 70)

if __name__ == "__main__":
    auditar_coletas()