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