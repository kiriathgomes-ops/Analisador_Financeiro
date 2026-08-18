# teste_motor.py
import sys
import json
from pathlib import Path

# Adiciona a raiz do projeto ao path para importar o novo motor
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from NOVO_MOTOR_PREVISAO_ABERTURA.core.motor_previsao import executar_previsao

if __name__ == "__main__":
    print("🚀 Executando Novo Motor de Previsão...")
    resultado = executar_previsao()
    
    if resultado:
        print("\n✅ Previsão gerada com sucesso!\n")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
    else:
        print("\n❌ Falha ao carregar dados. Certifique-se de que o pipeline foi executado e os JSONs estão em 'Coletas/'.")