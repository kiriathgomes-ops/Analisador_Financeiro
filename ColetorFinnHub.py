import os
import requests
import pandas as pd
from dotenv import load_dotenv

# Carrega as variáveis declaradas no arquivo .env para o ambiente
load_dotenv()

# Obtém a API Key da variável de ambiente
API_KEY = os.getenv('FINNHUB_API_KEY')

# Validação básica de segurança
if not API_KEY:
    raise ValueError("A chave 'FINNHUB_API_KEY' não foi encontrada no arquivo .env!")

# Lista das principais ADRs brasileiras
#ADRS_BRASIL = ['VALE', 'PBR', 'ITUB', 'BBD', 'ABEV', 'EBR', 'GGB', 'SUZ']
# Tickers das ADRs/ETFs do seu sistema para usar na API Finnhub
ADRS_BRASIL = [
    'EWZ',   # ETF Principal Brasil
    'VALE',  # Vale
    'PBR',   # Petrobras ON
    'ITUB',  # Itaú Unibanco
    'BBD',   # Bradesco PN
    'SPY',   # S&P 500 ETF
    'QQQ',   # Nasdaq 100 ETF
]



def obter_cotacao_adr(ticker):
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if 'c' in data and data['c'] != 0:
            return {
                'Ticker': ticker,
                'Preco': data['c'],
                'Variacao_%': round(data['dp'], 2),
                'Variacao_$': round(data['d'], 2),
                'Abertura': data['o'],
                'Maxima': data['h'],
                'Minima': data['l'],
                'Fechamento_Anterior': data['pc']
            }
    except Exception as e:
        print(f"Erro ao coletar {ticker}: {e}")
    return None

# Loop de coleta
resultados = []
for adr in ADRS_BRASIL:
    info = obter_cotacao_adr(adr)
    if info:
        resultados.append(info)

df_adrs = pd.DataFrame(resultados)
print(df_adrs)