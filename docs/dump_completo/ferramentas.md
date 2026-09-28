# Dump completo - ferramentas

Gerado em: 2026-09-28 12:11:32
Total de arquivos: 3

## Arvore

```
ferramentas
|-- _debug_regiao.py
|-- mapear_regiao_ocr.py
`-- teste_ocr_direto.py
```

## Conteudo dos arquivos

### `ferramentas/_debug_regiao.py`

```python
import mss
import json

with open("Coletas/config_regiao.json", "r", encoding="utf-8") as f:
    regiao = json.load(f)

print(f"Região capturada: {regiao}")

with mss.MSS() as sct:
    img = sct.grab(regiao)
    mss.tools.to_png(img.rgb, img.size, output="Coletas/_debug_regiao_atual.png")

print("✅ Salvo em Coletas/_debug_regiao_atual.png")
print(f"Tamanho: {img.size}")

```

### `ferramentas/mapear_regiao_ocr.py`

```python
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
```

### `ferramentas/teste_ocr_direto.py`

```python
import mss
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import time
import re
import json
import os
import shutil

PASTA_COLETAS = "Coletas"
ARQUIVO_CONFIG = os.path.join(PASTA_COLETAS, "config_regiao.json")
ARQUIVO_TESTE_CSV = os.path.join(PASTA_COLETAS, "teste_coleta_bruta.csv")

tesseract_bin = shutil.which("tesseract")
if tesseract_bin:
    pytesseract.pytesseract.tesseract_cmd = tesseract_bin
else:
    caminhos_padrao = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        os.path.expanduser(r'~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe')
    ]
    for caminho in caminhos_padrao:
        if os.path.exists(caminho):
            pytesseract.pytesseract.tesseract_cmd = caminho
            break

def melhorar_para_ocr(img_pil):
    img = img_pil.convert('L')
    img = ImageEnhance.Contrast(img).enhance(3.0)
    img = img.filter(ImageFilter.SHARPEN)
    w, h = img.size
    return img.resize((w * 4, h * 4), Image.LANCZOS)

def testar_extracao(regiao):
    with mss.MSS() as sct:
        img_grab = sct.grab(regiao)
        img_pil = Image.frombytes("RGB", img_grab.size, img_grab.bgra, "raw", "BGRX")
    
    img_proc = melhorar_para_ocr(img_pil)
    # Mantemos o ponto e os dígitos na whitelist
    config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789.'
    texto_bruto = pytesseract.image_to_string(img_proc, config=config).strip()
    
    preco = None
    # âncora no ponto: procura exatamente o padrão [3 dígitos] . [3 dígitos] (ex: 189.266)
    match = re.search(r'(\d{3})\.(\d{3})', texto_bruto)
    
    if match:
        # Junta os 3 antes e os 3 depois do ponto ignorando o próprio ponto para virar inteiro
        milhares = match.group(1)
        centenas = match.group(2)
        valor_str = milhares + centenas
        valor = int(valor_str)
        
        if 70000 < valor < 300000:
            preco = valor

    return texto_bruto, preco

def main():
    print("="*60)
    print(" 🧪 TESTE DE COLETA (ÂNCORA NO PONTO) ")
    print("="*60)

    if not os.path.exists(ARQUIVO_CONFIG):
        print(f"[ERRO] Arquivo '{ARQUIVO_CONFIG}' não encontrado! Rode o 'mapear_regiao.py' primeiro.")
        return

    with open(ARQUIVO_CONFIG, 'r', encoding='utf-8') as f:
        regiao = json.load(f)
    print(f"[OK] Lendo a região: {regiao}")
    print("[INFO] Pressione CTRL+C para parar.\n")

    try:
        while True:
            texto_bruto, preco = testar_extracao(regiao)
            agora = time.strftime('%H:%M:%S')

            if preco:
                print(f"[{agora}] 🎯 SUCESSO! Texto Bruto na Tela: '{texto_bruto}' | Preço Extraído: {preco}")
            else:
                print(f"[{agora}] ⏳ Buscando o ponto '.'... (Lido: '{texto_bruto}')", end="\r")

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\nTeste finalizado.")

if __name__ == "__main__":
    main()
```
