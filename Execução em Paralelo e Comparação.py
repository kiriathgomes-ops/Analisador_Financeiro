import os
import time
import pandas as pd
import MetaTrader5 as mt5
import requests
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()
FINNHUB_KEY = os.getenv('FINNHUB_API_KEY')

# Listas de Ativos
MAPEAMENTO_ATIVOS = {
    'VALE3': 'VALE',
    'PETR4': 'PBR-A',
    'PETR3': 'PBR',
    'ITUB4': 'ITUB',
    'BBDC4': 'BBD'
}

# -------------------------------------------------------------------
# 1. TAREFA PARALELA A: Coleta de Dados Globais via Finnhub (API REST)
# -------------------------------------------------------------------
def coletar_dados_finnhub():
    """Coleta pré-market de EWZ, SPY e ADRs simultaneamente."""
    tickers = ['EWZ', 'SPY', 'QQQ', 'VALE', 'PBR', 'PBR-A', 'ITUB', 'BBD']
    resultados = {}
    
    def buscar_quote(ticker):
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}"
        try:
            res = requests.get(url, timeout=5).json()
            if 'dp' in res and res['dp'] is not None:
                return ticker, round(res['dp'], 2)
        except Exception:
            pass
        return ticker, 0.0

    # Paraleliza também as requisições HTTP individuais do Finnhub
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(buscar_quote, t) for t in tickers]
        for f in futures:
            t, val = f.result()
            resultados[t] = val
            
    return resultados

# -------------------------------------------------------------------
# 2. TAREFA PARALELA B: Coleta de Dados de Leilão/Mercado via MT5
# -------------------------------------------------------------------
def coletar_dados_mt5():
    """Coleta o estado do leilão e preço atual do WIN e ações no MT5."""
    if not mt5.initialize():
        return {'erro': 'Falha MT5'}
    
    dados_mt5 = {}
    
    # Coleta WIN$
    info_win = mt5.symbol_info("WIN$")
    tick_win = mt5.symbol_info_tick("WIN$")
    if info_win and tick_win and info_win.session_close > 0:
        var_win = ((tick_win.last / info_win.session_close) - 1) * 100
        dados_mt5['WIN$'] = {
            'ultimo': tick_win.last,
            'fechamento_ant': info_win.session_close,
            'var_%': round(var_win, 2)
        }
    
    # Coleta leilão/tick das ações B3
    dados_mt5['acoes'] = {}
    for ticker_b3 in MAPEAMENTO_ATIVOS.keys():
        info = mt5.symbol_info(ticker_b3)
        tick = mt5.symbol_info_tick(ticker_b3)
        if info and tick and info.session_close > 0:
            var_acao = ((tick.last / info.session_close) - 1) * 100
            dados_mt5['acoes'][ticker_b3] = {
                'preco_leilao': tick.last,
                'var_%': round(var_acao, 2)
            }

    mt5.shutdown()
    return dados_mt5

# -------------------------------------------------------------------
# 3. CONSOLIDADOR PARALELO (Executa A e B juntas)
# -------------------------------------------------------------------
def executar_analise_paralela_comparativa():
    inicio = time.time()
    
    # Dispara as duas coletas em threads separadas ao mesmo tempo
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_finnhub = executor.submit(coletar_dados_finnhub)
        future_mt5 = executor.submit(coletar_dados_mt5)
        
        dados_finnhub = future_finnhub.result()
        dados_mt5 = future_mt5.result()
        
    tempo_execucao = round(time.time() - inicio, 2)
    
    # ---------------------------------------------------------------
    # 4. COMPARAÇÃO E CONSOLIDAÇÃO DOS DADOS
    # ---------------------------------------------------------------
    # A) Métrica 1: Projeção Teórica do WIN (Baseada puramente em NY)
    var_ewz = dados_finnhub.get('EWZ', 0.0)
    var_spy = dados_finnhub.get('SPY', 0.0)
    var_vale_adr = dados_finnhub.get('VALE', 0.0)
    var_pbr_adr = dados_finnhub.get('PBR', 0.0)
    
    projecao_win_ny = round((var_ewz * 0.35) + (var_spy * 0.25) + (var_vale_adr * 0.20) + (var_pbr_adr * 0.20), 2)
    
    # B) Métrica 2: Situação Real do WIN no MT5
    win_real_info = dados_mt5.get('WIN$', {})
    var_win_real = win_real_info.get('var_%', 0.0)
    
    # C) Comparativos de Arbitragem Ações vs ADRs
    comparativo_acoes = []
    acoes_mt5 = dados_mt5.get('acoes', {})
    
    for acao_b3, adr_ny in MAPEAMENTO_ATIVOS.items():
        var_adr = dados_finnhub.get(adr_ny, 0.0)
        var_b3 = acoes_mt5.get(acao_b3, {}).get('var_%', 0.0)
        spread = round(var_adr - var_b3, 2)
        
        comparativo_acoes.append({
            'Ativo': acao_b3,
            'Var_B3_%': var_b3,
            'ADR_NY': adr_ny,
            'Var_ADR_%': var_adr,
            'Spread_%': spread
        })

    # Tabela final de comparação
    df_comparativo_acoes = pd.DataFrame(comparativo_acoes)
    
    return {
        'tempo_execucao_s': tempo_execucao,
        'projecao_win_ny_%': projecao_win_ny,
        'var_win_real_mt5_%': var_win_real,
        'descasamento_win_%': round(projecao_win_ny - var_win_real, 2),
        'tabela_acoes': df_comparativo_acoes,
        'dados_brutos_finnhub': dados_finnhub
    }

# -------------------------------------------------------------------
# TESTE DE EXECUÇÃO
# -------------------------------------------------------------------
if __name__ == "__main__":
    res = executar_analise_paralela_comparativa()
    
    print(f"\n Análise concluída em {res['tempo_execucao_s']} segundos em paralelo!\n")
    print("=== 1. COMPARAÇÃO DE MODELOS PARA O WIN FUTURO ===")
    print(f"Modelo A (Projeção Externa NY): {res['projecao_win_ny_%']}%")
    print(f"Modelo B (Preço Real/Leilão MT5): {res['var_win_real_mt5_%']}%")
    print(f"Diferença / Descasamento WIN:  {res['descasamento_win_%']}%\n")
    
    print("=== 2. COMPARAÇÃO AÇÕES B3 (LEILÃO) VS ADRs (NY) ===")
    print(res['tabela_acoes'].to_string(index=False))