import cv2
import mss
from PIL import Image
import os
import json

PASTA_COLETAS = "Coletas"
os.makedirs(PASTA_COLETAS, exist_ok=True)
ARQUIVO_CONFIG = os.path.join(PASTA_COLETAS, "config_regiao.json")

def listar_monitores():
    with mss.MSS() as sct:
        monitores = sct.monitors
        print("\n" + "="*60)
        print("MONITORES DETECTADOS")
        print("="*60)
        for i, mon in enumerate(monitores):
            if i == 0:
                print(f"[{i}] Tela virtual (todos juntos) - {mon['width']}x{mon['height']}")
            else:
                print(f"[{i}] Monitor {i} | left={mon['left']:5}  top={mon['top']:4}  {mon['width']}x{mon['height']}")
        print("="*60)
        return monitores

def main():
    print("="*60)
    print(" 🗺️ MAPEADOR DE REGIÃO DO PREÇO TEÓRICO ")
    print("="*60)

    monitores = listar_monitores()
    while True:
        try:
            escolha = int(input("\nEm qual monitor está o Profit Pro? (digite o número): "))
            if 1 <= escolha < len(monitores):
                monitor = monitores[escolha]
                break
            print("Escolha um número válido.")
        except ValueError:
            print("Digite apenas números.")

    print("\n1. Deixe o Profit Pro aberto e o preço teórico visível.")
    input("Pressione ENTER para capturar a tela inteira do monitor...")

    with mss.MSS() as sct:
        img = sct.grab(monitor)
        img_pil = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")

    nome_completo = os.path.join(PASTA_COLETAS, f"monitor_{escolha}_completo.png")
    img_pil.save(nome_completo)
    print(f"\n[OK] Tela salva em '{nome_completo}'. Abra-a para ver as coordenadas.")

    print("\nInforme as coordenadas RELATIVAS (dentro desse monitor):")
    left = int(input("LEFT   (X do canto esquerdo): "))
    top = int(input("TOP    (Y do canto superior): "))
    width = int(input("WIDTH  (largura da área): "))
    height = int(input("HEIGHT (altura da área): "))

    # Cria o recorte para confirmação visual
    recorte = img_pil.crop((left, top, left + width, top + height))
    caminho_recorte = os.path.join(PASTA_COLETAS, "recorte_confirmacao.png")
    recorte.save(caminho_recorte)
    
    # Salva também a região absoluta baseada no monitor
    regiao_absoluta = {
        "top": monitor["top"] + top,
        "left": monitor["left"] + left,
        "width": width,
        "height": height
    }

    with open(ARQUIVO_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(regiao_absoluta, f, indent=4)

    print("\n" + "="*60)
    print(" 📋 TABELINHA DE COORDENADAS MAPEADAS (Salvo em Coletas/)")
    print("="*60)
    print(f" +--------+--------+--------+--------+")
    print(f" |  LEFT  |  TOP   | WIDTH  | HEIGHT |")
    print(f" +--------+--------+--------+--------+")
    print(f" | {left:<6} | {top:<6} | {width:<6} | {height:<6} |")
    print(f" +--------+--------+--------+--------+")
    print(f"\n[SUCESSO] Configuração gravada em '{ARQUIVO_CONFIG}'.")
    print(f"Verifique o recorte em '{caminho_recorte}' para garantir que o preço está enquadrado.")

if __name__ == "__main__":
    main()