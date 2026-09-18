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
from datetime import datetime, time as dt_time
from collections import deque

# ==================== CONFIGURAÇÕES DE PASTAS ====================
PASTA_COLETAS = "Coletas"
PASTA_HISTORICO = os.path.join(PASTA_COLETAS, "coleta_preco_teorico_historico")
os.makedirs(PASTA_COLETAS, exist_ok=True)
os.makedirs(PASTA_HISTORICO, exist_ok=True)

ARQUIVO_CSV = os.path.join(PASTA_COLETAS, "preco_teorico_win_fluxo.csv")
ARQUIVO_CONFIG = os.path.join(PASTA_COLETAS, "config_regiao.json")
ARQUIVO_JSON_MACRO = os.path.join(PASTA_COLETAS, "DadosAtivosUnificados.json")
ARQUIVO_JSON_SMC = os.path.join(PASTA_COLETAS, "AnaliseGraficaSMC_Regras.json")

# Configurações do Leitor
INTERVALO = 0.25
TAMANHO_JANELA_TENDENCIA = 40  # ~10 segundos de memória do leilão
INTERVALO_FORCAR_GRAVACAO = 10.0  # segundos

# ============================================================
# FILTRO DE SANIDADE DO PREÇO
# ============================================================
# Limite absoluto: WIN nunca esteve fora dessa faixa na história
PRECO_MIN_ABSOLUTO = 50000
PRECO_MAX_ABSOLUTO = 300000

# Salto máximo aceito (em pontos) entre leituras consecutivas.
# Para replay acelerado, aumentar (ex: 2000). Para mercado real, 500 é OK.
LIMITE_SALTO_PTS = 1000

# Quantas leituras anteriores usar como referência de "regime atual"
JANELA_REFERENCIA = 5

# Janela de LEILÃO — durante esse período o preço teórico oscila MUITO
# (é descoberta de preço). O filtro de salto vs mediana é DESABILITADO.
LEILAO_INICIO = dt_time(8, 50)
LEILAO_FIM = dt_time(9, 5)


def _esta_no_leilao() -> bool:
    """True se estiver na janela de leilão (08:50–09:05)."""
    agora = datetime.now().time()
    return LEILAO_INICIO <= agora <= LEILAO_FIM
# ============================================================

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


# ============================================================
# ROTAÇÃO DIÁRIA DO CSV
# ============================================================
def _parse_data(texto: str):
    texto = texto.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(texto, fmt)
        except ValueError:
            continue
    return None


def _ultima_data_no_csv() -> datetime:
    if not os.path.exists(ARQUIVO_CSV):
        return None

    ultima = None
    try:
        with open(ARQUIVO_CSV, "r", encoding="utf-8-sig") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or not linha[0].isdigit():
                    continue
                partes = linha.split(",")
                if not partes:
                    continue
                dt = _parse_data(partes[0])
                if dt:
                    ultima = dt
    except Exception:
        return None

    return ultima


def rotacionar_csv_se_necessario():
    ultima_data = _ultima_data_no_csv()
    if ultima_data is None:
        return

    hoje = datetime.now().date()
    if ultima_data.date() == hoje:
        return

    data_ref = ultima_data.date().isoformat()
    nome_hist = f"preco_teorico_{data_ref}.csv"
    destino = os.path.join(PASTA_HISTORICO, nome_hist)

    if os.path.exists(destino):
        try:
            with open(destino, "r", encoding="utf-8-sig") as f:
                linhas_hist = f.readlines()
            with open(ARQUIVO_CSV, "r", encoding="utf-8-sig") as f:
                linhas_novas = f.readlines()

            if linhas_novas and linhas_novas[0].lower().startswith("datahora"):
                linhas_novas = linhas_novas[1:]

            with open(destino, "w", encoding="utf-8") as f:
                f.writelines(linhas_hist)
                f.writelines(linhas_novas)

            os.remove(ARQUIVO_CSV)
            print(f"📦 CSV rotacionado (concat): {nome_hist} (+{len(linhas_novas)} linhas)")
        except Exception as e:
            print(f"⚠️ Falha ao concatenar: {e}")
    else:
        try:
            shutil.move(ARQUIVO_CSV, destino)
            print(f"📦 CSV rotacionado: {nome_hist}")
        except Exception as e:
            print(f"⚠️ Falha ao mover: {e}")
