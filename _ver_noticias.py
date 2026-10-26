import json

with open(r'Coletas\Noticias_Calendario.json', 'r', encoding='utf-8') as f:
    dados = json.load(f)

eventos = dados.get("calendario_eventos", {}).get("eventos", [])

print("=" * 70)
print(" 📰 NOTÍCIAS DO DIA (TradingView API)")
print("=" * 70)

if not eventos:
    print("⚠️ Nenhum evento encontrado no arquivo.")
else:
    for e in eventos:
        hora = e.get('hora', '?')
        nome = e.get('evento', '?')
        pais = e.get('pais', '?')
        estrelas = e.get('importancia', '?')
        atual = e.get('atual', '-')
        previsao = e.get('previsao', '-')
        print(f"[{hora}] {nome} ({pais})")
        print(f"       Estrelas: {estrelas} | Atual: {atual} | Previsão: {previsao}")
        print("-" * 70)