# Coletor_MT5.py
"""
Módulo de Coleta MT5
================================
Coleta dados do MetaTrader5 para integração com o Analisador Financeiro
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path

# Adiciona a raiz ao path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from utils.KeyManager import key_manager  # Só para manter padrão

try:
    import MetaTrader5 as mt5
    MT5_DISPONIVEL = True
except ImportError:
    MT5_DISPONIVEL = False
    print("⚠️ MetaTrader5 não instalado. Execute: pip install MetaTrader5")

# ============================================================
# CONFIGURAÇÃO
# ============================================================

COLETAS_DIR = BASE_DIR / "Coletas"
ARQUIVO_MT5 = COLETAS_DIR / "Dados_MT5.json"

os.makedirs(COLETAS_DIR, exist_ok=True)

# Contratos disponíveis para consulta (ajuste conforme sua B3)
CONTRATOS_MT5 = {
    "WIN": ["WINV26", "WINZ26"],  # Contratos ativos
    "WDO": ["WDOQ26", "WDOV26", "WDOZ26"],  # Contratos ativos
    "DI1": ["DI1Q26", "DI1V26", "DI1Z26"],
}

# ============================================================
# FUNÇÃO PRINCIPAL DE COLETA
# ============================================================

def coletar_dados_mt5():
    """
    Coleta dados do MetaTrader5
    Retorna dict com os dados coletados
    """
    
    if not MT5_DISPONIVEL:
        return {
            "status": "ERRO",
            "mensagem": "MetaTrader5 não está instalado",
            "dados": None
        }
    
    # Inicializa o MT5
    if not mt5.initialize():
        return {
            "status": "ERRO",
            "mensagem": "Falha ao inicializar MetaTrader5",
            "dados": None
        }
    
    resultado = {
        "timestamp": datetime.now().isoformat(),
        "status": "OK",
        "contratos": {}
    }
    
    # Pega dados de todos os contratos
    for categoria, contratos in CONTRATOS_MT5.items():
        for contrato in contratos:
            try:
                # Verifica se o contrato existe
                if not mt5.symbol_select(contrato, True):
                    continue
                
                # Pega o tick atual
                tick = mt5.symbol_info_tick(contrato)
                if tick:
                    resultado["contratos"][contrato] = {
                        "bid": tick.bid,
                        "ask": tick.ask,
                        "last": tick.last,
                        "volume": tick.volume,
                        "time": datetime.fromtimestamp(tick.time).isoformat()
                    }
                    
            except Exception as e:
                print(f"⚠️ Erro ao coletar {contrato}: {e}")
    
    # Shutdown do MT5
    mt5.shutdown()
    
    return resultado

# ============================================================
# FUNÇÃO PARA SALVAR DADOS
# ============================================================

def salvar_dados_mt5(dados):
    """Salva os dados coletados em arquivo JSON"""
    with open(ARQUIVO_MT5, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Dados MT5 salvos em: {ARQUIVO_MT5}")
    return dados

# ============================================================
# FUNÇÃO PARA OBTER O MELHOR CONTRATO
# ============================================================

def obter_melhor_contrato(categoria="WIN"):
    """
    Retorna o contrato com dados mais recentes
    """
    dados = carregar_dados_mt5()
    if not dados or dados.get("status") != "OK":
        return None
    
    contratos = dados.get("contratos", {})
    categoria_contratos = CONTRATOS_MT5.get(categoria, [])
    
    for contrato in categoria_contratos:
        if contrato in contratos:
            return {
                "contrato": contrato,
                "last": contratos[contrato]["last"],
                "bid": contratos[contrato]["bid"],
                "ask": contratos[contrato]["ask"],
                "time": contratos[contrato]["time"]
            }
    
    return None

# ============================================================
# FUNÇÃO PARA CARREGAR DADOS SALVOS
# ============================================================

def carregar_dados_mt5():
    """Carrega dados salvos do arquivo JSON"""
    if not ARQUIVO_MT5.exists():
        return None
    
    try:
        with open(ARQUIVO_MT5, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

# ============================================================
# FUNÇÃO PARA INTEGRAR AO PIPELINE
# ============================================================

def executar_coleta_mt5():
    """
    Função principal para ser chamada pelo pipeline
    """
    print("\n" + "=" * 60)
    print("📊 COLETA MT5 - MERCADO B3")
    print("=" * 60)
    
    if not MT5_DISPONIVEL:
        print("❌ MetaTrader5 não disponível")
        return None
    
    print(f"🔄 Coletando dados do MetaTrader5...")
    dados = coletar_dados_mt5()
    
    if dados["status"] != "OK":
        print(f"❌ Erro: {dados['mensagem']}")
        return None
    
    salvar_dados_mt5(dados)
    
    # Exibe resumo
    print(f"\n📊 Contratos encontrados: {len(dados['contratos'])}")
    for contrato, info in dados['contratos'].items():
        print(f"   • {contrato}: Last {info['last']:.2f} | Bid {info['bid']:.2f} | Ask {info['ask']:.2f}")
    
    print("=" * 60)
    return dados

# ============================================================
# FUNÇÃO PARA OBTER AJUSTE OFICIAL (MT5)
# ============================================================

def obter_ajuste_mt5(contrato=None):
    """
    Obtém o preço de ajuste do contrato via MT5
    Pode ser usado como fallback para o ajuste oficial
    """
    if not MT5_DISPONIVEL:
        return None
    
    if not mt5.initialize():
        return None
    
    # Se não especificado, tenta achar o melhor contrato WIN
    if not contrato:
        for c in CONTRATOS_MT5["WIN"]:
            if mt5.symbol_select(c, True):
                contrato = c
                break
    
    if not contrato:
        mt5.shutdown()
        return None
    
    try:
        tick = mt5.symbol_info_tick(contrato)
        mt5.shutdown()
        
        if tick:
            return {
                "contrato": contrato,
                "preco": tick.last,
                "bid": tick.bid,
                "ask": tick.ask,
                "timestamp": datetime.now().isoformat()
            }
    except:
        mt5.shutdown()
        return None
    
    mt5.shutdown()
    return None

# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    executar_coleta_mt5()
    