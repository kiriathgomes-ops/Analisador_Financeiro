# test_import.py
import sys
from pathlib import Path
from dotenv import load_dotenv  # ← ADICIONE ESTA IMPORTAÇÃO

# Adiciona a raiz ao path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# 🔥 CARREGA O .env ANTES DE IMPORTAR
env_path = BASE_DIR / ".env"
load_dotenv(env_path, override=True)
print(f"📁 BASE_DIR: {BASE_DIR}")

# Tenta importar
try:
    from utils.KeyManager import get_groq_client, key_manager
    print("✅ Importação bem sucedida!")
    print(f"🔑 Chaves carregadas: {len(key_manager.keys)}")
    print(f"📊 Status: {key_manager.get_status()}")
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    print("\n📂 Verifique a estrutura:")
    print("  Analisador_Financeiro/")
    print("  ├── utils/")
    print("  │   ├── __init__.py")
    print("  │   └── KeyManager.py")
    print("  └── test_import.py")
except Exception as e:
    print(f"❌ Outro erro: {e}")