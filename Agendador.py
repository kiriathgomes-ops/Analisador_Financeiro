# ============================================================
# ARQUIVO: Agendador.py
#
# AGENDADOR SINCRONIZADO COM RELÓGIO (A CADA 5 MIN EM :04, :09, :14...)
# ============================================================

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PIPELINE = os.path.join(BASE_DIR, "main_pipeline.py")


# Segundos de delay apos o minuto redondo (seguranca pra candle fechar no MT5)
SEGUNDO_DISPARO = 5

# Disparos regulares: a cada 5 min no segundo :05
DISPAROS_REGULARES = [
    h * 3600 + m * 60 + SEGUNDO_DISPARO
    for h in range(24)
    for m in range(0, 60, 5)
]

# Disparos especiais (adicionais): 1 min antes da abertura B3 e do ORB
DISPAROS_ESPECIAIS = [
    8 * 3600 + 59 * 60 + SEGUNDO_DISPARO,   # 08:59:05
    9 * 3600 + 59 * 60 + SEGUNDO_DISPARO,   # 09:59:05
]

# Grade consolidada (ordenada, dedupada)
DISPAROS = sorted(set(DISPAROS_REGULARES + DISPAROS_ESPECIAIS))


def calcular_segundos_ate_proximo_ciclo():
    """Calcula quantos segundos faltam ate o proximo disparo (grade + especiais)."""
    agora = datetime.now()
    agora_seg = (
        agora.hour * 3600
        + agora.minute * 60
        + agora.second
        + agora.microsecond / 1_000_000.0
    )

    for t in DISPAROS:
        if t > agora_seg:
            return max(0.0, t - agora_seg)

    # Passou de todos hoje -> pega o primeiro de amanha
    return max(0.0, 86400 - agora_seg + DISPAROS[0])


def iniciar_agendador(once: bool = False):
    print("============================================================")
    print("⏰ AGENDADOR SINCRONIZADO INICIADO")
    print(f"🎯 REGULAR: a cada 5 min no segundo :{SEGUNDO_DISPARO:02d}")
    print(f"   Ex: 00:05 | 05:05 | 10:05 | ... | 55:05")
    print(f"🎯 ESPECIAIS: 08:59:{SEGUNDO_DISPARO:02d} | 09:59:{SEGUNDO_DISPARO:02d}")
    print("============================================================")
    print()
    print("📅 Proximos 5 disparos:")
    agora = datetime.now()
    agora_seg = (
        agora.hour * 3600 + agora.minute * 60 + agora.second
        + agora.microsecond / 1_000_000.0
    )
    contador = 0
    for t in DISPAROS:
        if t > agora_seg and contador < 5:
            h, rem = divmod(int(t), 3600)
            m, s = divmod(rem, 60)
            print(f"   {h:02d}:{m:02d}:{s:02d}")
            contador += 1
    print()

    # fix78: modo --once (debug) — executa 1 ciclo e sai
    if once:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 [--once] Disparando Main Pipeline (imediato)...")
        try:
            subprocess.run([sys.executable, SCRIPT_PIPELINE], check=True)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Ciclo unico concluido.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro na execucao do pipeline: {e}")
        except Exception as e:
            print(f"⚠️ Falha inesperada: {e}")
        return

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
    _parser = argparse.ArgumentParser(
        description="Agendador sincronizado do pipeline (grade :05s + especiais)"
    )
    _parser.add_argument(
        "--once", action="store_true",
        help="Executa 1 ciclo imediato e sai (modo debug)"
    )
    _args = _parser.parse_args()
    iniciar_agendador(once=_args.once)
