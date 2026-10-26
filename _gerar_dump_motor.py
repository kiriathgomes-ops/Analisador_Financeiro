import os
from pathlib import Path

# Pasta alvo da análise
TARGET_DIR = Path("NOVO_MOTOR_PREVISAO_ABERTURA")
OUTPUT_FILE = "dump_motor.txt"

def gerar_dump():
    print(f"🔎 Iniciando varredura na pasta: {TARGET_DIR}...")
    
    if not TARGET_DIR.exists():
        print(f"❌ Erro: A pasta {TARGET_DIR} não existe.")
        return

    conteudo_final = []
    
    # Extensões que queremos ler
    extensoes_validas = {".py", ".yaml", ".json", ".txt"}

    # Caminha por todas as subpastas
    for root, dirs, files in os.walk(TARGET_DIR):
        # Ignora a pasta __pycache__
        if "__pycache__" in root:
            continue
            
        for file in sorted(files):
            ext = Path(file).suffix.lower()
            if ext in extensoes_validas:
                caminho_completo = Path(root) / file
                
                # Formata o cabeçalho do arquivo no dump
                header = "=" * 80
                header += f"\nARQUIVO: {caminho_completo}\n"
                header += "=" * 80 + "\n"
                
                try:
                    texto_arquivo = caminho_completo.read_text(encoding="utf-8", errors="ignore")
                    conteudo_final.append(header + texto_arquivo + "\n\n")
                except Exception as e:
                    print(f"⚠️ Erro ao ler {caminho_completo}: {e}")

    # Salva tudo num único arquivo
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("".join(conteudo_final))
        
    print(f"✅ Dump gerado com sucesso!")
    print(f"📁 Arquivo salvo em: {OUTPUT_FILE}")
    print(f"📏 Tamanho: {os.path.getsize(OUTPUT_FILE) / 1024:.1f} KB")
    print("\nAgora abra o arquivo dump_motor.txt, copie tudo e cole aqui no chat para eu analisar.")

if __name__ == "__main__":
    gerar_dump()