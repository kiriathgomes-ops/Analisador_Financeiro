# ============================================================
# ARQUIVO: Agendador.py
#
# AGENDADOR SINCRONIZADO COM RELÓGIO (A CADA 5 MIN EM :04, :09, :14...)
# ============================================================

import os
import subprocess
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PIPELINE = os.path.join(BASE_DIR, "main_pipeline.py")


def calcular_segundos_ate_proximo_ciclo():
    """Calcula quantos segundos faltam até o próximo minuto terminado em 4 ou 9."""
    agora = datetime.now()
    minuto_atual = agora.minute
    segundo_atual = agora.second
    microsegundo_atual = agora.microsecond

    # Calcula os minutos necessários até o próximo múltiplo de 5 vindo do :04
    # Os minutos de disparo são: 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59
    minutos_para_esperar = (4 - (minuto_atual % 5)) % 5

    # Se já passou do segundo 0 do minuto exato de execução, espera o próximo ciclo de 5 min
    if minutos_para_esperar == 0 and (
        segundo_atual > 0 or microsegundo_atual > 0
    ):
        minutos_para_esperar = 5

    # Converte tudo para segundos exatos
    segundos_restantes = (
        (minutos_para_esperar * 60)
        - segundo_atual
        - (microsegundo_atual / 1_000_000.0)
    )
    return max(0.0, segundos_restantes)


def iniciar_agendador():
    print("============================================================")
    print("⏰ AGENDADOR SINCRONIZADO INICIADO")
    print("🎯 PONTOS DE EXECUÇÃO: :04 | :09 | :14 | :19 | :24 | :29 ...")
    print("============================================================")

    while True:
        segundos_espera = calcular_segundos_ate_proximo_ciclo()
        proximo_disparo = time.strftime(
            "%H:%M:%S", time.localtime(time.time() + segundos_espera)
        )

        print(
            f"\n[⏳ STATUS] Aguardando {int(segundos_espera)}s até a próxima janela ({proximo_disparo})..."
        )
        time.sleep(segundos_espera)

        print(
            f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 Disparando Main Pipeline..."
        )
        try:
            subprocess.run([sys.executable, SCRIPT_PIPELINE], check=True)
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Ciclo concluído com sucesso."
            )
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro na execução do pipeline: {e}")
        except Exception as e:
            print(f"⚠️ Falha inesperada no agendador: {e}")


if __name__ == "__main__":
    iniciar_agendador()
