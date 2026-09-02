# -*- coding: utf-8 -*-
"""
Módulo: Gerar_Relatorio_Mensagem.py
Versão: 2.4 (Integração SMC / Volume Profile + Cost of Carry)
Objetivo: Consolida os arquivos de decisão, estimativas e cotações unificadas em um relatório executivo em Markdown.
"""

import json
from pathlib import Path
from datetime import datetime

# ==============================================================================
# RESOLUÇÃO DE CAMINHOS E LEITURA DE JSON
# ==============================================================================
RAIZ_PROJETO = Path(__file__).resolve().parent

def carregar_json(nome_arquivo):
    locais = [
        RAIZ_PROJETO / nome_arquivo,
        RAIZ_PROJETO / "Coletas" / nome_arquivo,
        RAIZ_PROJETO / "v2" / nome_arquivo,
        Path.cwd() / nome_arquivo,
        Path.cwd() / "Coletas" / nome_arquivo
    ]
    for p in locais:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}

unificados = carregar_json("DadosAtivosUnificados.json")
decisao_v2 = carregar_json("Decisao_V2.json")
resultado_operacional = carregar_json("Resultado_Calculadora_Operacional_Abertura.json")
estimativas = carregar_json("EstimativaAbertura.json") or carregar_json("Resultado_Calculadora.json")
smc_dados = carregar_json("AnaliseGraficaSMC_Regras.json")

ativos = unificados.get("ativos", {})
obj_decisao = decisao_v2.get("decisao", {})
meta_decisao = obj_decisao.get("metadados", {})

# ==============================================================================
# FUNÇÕES DE EXTRAÇÃO E FORMATAÇÃO DE DADOS
# ==============================================================================
def get_preco_str(chave, sufixo=""):
    if chave in ativos:
        val = ativos[chave].get("preco")
        if val is not None and isinstance(val, (int, float)):
            return f"{val:,.2f}{sufixo}"
    return "N/A"

def get_var_str(chave):
    if chave in ativos:
        val = ativos[chave].get("variacao_pct")
        if val is not None and isinstance(val, (int, float)):
            return f"{val:+.2f}%"
    return "N/A"

def get_num_fmt(dicionario, chave, padrao=0.0):
    val = dicionario.get(chave, padrao)
    if isinstance(val, (int, float)) and val > 0:
        return f"{val:,.0f}"
    return "—"

# Extração de Decisão e Targets
vies_final = obj_decisao.get("vies_final") or "NEUTRO"
confianca = obj_decisao.get("confianca", 0)
icone_confianca = "🔴" if confianca >= 80 else ("🟡" if confianca >= 50 else "⚪")

gatilho = obj_decisao.get("gatilho") or obj_decisao.get("entrada") or obj_decisao.get("entrada_sugerida") or meta_decisao.get("entrada", 0.0)
stop = obj_decisao.get("stop") or obj_decisao.get("stop_loss") or meta_decisao.get("stop", 0.0)

alvos = obj_decisao.get("alvos") or meta_decisao.get("alvos", [])
alvo_1 = alvos[0] if isinstance(alvos, list) and len(alvos) > 0 else (obj_decisao.get("alvo_1") or 0.0)

# Extração de Estimativas de Abertura & Cost of Carry
win_est = estimativas.get("estimativa_abertura", {}).get("WIN_INDICE") or estimativas.get("estimativa_abertura", {}).get("WIN_FUT") or {}
teorico = win_est.get("abertura_teorica_pontos") or resultado_operacional.get("previsao_abertura", {}).get("teorico_win") or meta_decisao.get("teorico_win", 0.0)
teorico_str = f"{teorico:,.0f} pts" if isinstance(teorico, (int, float)) and teorico > 0 else "—"

coc_dados = win_est.get("cost_of_carry", {})
preco_carregado = coc_dados.get("preco_teorico_carregado", 0.0)
carregado_str = f"{preco_carregado:,.0f} pts" if isinstance(preco_carregado, (int, float)) and preco_carregado > 0 else "—"

var_est = win_est.get("variacao_teorica_pct") or resultado_operacional.get("previsao_abertura", {}).get("variacao_estimada", 0.0)
var_est_str = f"{var_est:+.2f}%"

ajuste = meta_decisao.get("ajuste") or ativos.get("WIN_AJUSTE", {}).get("preco", 0.0)
ajuste_str = f"{ajuste:,.0f} pts" if isinstance(ajuste, (int, float)) and ajuste > 0 else "— pts"

