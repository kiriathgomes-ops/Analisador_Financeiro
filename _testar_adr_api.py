import json
import urllib.request
import urllib.error

# Lista exata das ADRs que usamos
adrs = {
    "VALE": "NYSE:VALE",
    "PETR": "NYSE:PBR",
    "ITUB": "NYSE:ITUB",
    "BBAS": "OTC:BDORY",
    "BBD": "NYSE:BBD",
    "B3": "OTC:BOLSY",
    "EWZ": "AMEX:EWZ"
}

print("=" * 80)
print(" 🔍 TESTE DIRETO NA API DA TRADINGVIEW (PRÉ-MARKET)")
print("=" * 80)

for nome, ticker_tv in adrs.items():
    url = (
        f"https://scanner.tradingview.com/symbol?"
        f"symbol={ticker_tv}&fields=close,change,premarket_close,premarket_change,postmarket_close,postmarket_change"
    )
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            
            print(f"\n📊 {nome} ({ticker_tv})")
            print(f"   Close (Fechamento) : {res.get('close')}")
            print(f"   Change (Var. Dia)  : {res.get('change')}%")
            print(f"   Pre-Market Close   : {res.get('premarket_close')}")
            print(f"   Pre-Market Change  : {res.get('premarket_change')}%")
            print(f"   Post-Market Close  : {res.get('postmarket_close')}")
            print(f"   Post-Market Change : {res.get('postmarket_change')}%")
            
            # Validação lógica
            pre_c = res.get('premarket_close')
            c = res.get('close')
            if pre_c and c and c > 0:
                var_calc = ((pre_c / c) - 1) * 100
                print(f"   ---")
                print(f"   Var. Real Calculada (Pre vs Close): {var_calc:+.2f}%")
                
    except Exception as e:
        print(f"\n❌ {nome}: Erro na API -> {e}")

print("\n" + "=" * 80)
