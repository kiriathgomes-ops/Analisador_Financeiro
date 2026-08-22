# ============================================================
# ARQUIVO: Validador.py
# DATA: 30/07/2026
# AUTOR: Arquiteto de Sistemas
# MOTIVO: Fase 3 - Validação, sanitização e padronização dos 
#         32 ativos (com WIN e WDO Ajustes separados).
# DESCRICAO:
#   Processa o arquivo JSON bruto oriundo da fase de coleta,
#   aplica regras de negócio para consistência de dados, 
#   padroniza os identificadores dos ativos (tickers) e 
#   gera um arquivo JSON estruturado para consumo posterior.
# ============================================================

import json
import os
from datetime import datetime

# ------------------------------------------------------------
# CONFIGURAÇÃO DE DIRETÓRIOS E CAMINHOS DE ARQUIVOS
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")

# Arquivo JSON de entrada gerado pelo pipeline de coleta
FILE_INPUT = os.path.join(COLETAS_DIR, "Coleta_rom-0.json")

# Arquivo JSON de saída com o payload limpo e o relatório de auditoria
FILE_OUTPUT = os.path.join(COLETAS_DIR, "Dados_Validados.json")

# ------------------------------------------------------------
# DICIONÁRIO DE PADRONIZAÇÃO DE TICKERS (DE-PARA)
# Mapeia os símbolos brutos das fontes de dados externas para 
# os identificadores internos padronizados do sistema.
# ------------------------------------------------------------
MAPEAMENTO_TICKERS = {
    # Moedas e Indicadores Oficiais
    "USD_PTAX": "USD_PTAX",
    "B3_AJUSTE_WIN": "WIN_AJUSTE",
    "B3_AJUSTE_WDO": "WDO_AJUSTE",
    
    # Futuros B3
    "BMFBOVESPA:WIN1!": "WIN_FUT",
    "BMFBOVESPA:WDO1!": "WDO_FUT",
    "BMFBOVESPA:DI1F2027": "DI1_2027",
    "BMFBOVESPA:DI1F2029": "DI1_2029",
    
    # Índices e Commodities Globais
    "TVC:VIX": "VIX",
    "SGX:FEF1!": "IRON_ORE",
    "SGX:FEF2!": "IRON_ORE_2M",
    "NYMEX:CL1!": "CRUDE_OIL",
    "CME_MINI:ES1!": "SP500_FUT",
    "CME_MINI:NQ1!": "NASDAQ_FUT",
    "TVC:DXY": "DXY",
    "FX_IDC:USDMXN": "USD_MXN",
    "TVC:GOLD": "GOLD",
    "FX_IDC:USDBRL": "USD_BRL",
    
    # ADRs no Mercado Americano (NYSE/AMEX/OTC)
    "NYSE:VALE": "VALE_ADR",
    "NYSE:PBR": "PETR_ADR",
    "NYSE:ITUB": "ITUB_ADR",
    "OTC:BDORY": "BBAS_ADR",
    "NYSE:BBD": "BBD_ADR",
    "OTC:BOLSY": "B3_ADR",
    "AMEX:EWZ": "EWZ"
}

