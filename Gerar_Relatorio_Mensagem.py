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

# ATENCAO: os JSONs eram carregados no nivel de modulo (bug).
# Como o main_pipeline importa este modulo no topo, os carregamentos
# rodavam ANTES de qualquer fase executar — o relatorio mostrava sempre
# o estado do ciclo ANTERIOR.
# Agora sao carregados em _carregar_estado(), chamada dentro de executar().

def _carregar_estado():
    """Carrega todos os JSONs frescos e retorna dict com as variaveis."""
    unificados = carregar_json("DadosAtivosUnificados.json")
    decisao_v2 = carregar_json("Decisao_V2.json")
    resultado_operacional = carregar_json("Resultado_Calculadora_Operacional_Abertura.json")
    estimativas = carregar_json("EstimativaAbertura.json") or carregar_json("Resultado_Calculadora.json")
    smc_dados = carregar_json("AnaliseGraficaSMC_Regras.json")

    ativos = unificados.get("ativos", {})
    obj_decisao = decisao_v2.get("decisao", {})
    meta_decisao = obj_decisao.get("metadados", {})

    return {
        "ativos": ativos,
        "obj_decisao": obj_decisao,
        "meta_decisao": meta_decisao,
        "estimativas": estimativas,
        "resultado_operacional": resultado_operacional,
        "smc_dados": smc_dados,
    }

# Placeholders para compatibilidade com funcoes que usam essas vars no
# nivel de modulo (get_preco_str, get_var_str, etc). Serao preenchidos
# por executar() antes de formatar o relatorio.
ativos = {}
obj_decisao = {}
meta_decisao = {}
estimativas = {}
resultado_operacional = {}
smc_dados = {}

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
# FIX30b: este bloco agora roda DENTRO de executar() (antes ficava no
# nivel de modulo, congelando os valores do import).
def _calcular_derivados():
    """Calcula todos os campos derivados a partir das vars globais."""
    vies_final = obj_decisao.get("vies_final") or "NEUTRO"
    confianca = obj_decisao.get("confianca", 0)
    icone_confianca = "🔴" if confianca >= 80 else ("🟡" if confianca >= 50 else "⚪")

    gatilho = obj_decisao.get("gatilho") or obj_decisao.get("entrada") or obj_decisao.get("entrada_sugerida") or meta_decisao.get("entrada", 0.0)
    stop = obj_decisao.get("stop") or obj_decisao.get("stop_loss") or meta_decisao.get("stop", 0.0)

    alvos = obj_decisao.get("alvos") or meta_decisao.get("alvos", [])
    alvo_1 = alvos[0] if isinstance(alvos, list) and len(alvos) > 0 else (obj_decisao.get("alvo_1") or 0.0)

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

    pivots = estimativas.get("pivot_points", {}).get("WIN_FUT") or meta_decisao.get("pivots") or {}
    niveis_inst = smc_dados.get("niveis_institucionais", {}) or estimativas.get("pivots_institucionais", {})
    poc_ontem = niveis_inst.get("poc_ontem", 0.0)
    vwap_ontem = niveis_inst.get("vwap_ontem", 0.0)

    poc_str = f"{poc_ontem:,.0f} pts" if isinstance(poc_ontem, (int, float)) and poc_ontem > 0 else "—"
    vwap_str = f"{vwap_ontem:,.1f} pts" if isinstance(vwap_ontem, (int, float)) and vwap_ontem > 0 else "—"

    vix_val = get_preco_str("VIX")
    iron_val = get_preco_str("IRON_ORE")
    oil_val = get_preco_str("CRUDE_OIL")
    di27_val = get_var_str("DI1_2027")
    di29_val = get_var_str("DI1_2029")

    return {
        "vies_final": vies_final,
        "confianca": confianca,
        "icone_confianca": icone_confianca,
        "gatilho": gatilho,
        "stop": stop,
        "alvos": alvos,
        "alvo_1": alvo_1,
        "teorico_str": teorico_str,
        "carregado_str": carregado_str,
        "var_est_str": var_est_str,
        "ajuste_str": ajuste_str,
        "pivots": pivots,
        "poc_str": poc_str,
        "vwap_str": vwap_str,
        "vix_val": vix_val,
        "iron_val": iron_val,
        "oil_val": oil_val,
        "di27_val": di27_val,
        "di29_val": di29_val,
    }

# ==============================================================================
# MONTAGEM E GRAVAÇÃO DO RELATÓRIO
# ==============================================================================
def executar():
    print("=" * 60)
    print("🚀 INICIANDO GERADOR DE RELATÓRIO OPERACIONAL EXECUTIVO (V2)")
    print("=" * 60)

    # --- FIX30 + FIX30b: recarrega estado E recalcula derivados ---
    global ativos, obj_decisao, meta_decisao
    global estimativas, resultado_operacional, smc_dados

    estado = _carregar_estado()
    ativos = estado["ativos"]
    obj_decisao = estado["obj_decisao"]
    meta_decisao = estado["meta_decisao"]
    estimativas = estado["estimativas"]
    resultado_operacional = estado["resultado_operacional"]
    smc_dados = estado["smc_dados"]

    # Recalcula TODOS os derivados (gatilho, stop, alvos, teorico, etc)
    _d = _calcular_derivados()
    vies_final = _d["vies_final"]
    confianca = _d["confianca"]
    icone_confianca = _d["icone_confianca"]
    gatilho = _d["gatilho"]
    stop = _d["stop"]
    alvos = _d["alvos"]
    alvo_1 = _d["alvo_1"]
    teorico_str = _d["teorico_str"]
    carregado_str = _d["carregado_str"]
    var_est_str = _d["var_est_str"]
    ajuste_str = _d["ajuste_str"]
    pivots = _d["pivots"]
    poc_str = _d["poc_str"]
    vwap_str = _d["vwap_str"]
    vix_val = _d["vix_val"]
    iron_val = _d["iron_val"]
    oil_val = _d["oil_val"]
    di27_val = _d["di27_val"]
    di29_val = _d["di29_val"]

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