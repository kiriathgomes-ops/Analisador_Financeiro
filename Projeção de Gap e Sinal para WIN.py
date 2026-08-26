# ============================================================
# ARQUIVO: Projeção de Gap e Sinal para WIN.py (VERSÃO MODIFICADA)
# 
# OBJETIVO:
#   Calcular projeção de abertura do WIN usando WIN_LAST_TICK
#   como referência de fechamento anterior (em vez do MT5).
#
# FONTE DE DADOS:
#   - Finnhub (variações de EWZ, SPY, VALE, PBR)
#   - DadosAtivosUnificados.json (para WIN_LAST_TICK e WIN_AJUSTE)
#
# ALTERAÇÕES:
#   - Remove dependência direta do MT5 para obter o fechamento.
#   - Lê WIN_LAST_TICK do arquivo unificado (gerado pelo Coletor.py).
#   - Fallback para WIN_AJUSTE caso WIN_LAST_TICK não esteja disponível.
# ============================================================

import json
import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO DE DIRETÓRIOS E ARQUIVOS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
COLETAS_DIR = BASE_DIR / "Coletas"
ARQUIVO_ATIVOS = COLETAS_DIR / "DadosAtivosUnificados.json"

# Carrega a chave do Finnhub do .env
load_dotenv()
FINNHUB_KEY = os.getenv('FINNHUB_API_KEY')

# ============================================================
# PESOS DE INFLUÊNCIA PARA O WIN (mesmo do script original)
# ============================================================
PESOS_WIN = {
    'EWZ': 0.35,   # ETF Brasil em NY
    'SPY': 0.25,   # S&P 500 Futuro/Pré-market
    'VALE': 0.20,  # ADR Vale
    'PBR': 0.20    # ADR Petrobras
}

# ============================================================
# FUNÇÃO PARA CARREGAR WIN_LAST_TICK DO JSON UNIFICADO
# ============================================================
def obter_preco_referencia_win() -> float:
    """
    Lê o preço do WIN_LAST_TICK do DadosAtivosUnificados.json.
    Se não encontrar, tenta usar WIN_AJUSTE como fallback.
    Retorna 0.0 se nenhum estiver disponível.
    """
    if not ARQUIVO_ATIVOS.exists():
        print(f"[ERRO] Arquivo {ARQUIVO_ATIVOS} não encontrado. Execute o Coletor.py primeiro.")
        return 0.0

    try:
        with open(ARQUIVO_ATIVOS, "r", encoding="utf-8") as f:
            dados = json.load(f)
        
        ativos = dados.get("ativos", {})
        
        # 1. Tenta obter o WIN_LAST_TICK (prioridade máxima)
        win_last = ativos.get("WIN_LAST_TICK", {})
        preco = win_last.get("preco")
        if preco and isinstance(preco, (int, float)) and preco > 0:
            print(f"✅ Usando WIN_LAST_TICK como referência: {preco}")
            return float(preco)
        
        # 2. Fallback: WIN_AJUSTE (ajuste oficial da B3)
        win_ajuste = ativos.get("WIN_AJUSTE", {})
        preco = win_ajuste.get("preco")
        if preco and isinstance(preco, (int, float)) and preco > 0:
            print(f"⚠️ WIN_LAST_TICK não disponível. Usando WIN_AJUSTE como fallback: {preco}")
            return float(preco)
        
        # 3. Fallback final: WIN_FUT (último preço do contrato)
        win_fut = ativos.get("WIN_FUT", {})
        preco = win_fut.get("preco")
        if preco and isinstance(preco, (int, float)) and preco > 0:
            print(f"⚠️ Usando WIN_FUT como último recurso: {preco}")
            return float(preco)
        
        print("[ERRO] Nenhum preço de referência para o WIN encontrado no arquivo unificado.")
        return 0.0
        
    except Exception as e:
        print(f"[ERRO] Falha ao ler {ARQUIVO_ATIVOS}: {e}")
        return 0.0

# ============================================================
# FUNÇÃO PARA OBTER VARIAÇÃO DO FINNHUB (mantida igual)
# ============================================================
def obter_variacao_finnhub(ticker):
    """Puxa a variação % do pré-market/fechamento do ticker no Finnhub."""
    if not FINNHUB_KEY:
        print("[AVISO] FINNHUB_API_KEY não configurada.")
        return 0.0
    
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}"
    try:
        res = requests.get(url, timeout=5).json()
        if 'dp' in res and res['dp'] is not None:
            return round(res['dp'], 2)
    except Exception as e:
        print(f"Erro Finnhub ({ticker}): {e}")
    return 0.0

# ============================================================
# FUNÇÃO PRINCIPAL (MODIFICADA)
# ============================================================
def calcular_gap_win_futuro():
    """
    Calcula a variação teórica (%) e a projeção em PONTOS para o WIN,
    usando WIN_LAST_TICK como referência de fechamento anterior.
    """
    # 1. Coleta a variação dos ativos externos via Finnhub
    variacoes = {}
    var_teorica_pct = 0.0

    for ticker, peso in PESOS_WIN.items():
        var_pct = obter_variacao_finnhub(ticker)
        variacoes[ticker] = var_pct
        var_teorica_pct += var_pct * peso

    var_teorica_pct = round(var_teorica_pct, 2)
    print(f"📊 Variação teórica ponderada: {var_teorica_pct}%")

    # 2. Obtém o preço de referência (WIN_LAST_TICK) do arquivo unificado
    preco_referencia = obter_preco_referencia_win()
    
    if preco_referencia <= 0:
        print("[ERRO] Não foi possível obter um preço de referência válido.")
        return None

    # 3. Calcula a estimativa de preço de abertura e GAP em pontos
    preco_abertura_estimado = preco_referencia * (1 + (var_teorica_pct / 100))
    gap_pontos_estimado = round(preco_abertura_estimado - preco_referencia)

    # 4. Classificação do Viés
    if var_teorica_pct >= 0.30:
        vies = "COMPRADO (GAP DE ALTA)"
    elif var_teorica_pct <= -0.30:
        vies = "VENDIDO (GAP DE BAIXA)"
    else:
        vies = "NEUTRO (GAP PEQUENO / SEM TENDÊNCIA)"

    # 5. Retorna o resultado
    return {
        'Preco_Referencia_WIN': preco_referencia,         # WIN_LAST_TICK ou fallback
        'Fonte_Referencia': 'WIN_LAST_TICK' if preco_referencia else 'FALLBACK',
        'Var_Teorica_Projetada_%': var_teorica_pct,
        'Gap_Estimado_Pontos': gap_pontos_estimado,
        'Preco_Abertura_Projetado': round(preco_abertura_estimado),
        'Vies_Abertura': vies,
        'Detalhes_Ativos': variacoes
    }

# ============================================================
# EXECUÇÃO DIRETA
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print(" PROJEÇÃO DE ABERTURA DO WIN FUTURO (09:00)")
    print(" (usando WIN_LAST_TICK como referência)")
    print("=" * 60)
    
    resultado = calcular_gap_win_futuro()
    
    if resultado:
        print("\n=== RESULTADO DA PROJEÇÃO ===")
        for chave, valor in resultado.items():
            if chave == 'Detalhes_Ativos':
                print(f"{chave}:")
                for ativo, var in valor.items():
                    print(f"  • {ativo}: {var}%")
            else:
                print(f"{chave}: {valor}")
    else:
        print("❌ Falha ao calcular a projeção.")