def validar_item(item):
    """
    Executa regras estritas de validação, integridade e sanitização em um item.

    Parâmetros:
        item (dict): Registro individual extraído da lista de coletas.

    Retorno:
        tuple (bool, str, dict):
            - bool: True se o item for válido, False caso contrário.
            - str: Mensagem descritiva do resultado da auditoria.
            - dict: Dicionário sanitizado se aprovado, None se rejeitado.
    """
    ativo_raw = item.get("ativo")
    status_fonte = item.get("status")
    dados = item.get("dados_reais")
    
    # 1. Validação do Status da Coleta e Estrutura dos Dados
    if status_fonte != "OK" or not dados:
        return False, f"Status de coleta inválido: {status_fonte}", None
        
    close = dados.get("close")
    
    # 2. Validação do Preço/Taxa de Fechamento (obrigatório, numérico e estritamente positivo)
    if close is None or not isinstance(close, (int, float)) or close <= 0:
        return False, f"Preço/Taxa de fechamento inválido ou zerado: {close}", None
        
    # 3. Mapeamento para Identificador Padrão Interno
    nome_padronizado = MAPEAMENTO_TICKERS.get(ativo_raw, ativo_raw)
    
    # 4. Sanitização e Normalização dos Tipos de Dados
    dados_sanitizados = {
        "ativo_id": nome_padronizado,
        "ticker_original": ativo_raw,
        "fonte": item.get("fonte"),
        "timestamp_coleta": item.get("timestamp"),
        "close": float(close),
        "open": float(dados["open"]) if dados.get("open") is not None else None,
        "high": float(dados["high"]) if dados.get("high") is not None else None,
        "low": float(dados["low"]) if dados.get("low") is not None else None,
        "change_percent": float(dados["change_percent"]) if dados.get("change_percent") is not None else None,
        "volume": float(dados["volume"]) if dados.get("volume") is not None else None
    }

    return True, "Aprovado", dados_sanitizados

def executar_validacao():
    """
    Orquestra o processo de validação do arquivo de coleta.
    
    Passos:
        1. Carrega o arquivo JSON bruto de entrada.
        2. Itera sobre cada ativo aplicando as regras de auditoria.
        3. Exibe o log em tempo real no console formatado em colunas.
        4. Consolida e grava os ativos aprovados e o relatório de rejeições na saída.
    """
    # Verificação de existência do arquivo de entrada
    if not os.path.exists(FILE_INPUT):
        print(f"[ERRO] Arquivo de entrada não encontrado: {FILE_INPUT}")
        return False
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Lendo {os.path.basename(FILE_INPUT)}...")
    
    with open(FILE_INPUT, 'r', encoding='utf-8') as f:
        coleta = json.load(f)
        
    itens = coleta.get("coletas", [])
    aprovados = []
    rejeitados = []
    
    # Cabeçalho da Tabela de Auditoria no Terminal
    print(f"\n{'ATIVO ORIGINAL':<22} | {'ID PADRÃO':<14} | {'PREÇO/TAXA':<10} | {'STATUS AUDITORIA'}")
    print("-" * 75)
    
    # Loop principal de auditoria dos ativos
    for item in itens:
        valido, motivo, dados_limpos = validar_item(item)
        ativo_raw = item.get("ativo", "UNKNOWN")
        id_padrao = MAPEAMENTO_TICKERS.get(ativo_raw, ativo_raw)
        
        if valido:
            aprovados.append(dados_limpos)
            print(f"{ativo_raw:<22} | {id_padrao:<14} | {dados_limpos['close']:<10.4f} | [OK] {motivo}")
        else:
            rejeitados.append({"ativo": ativo_raw, "motivo": motivo})
            print(f"{ativo_raw:<22} | {id_padrao:<14} | N/A        | [REJEITADO] {motivo}")
            
    print("-" * 75)
    
    # Estruturação da Carga Útil de Saída e Metadados
    saida = {
        "metadata_validacao": {
            "timestamp_validacao": datetime.now().isoformat(),
            "arquivo_origem": os.path.basename(FILE_INPUT),
            "total_recebidos": len(itens),
            "total_aprovados": len(aprovados),
            "total_rejeitados": len(rejeitados)
        },
        "ativos_validados": aprovados,
        "relatorio_rejeicoes": rejeitados
    }
    
    # Gravando o arquivo processado e higienizado
    with open(FILE_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(saida, f, indent=2, ensure_ascii=False)
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Validação concluída!")
    print(f"Aprovados: {len(aprovados)}/{len(itens)} | Arquivo gerado: {os.path.basename(FILE_OUTPUT)}\n")
    return len(rejeitados) == 0

# ------------------------------------------------------------
# PONTO DE ENTRADA DO SCRIPT
# ------------------------------------------------------------
if __name__ == "__main__":
    print("============================================================")
    print(" FASE 3: ENGINE DE VALIDAÇÃO E SANITIZAÇÃO DE DADOS (32 ATIVOS)")
    print("============================================================")
    executar_validacao()