# Pivôs Clássicos e Nivéis Institucionais (SMC)
pivots = estimativas.get("pivot_points", {}).get("WIN_FUT") or meta_decisao.get("pivots") or {}
niveis_inst = smc_dados.get("niveis_institucionais", {}) or estimativas.get("pivots_institucionais", {})
poc_ontem = niveis_inst.get("poc_ontem", 0.0)
vwap_ontem = niveis_inst.get("vwap_ontem", 0.0)

poc_str = f"{poc_ontem:,.0f} pts" if isinstance(poc_ontem, (int, float)) and poc_ontem > 0 else "—"
vwap_str = f"{vwap_ontem:,.1f} pts" if isinstance(vwap_ontem, (int, float)) and vwap_ontem > 0 else "—"

# Termômetro Macro
vix_val = get_preco_str("VIX")
iron_val = get_preco_str("IRON_ORE")
oil_val = get_preco_str("CRUDE_OIL")
di27_val = get_var_str("DI1_2027")
di29_val = get_var_str("DI1_2029")

# ==============================================================================
# MONTAGEM E GRAVAÇÃO DO RELATÓRIO
# ==============================================================================
def executar():
    print("=" * 60)
    print("🚀 INICIANDO GERADOR DE RELATÓRIO OPERACIONAL EXECUTIVO (V2)")
    print("=" * 60)
    
    agora_str = datetime.now().strftime("%d/%m/%Y às %H:%M")
    
    gatilho_str = f"{gatilho:,.0f} pts" if isinstance(gatilho, (int, float)) and gatilho > 0 else "—"
    stop_str = f"{stop:,.0f} pts" if isinstance(stop, (int, float)) and stop > 0 else "—"
    alvo_1_str = f"{alvo_1:,.0f} pts" if isinstance(alvo_1, (int, float)) and alvo_1 > 0 else "—"

    relatorio_md = f"""📊 *QUANT TERMINAL B3 — MORNING REPORT V2* 📊
⏱ _Pregão Analisado: {agora_str}_
--------------------------------------------------
🎯 *ESTRUTURA DIRECIONAL CORE V2*
• **Viés Institucional:** `{vies_final}`
• **Força de Confluência:** `{icone_confianca} {confianca}%`
• **Ordem Gatilho (Entry):** `{gatilho_str}`
• **Stop Loss Técnico:** `{stop_str}`
• **Alvo Principal (T1):** `{alvo_1_str}`

--------------------------------------------------
📈 *PREVISÃO DE ESTIMATIVA E GAP (WIN)*
• **Preço Teórico de Abertura:** `{teorico_str}`
• **Abertura Carregada (DI/252):** `{carregado_str}`
• **Variação Estimada:** `{var_est_str}`
• **Ajuste Base Anterior:** `{ajuste_str}`

🏦 *Pivôs Institucionais (Volume Profile / Tesouraria):*
• **POC (Ontem - Maior Volume):** `{poc_str}`
• **VWAP (Ontem - Preço Ponderado):** `{vwap_str}`

📍 *Níveis Críticos de Pivô (Floor):*
• Resistência 2 (R2): `{get_num_fmt(pivots, 'R2', pivots.get('r2', 0))}` | Resistência 1 (R1): `{get_num_fmt(pivots, 'R1', pivots.get('r1', 0))}`
• **Ponto de Pivô (PP):** `{get_num_fmt(pivots, 'PP', pivots.get('pp', 0))}`
• Suporte 1 (S1): `{get_num_fmt(pivots, 'S1', pivots.get('s1', 0))}` | Suporte 2 (S2): `{get_num_fmt(pivots, 'S2', pivots.get('s2', 0))}`

--------------------------------------------------
🌐 *TERMÔMETRO CONTEXTUAL MACRO*
• VIX Volatilidade : `{vix_val}`
• Minério de Ferro  : `US$ {iron_val}`
• Petróleo WTI      : `US$ {oil_val}`
• Curva de Juros    : DI27: `{di27_val}` | DI29: `{di29_val}`
--------------------------------------------------
⚠️ _Relatório quantitativo confidencial para apoio operational à mesa._
"""

    caminho_saida = RAIZ_PROJETO / "Coletas" / "Relatorio_Executivo.md"
    if not caminho_saida.parent.exists():
        caminho_saida = RAIZ_PROJETO / "Relatorio_Executivo.md"
        
    try:
        with open(caminho_saida, "w", encoding="utf-8") as f:
            f.write(relatorio_md)
        print("✨ Mensagem compilada e formatada com sucesso!")
        print(f"✅ Arquivo salvo para integração em: {caminho_saida.name}\n")
        print(relatorio_md)
    except Exception as e:
        print(f"❌ Erro ao salvar o relatório: {e}")

if __name__ == "__main__":
    executar()