# ============================================================


# ============================================================
# FILTRO DE SANIDADE DO PREÇO
# ============================================================
class FiltroPreco:
    """
    Filtra leituras absurdas do OCR.

    Comportamento:
      - Durante o leilão (08:50–09:05): valida APENAS faixa absoluta.
        O preço teórico pode ir de 187k → 200k → 185k em segundos — isso
        é descoberta de preço, NÃO ruído. Não usar mediana móvel.
      - Fora do leilão: valida faixa absoluta + salto vs mediana.

    Contadores internos (para relatório final):
      - rejeicoes_absoluta: quantas vezes caiu fora de [MIN, MAX]
      - rejeicoes_mediana:  quantas vezes passou da faixa absoluta mas
                            foi rejeitada por salto vs mediana
    """

    def __init__(self):
        self.ultimos_aceitos = deque(maxlen=JANELA_REFERENCIA)
        self.modo_leilao = False
        self.rejeicoes_absoluta = 0
        self.rejeicoes_mediana = 0

    def aceitar(self, preco: int) -> tuple:
        """
        Retorna (aceitar: bool, motivo: str).
        """
        no_leilao = _esta_no_leilao()

        # Detecta transição de modo (log único)
        if no_leilao != self.modo_leilao:
            if no_leilao:
                print("[FILTRO] Entrando em modo LEILÃO — filtro de salto DESABILITADO")
                self.ultimos_aceitos.clear()
            else:
                print("[FILTRO] Saindo do leilão — filtro de salto REATIVADO")
            self.modo_leilao = no_leilao

        # Camada 1 — faixa absoluta (sempre aplica)
        if preco < PRECO_MIN_ABSOLUTO or preco > PRECO_MAX_ABSOLUTO:
            self.rejeicoes_absoluta += 1
            return False, f"fora da faixa absoluta [{PRECO_MIN_ABSOLUTO}, {PRECO_MAX_ABSOLUTO}]"

        # Camada 2 — salto vs mediana (só FORA do leilão)
        if no_leilao:
            self.ultimos_aceitos.append(preco)
            return True, "OK_LEILAO"

        # Sem histórico → aceita
        if not self.ultimos_aceitos:
            self.ultimos_aceitos.append(preco)
            return True, "primeira leitura"

        # Regra 2: comparar com mediana
        lista_ordenada = sorted(self.ultimos_aceitos)
        n = len(lista_ordenada)
        if n % 2 == 1:
            mediana = lista_ordenada[n // 2]
        else:
            mediana = (lista_ordenada[n // 2 - 1] + lista_ordenada[n // 2]) / 2

        delta = abs(preco - mediana)
        if delta > LIMITE_SALTO_PTS:
            self.rejeicoes_mediana += 1
            return False, f"salto de {delta:+.0f} pts da mediana {mediana:.0f}"

        self.ultimos_aceitos.append(preco)
        return True, "OK"

    def resetar(self):
        self.ultimos_aceitos.clear()
# ============================================================


def carregar_contextos():
    contexto = {
        "vies_macro": "NEUTRO",
        "score_macro": 0,
        "win_ajuste": 0,
        "win_fechamento": 0,
        "vies_smc": "NEUTRO",
        "poc_ontem": 0,
    }

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
            if score > 0.4:
                contexto["vies_macro"] = "ALTA"
            elif score < -0.4:
                contexto["vies_macro"] = "BAIXA"
    except Exception as e:
        print(f"[AVISO] Falha ao ler Macro: {e}")

    try:
        with open(ARQUIVO_JSON_SMC, 'r', encoding='utf-8') as f:
            smc = json.load(f)
            contexto["poc_ontem"] = smc.get("niveis_institucionais", {}).get("poc_ontem", 0)
            contexto["vies_smc"] = smc.get("bias_direcional", "NEUTRO")
    except Exception as e:
        print(f"[AVISO] Falha ao ler SMC: {e}")

    return contexto


def calcular_confluencia(preco_teorico, contexto, tendencia_micro):
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
        # PSM 8 (single word) — melhor pra essa fonte do MT5
        config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789.'
        texto_bruto = pytesseract.image_to_string(img_proc, config=config).strip()

        # Aceita padrão "189.142" ou "189142.00"
        # Primeiro tenta o formato com ponto de milhar
        match = re.search(r'(\d{3})\.(\d{3})', texto_bruto)
        if match:
            valor_str = match.group(1) + match.group(2)
            preco_int = int(valor_str)
            if 70000 < preco_int < 300000:
                return preco_int, 0.95

        # Fallback: 6 dígitos seguidos (ex: "189142")
        match6 = re.search(r'\d{6}', texto_bruto.replace(".", "").replace(",", ""))
        if match6:
            preco_int = int(match6.group(0))
            if 70000 < preco_int < 300000:
                return preco_int, 0.90
    except:
        pass
    return None, 0.0


def capturar_regiao(regiao):
    with mss.MSS() as sct:
        img = sct.grab(regiao)
        return Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")


def analisar_fluxo(historico):
    if len(historico) < 10:
        return "LATERAL", 0
    metade = len(historico) // 2
    media_antiga = sum(list(historico)[:metade]) / metade
    media_recente = sum(list(historico)[metade:]) / (len(historico) - metade)
    dif = media_recente - media_antiga
    if dif > 2.5:
        return "ALTA", dif
    if dif < -2.5:
        return "BAIXA", dif
    return "LATERAL", dif


def salvar_csv(preco, confianca, motivo="MUDANCA"):
    existe = os.path.isfile(ARQUIVO_CSV)
    with open(ARQUIVO_CSV, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(["DataHora", "PrecoTeorico", "Confianca", "Motivo"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            preco,
            f"{confianca:.3f}",
            motivo,
        ])


def main():
    print("=" * 60)
    print(" 🎯 SNIPER DE LEILÃO (ÂNCORA NO PONTO) ")
    print("=" * 60)
    print(f" Modo: gravação por MUDANÇA + força a cada {INTERVALO_FORCAR_GRAVACAO:.0f}s")
    print(f" Filtro: faixa [{PRECO_MIN_ABSOLUTO}, {PRECO_MAX_ABSOLUTO}] | salto máx {LIMITE_SALTO_PTS} pts")
    print(f" Leilão: filtro de salto DESABILITADO entre {LEILAO_INICIO.strftime('%H:%M')} e {LEILAO_FIM.strftime('%H:%M')}")
    print(f" Rotação: CSV por dia em '{PASTA_HISTORICO}/'")
    print("=" * 60)

    rotacionar_csv_se_necessario()

    if not os.path.exists(ARQUIVO_CONFIG):
        print(f"[ERRO CRÍTICO] Arquivo de mapeamento '{ARQUIVO_CONFIG}' não encontrado!")
        return

    with open(ARQUIVO_CONFIG, 'r', encoding='utf-8') as f:
        regiao = json.load(f)
    print(f"[OK] Coordenadas carregadas: {regiao}")

    contexto = carregar_contextos()
    print(f"[INFO] Macro Vies: {contexto['vies_macro']} | SMC Vies: {contexto['vies_smc']}")
    print(f"[INFO] Ajuste: {contexto['win_ajuste']} | Fechamento: {contexto['win_fechamento']} | POC: {contexto['poc_ontem']}")

    print("\n" + "=" * 60)
    print(" 🚀 MONITORAMENTO DE LEILÃO ATIVO (Pressione CTRL+C p/ sair)")
    print("=" * 60 + "\n")

    ultimo_preco = None
    ultimo_salvamento_dt = None
    historico = deque(maxlen=TAMANHO_JANELA_TENDENCIA)
    filtro = FiltroPreco()

    total_tentativas = 0
    total_leituras_ok = 0
    total_leituras_falhas = 0
    total_rejeitadas_filtro = 0
    total_mudanca = 0
    total_forcado = 0

    try:
        while True:
            img = capturar_regiao(regiao)
            preco, conf = extrair_numero(img)
            agora_dt = datetime.now()
            agora = agora_dt.strftime('%H:%M:%S')

            total_tentativas += 1

            if preco:
                # ---- FILTRO DE SANIDADE ----
                aceitar, motivo_filtro = filtro.aceitar(preco)

                if not aceitar:
                    total_rejeitadas_filtro += 1
                    print(
                        f"[{agora}] 🚫 Preço rejeitado: {preco} ({motivo_filtro})",
                        end="\r",
                    )
                    time.sleep(INTERVALO)
                    continue

                total_leituras_ok += 1
                historico.append(preco)
                tendencia_micro, forca = analisar_fluxo(historico)

                mudou = (preco != ultimo_preco)
                precisa_forcar = (
                    ultimo_salvamento_dt is not None
                    and (agora_dt - ultimo_salvamento_dt).total_seconds() >= INTERVALO_FORCAR_GRAVACAO
                )

                if mudou or precisa_forcar:
                    # Marca motivo base
                    if mudou:
                        motivo_base = "MUDANCA"
                        total_mudanca += 1
                    else:
                        motivo_base = "FORCADO_TEMPO"
                        total_forcado += 1

                    # Sufixo [MODO_LEILAO] quando aplicável
                    if _esta_no_leilao():
                        motivo = f"{motivo_base}_LEILAO"
                    else:
                        motivo = motivo_base

                    gap_ajuste, pos_ajuste, gap_fechamento, pos_fechamento, dist_poc, pos_poc, veredito, vies_geral = calcular_confluencia(preco, contexto, tendencia_micro)

                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(f"=== 🕒 {agora} | PREVISÃO DE ABERTURA === [{motivo}]")
                    print(f"💰 PREÇO TEÓRICO : {preco} (Conf: {conf:.2f})")
                    print(f"📊 GAP DO AJUSTE : {gap_ajuste:+.0f} pts [{pos_ajuste}]")
                    print(f"📉 GAP DO FECHTO : {gap_fechamento:+.0f} pts [{pos_fechamento}]")
                    print(f"🏢 DISTÂNCIA POC : {dist_poc:+.0f} pts [{pos_poc}]")
                    print(f"🌊 MICROFLUXO    : {tendencia_micro} (Força/Aceleração: {forca:+.1f})")
                    print("-" * 40)
                    print(f"🎯 VEREDITO      : {veredito}")
                    print("=" * 40)

                    if motivo_base == "FORCADO_TEMPO":
                        print(f"⏱️  Gravação forçada: preço estável há {INTERVALO_FORCAR_GRAVACAO:.0f}s")
                    if _esta_no_leilao():
                        print(f"🎪 Modo LEILÃO ativo — filtro de salto relaxado")

                    print(
                        f"📊 Stats: {total_tentativas} tent | {total_leituras_ok} OK | "
                        f"{total_leituras_falhas} falhas OCR | "
                        f"{total_rejeitadas_filtro} rejeitadas filtro | "
                        f"{total_mudanca} mudança | {total_forcado} tempo"
                    )

                    salvar_csv(preco, conf, motivo)
                    ultimo_preco = preco
                    ultimo_salvamento_dt = agora_dt

            else:
                total_leituras_falhas += 1
                print(f"[{agora}] Buscando âncora do ponto (.) na região...", end="\r")

            time.sleep(INTERVALO)

    except KeyboardInterrupt:
        print(f"\n\nFinalizado! Dados armazenados em {PASTA_COLETAS}/")
        print("=" * 60)
        print(" 📊 ESTATÍSTICAS FINAIS")
        print("=" * 60)
        print(f"  Tentativas totais       : {total_tentativas}")
        print(f"  Leituras OK (aceitas)   : {total_leituras_ok}")
        print(f"  Leituras com falha OCR  : {total_leituras_falhas}")
        print(f"  Rejeitadas pelo filtro  : {total_rejeitadas_filtro}")
        print(f"      ├─ fora faixa abs.  : {filtro.rejeicoes_absoluta}")
        print(f"      └─ salto vs mediana : {filtro.rejeicoes_mediana}")
        print(f"  Gravações por mudança   : {total_mudanca}")
        print(f"  Gravações forçadas      : {total_forcado}")
        print(f"  Total gravado no CSV    : {total_mudanca + total_forcado}")
        print("=" * 60)


if __name__ == "__main__":
    main()
    