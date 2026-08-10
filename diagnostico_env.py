# diagnostico_env.py
import os
from pathlib import Path
from dotenv import load_dotenv

print("=" * 60)
print("🔍 DIAGNÓSTICO DO .env")
print("=" * 60)

# 1. Onde está o .env?
BASE_DIR = Path(__file__).resolve().parent
print(f"\n📁 BASE_DIR: {BASE_DIR}")

# 2. O arquivo .env existe?
env_path = BASE_DIR / ".env"
print(f"\n📄 Arquivo .env: {env_path}")
print(f"   Existe? {env_path.exists()}")

if env_path.exists():
    # 3. Mostra o conteúdo do .env (primeiras linhas)
    print("\n📝 CONTEÚDO DO .env (primeiras 20 linhas):")
    print("-" * 40)
    with open(env_path, "r", encoding="utf-8") as f:
        linhas = f.readlines()
        for i, linha in enumerate(linhas[:20]):
            # Oculta o valor da chave por segurança
            if "GROQ_API_KEY" in linha:
                if "=" in linha:
                    parte = linha.split("=")
                    if len(parte) > 1:
                        valor = parte[1].strip()
                        if valor and valor != '""' and valor != "''":
                            print(f"{i+1}: {parte[0]} = {valor[:10]}...")
                        else:
                            print(f"{i+1}: {parte[0]} = (vazio)")
                    else:
                        print(f"{i+1}: {linha.strip()}")
            else:
                if linha.strip():
                    print(f"{i+1}: {linha.strip()}")
    print("-" * 40)

# 4. Carrega o .env
print("\n🔄 Carregando .env com load_dotenv()...")
load_dotenv(env_path, override=True)

# 5. Verifica as variáveis carregadas
print("\n🔑 VARIÁVEIS GROQ_ENCONTRADAS:")
print("-" * 40)

chaves_encontradas = []
i = 1
while True:
    var_name = f"GROQ_API_KEY_{i}"
    value = os.getenv(var_name)
    if value:
        chaves_encontradas.append(f"{var_name} = {value[:15]}...")
        i += 1
    else:
        break

# Também verifica a chave padrão
default_key = os.getenv("GROQ_API_KEY")
if default_key:
    chaves_encontradas.append(f"GROQ_API_KEY = {default_key[:15]}...")

if chaves_encontradas:
    for c in chaves_encontradas:
        print(f"   ✅ {c}")
else:
    print("   ❌ NENHUMA CHAVE ENCONTRADA!")

# 6. Verifica todas as variáveis do .env
print("\n📊 TODAS AS VARIÁVEIS CARREGADAS:")
print("-" * 40)
for key, value in os.environ.items():
    if "GROQ" in key.upper():
        print(f"   {key} = {value[:20]}...")

print("\n" + "=" * 60)
print("✅ DIAGNÓSTICO CONCLUÍDO")
print("=" * 60)