import os
from pathlib import Path

# Pasta alvo
TARGET_DIR = Path("v2")
OUTPUT_FILE = "dump_v2.txt"

def gerar_dump():
    print(f"🔎 Iniciando varredura na pasta: {TARGET_DIR}...")
    
    if not TARGET_DIR.exists():
        print(f"❌ Erro: A pasta {TARGET_DIR} não existe.")
        return

    conteudo_final = []
    extensoes_validas = {".py"}

    for root, dirs, files in os.walk(TARGET_DIR):
        # Ignora caches
        if "__pycache__" in root:
            continue
            
        for file in sorted(files):
            ext = Path(file).suffix.lower()
            if ext in extensoes_validas:
                # Pula arquivos de teste se quiser (opcional, mas vamos incluir para ver a cobertura)
                # if "test_" in file: continue
                
                caminho_completo = Path(root) / file
                header = "=" * 80
                header += f"\nARQUIVO: {caminho_completo}\n"
                header += "=" * 80 + "\n"
                
                try:
                    texto_arquivo = caminho_completo.read_text(encoding="utf-8", errors="ignore")
                    conteudo_final.append(header + texto_arquivo + "\n\n")
                except Exception as e:
                    print(f"⚠️ Erro ao ler {caminho_completo}: {e}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("".join(conteudo_final))
        
    tamanho_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"✅ Dump gerado com sucesso!")
    print(f"📁 Arquivo salvo em: {OUTPUT_FILE}")
    print(f"📏 Tamanho: {tamanho_kb:.1f} KB")
    
    if tamanho_kb > 150:
        print("\n⚠️ ATENÇÃO: O arquivo ficou muito grande. Se não couber na mensagem, me avise que podemos dividir a análise por pastas (engines, services, etc).")
    else:
        print("\nAgora abra o arquivo dump_v2.txt, copie tudo e cole aqui no chat para eu analisar.")

if __name__ == "__main__":
    gerar_dump()