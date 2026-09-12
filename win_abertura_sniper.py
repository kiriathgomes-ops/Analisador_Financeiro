import cv2
import numpy as np
import mss
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import time
import re
import csv
import os
import json
import shutil
from datetime import datetime
from collections import deque

# ==================== CONFIGURAÇÕES DE PASTAS ====================
PASTA_COLETAS = "Coletas"
os.makedirs(PASTA_COLETAS, exist_ok=True)

ARQUIVO_CSV = os.path.join(PASTA_COLETAS, "preco_teorico_win_fluxo.csv")
ARQUIVO_CONFIG = os.path.join(PASTA_COLETAS, "config_regiao.json")
ARQUIVO_JSON_MACRO = os.path.join(PASTA_COLETAS, "DadosAtivosUnificados.json")
ARQUIVO_JSON_SMC = os.path.join(PASTA_COLETAS, "AnaliseGraficaSMC_Regras.json")

# Configurações do Leitor
INTERVALO = 0.25
TAMANHO_JANELA_TENDENCIA = 40  # ~10 segundos de memória do leilão

# TRATAMENTO DINÂMICO DO TESSERACT
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
# =================================================================

def carregar_contextos():
    """Lê os arquivos JSON da pasta Coletas para formar a visão Macro e Institucional."""
    contexto = {
        "vies_macro": "NEUTRO", 
        "score_macro": 0,
        "win_ajuste": 0,
        "win_fechamento": 0,
        "vies_smc": "NEUTRO",
        "poc_ontem": 0
    }
    
    # 1. Carregar Macro (32 Ativos)
    try:
        with open(ARQUIVO_JSON_MACRO, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            ativos = dados.get("ativos", {})
            ewz_var = ativos.get("EWZ", {}).get("variacao_pct", 0)
            sp500_var = ativos.get("SP500_FUT", {}).get("variacao_pct", 0)
            petr_var = ativos.get("PETR_ADR", {}).get("variacao_pct", 0)
            vale_var = ativos.get("VALE_ADR", {}).get("variacao_pct", 0)
            
            contexto["win_ajuste"] = ativos.get("WIN_AJUSTE", {}).get("preco", 0)
            contexto["win_fechamento"] = ativos.get("WIN_LAST_TICK", {}).get("preco", 0)
            
            score = ((ewz_var * 2) + sp500_var + petr_var + vale_var) / 5
            contexto["score_macro"] = score
            if score > 0.4: contexto["vies_macro"] = "ALTA"
            elif score < -0.4: contexto["vies_macro"] = "BAIXA"
    except Exception as e:
        print(f"[AVISO] Falha ao ler Macro: {e}")

    # 2. Carregar SMC (Institucional)
    try:
        with open(ARQUIVO_JSON_SMC, 'r', encoding='utf-8') as f:
            smc = json.load(f)
            contexto["poc_ontem"] = smc.get("niveis_institucionais", {}).get("poc_ontem", 0)
            contexto["vies_smc"] = smc.get("bias_direcional", "NEUTRO")
    except Exception as e:
        print(f"[AVISO] Falha ao ler SMC: {e}")

    return contexto

def calcular_confluencia(preco_teorico, contexto, tendencia_micro):
    """Gera o painel de leitura do Gap e o Veredito de Entrada."""
    ajuste = contexto["win_ajuste"]
    fechamento = contexto["win_fechamento"]
    poc = contexto["poc_ontem"]
    
    gap_ajuste_pts = preco_teorico - ajuste if ajuste > 0 else 0
    gap_fechamento_pts = preco_teorico - fechamento if fechamento > 0 else 0
    distancia_poc = preco_teorico - poc if poc > 0 else 0
    
    posicao_ajuste = "ACIMA" if gap_ajuste_pts > 0 else "ABAIXO" if gap_ajuste_pts < 0 else "NO AJUSTE"
    posicao_fechamento = "ACIMA" if gap_fechamento_pts > 0 else "ABAIXO" if gap_fechamento_pts < 0 else "NO FECHAMENTO"
    posicao_poc = "ACIMA" if distancia_poc > 0 else "ABAIXO" if distancia_poc < 0 else "NA POC"
    
    vies_geral = contexto["vies_macro"]
    if contexto["vies_macro"] == "ALTA" and contexto["vies_smc"] == "ALTA":
        vies_geral = "FORTE ALTA"
    elif contexto["vies_macro"] == "BAIXA" and contexto["vies_smc"] == "BAIXA":
        vies_geral = "FORTE BAIXA"

    veredito = "AGUARDAR 🕒"
    if "ALTA" in vies_geral and tendencia_micro == "ALTA":
        veredito = "🟢 COMPRA A MERCADO (Confluência Macro + Fluxo)"
    elif "BAIXA" in vies_geral and tendencia_micro == "BAIXA":
        veredito = "🔴 VENDA A MERCADO (Confluência Macro + Fluxo)"
    elif tendencia_micro != "LATERAL":
        veredito = "⚠️ ALERTA DE FINTA (Fluxo divergente do Macro)"

    return gap_ajuste_pts, posicao_ajuste, gap_fechamento_pts, posicao_fechamento, distancia_poc, posicao_poc, veredito, vies_geral

def melhorar_para_ocr(img_pil):
    img = img_pil.convert('L')
    img = ImageEnhance.Contrast(img).enhance(3.0)
    img = img.filter(ImageFilter.SHARPEN)
    w, h = img.size
    return img.resize((w * 4, h * 4), Image.LANCZOS)

def extrair_numero(img_pil):
    try:
        img_proc = melhorar_para_ocr(img_pil)
        config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.'
        texto_bruto = pytesseract.image_to_string(img_proc, config=config).strip()
        
        # Âncora no ponto: busca o padrão exato de 3 dígitos, ponto, 3 dígitos (ex: 189.142)
        match = re.search(r'(\d{3})\.(\d{3})', texto_bruto)
        if match:
            valor_str = match.group(1) + match.group(2)
            preco_int = int(valor_str)
            if 70000 < preco_int < 300000:
                return preco_int, 0.95
    except:
        pass
    return None, 0.0

def capturar_regiao(regiao):
    with mss.MSS() as sct:
        img = sct.grab(regiao)
        return Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")

def analisar_fluxo(historico):
    if len(historico) < 10: return "LATERAL", 0
    metade = len(historico) // 2
    media_antiga = sum(list(historico)[:metade]) / metade
    media_recente = sum(list(historico)[metade:]) / (len(historico) - metade)
    dif = media_recente - media_antiga
    if dif > 2.5: return "ALTA", dif
    if dif < -2.5: return "BAIXA", dif
    return "LATERAL", dif

def salvar_csv(preco, confianca):
    existe = os.path.isfile(ARQUIVO_CSV)
    with open(ARQUIVO_CSV, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not existe: writer.writerow(["DataHora", "PrecoTeorico", "Confianca"])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], preco, f"{confianca:.3f}"])

