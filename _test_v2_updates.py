from v2.core.engines.decision_engine import DecisionEngine
from v2.core.contracts.market_context import MarketContext, AtivoSnapshot
from datetime import datetime

# Simula um mercado SEM pivots (metadados vazios)
mock_market = MarketContext(
    timestamp=datetime.now(),
    win_fut=AtivoSnapshot(preco=177000.0, variacao_pct=-15.0),
    wdo_fut=AtivoSnapshot(preco=5420.0, variacao_pct=9.0),
    win_ajuste=208000.0, wdo_ajuste=5000.0, ptax=5.5,
    sp500=AtivoSnapshot(0,0), nasdaq=AtivoSnapshot(0,0),
    vix=AtivoSnapshot(0,0), dxy=AtivoSnapshot(0,0), ewz=AtivoSnapshot(0,0),
    iron_ore=AtivoSnapshot(0,0), crude_oil=AtivoSnapshot(0,0), gold=AtivoSnapshot(0,0),
    metadados={"pivots": {}} # <--- SEM PIVOTS AQUI
)

engine = DecisionEngine(ativo="WIN")
confluence_falsa = {"vies": "COMPRA", "confianca": 80, "motivos": ["Teste"], "riscos": []}

print("--- TESTANDO DECISION ENGINE SEM PIVOTS ---")
res = engine.gerar_decisao(confluence_result=confluence_falsa, market=mock_market)

print(f"Viés Final : {res.vies_final}")
print(f"Entrada    : {res.entrada}")
print(f"Inválidação: {res.invalidacao}")

if res.vies_final == "NEUTRO" and res.entrada is None:
    print("✅ SUCESSO: O motor bloqueou a operação porque não havia pivôs reais!")
else:
    print("❌ FALHA: O motor inventou uma entrada!")