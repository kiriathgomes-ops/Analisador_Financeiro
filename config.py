# config.py
import sys
from pathlib import Path

# Adiciona a raiz ao path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Importa o KeyManager
from utils.KeyManager import get_groq_client, key_manager