def main():
    print("="*60)
    print(" 🎯 SNIPER DE LEILÃO (ÂNCORA NO PONTO) ")
    print("="*60)

    if not os.path.exists(ARQUIVO_CONFIG):
        print(f"[ERRO CRÍTICO] Arquivo de mapeamento '{ARQUIVO_CONFIG}' não encontrado!")
        print("Execute o script 'mapear_regiao.py' primeiro.")
        return

    with open(ARQUIVO_CONFIG, 'r', encoding='utf-8') as f:
        regiao = json.load(f)
    print(f"[OK] Coordenadas carregadas: {regiao}")

    contexto = carregar_contextos()
    print(f"[INFO] Macro Vies: {contexto['vies_macro']} | SMC Vies: {contexto['vies_smc']}")
    print(f"[INFO] Ajuste: {contexto['win_ajuste']} | Fechamento: {contexto['win_fechamento']} | POC: {contexto['poc_ontem']}")

    print("\n" + "="*60)
    print(" 🚀 MONITORAMENTO DE LEILÃO ATIVO (Pressione CTRL+C p/ sair)")
    print("="*60 + "\n")

    ultimo_preco = None
    historico = deque(maxlen=TAMANHO_JANELA_TENDENCIA)

    try:
        while True:
            img = capturar_regiao(regiao)
            preco, conf = extrair_numero(img)
            agora = datetime.now().strftime('%H:%M:%S')

            if preco:
                historico.append(preco)
                tendencia_micro, forca = analisar_fluxo(historico)
                
                if preco != ultimo_preco:
                    gap_ajuste, pos_ajuste, gap_fechamento, pos_fechamento, dist_poc, pos_poc, veredito, vies_geral = calcular_confluencia(preco, contexto, tendencia_micro)
                    
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(f"=== 🕒 {agora} | PREVISÃO DE ABERTURA ===")
                    print(f"💰 PREÇO TEÓRICO : {preco} (Conf: {conf:.2f})")
                    print(f"📊 GAP DO AJUSTE : {gap_ajuste:+.0f} pts [{pos_ajuste}]")
                    print(f"📉 GAP DO FECHTO : {gap_fechamento:+.0f} pts [{pos_fechamento}]")
                    print(f"🏢 DISTÂNCIA POC : {dist_poc:+.0f} pts [{pos_poc}]")
                    print(f"🌊 MICROFLUXO    : {tendencia_micro} (Força/Aceleração: {forca:+.1f})")
                    print("-" * 40)
                    print(f"🎯 VEREDITO      : {veredito}")
                    print("="*40)
                    
                    salvar_csv(preco, conf)
                    ultimo_preco = preco
            else:
                print(f"[{agora}] Buscando âncora do ponto (.) na região...", end="\r")

            time.sleep(INTERVALO)

    except KeyboardInterrupt:
        print(f"\n\nFinalizado! Dados armazenados em {PASTA_COLETAS}/")

if __name__ == "__main__":
    main()