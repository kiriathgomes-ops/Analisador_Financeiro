# -*- coding: utf-8 -*-
"""
Módulo: Gerar_Relatorio_Mensagem.py
Versão: 3.0 - Produção Unificada V2
Objetivo: Compilar estimativas, pivots e decisões da V2 em um relatório executivo em Markdown.
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Ingestão de caminhos centralizados do config.py da V2
from config import FILE_ESTIMATIVA_ABERTURA, FILE_DECISAO_V2, FILE_PIPELINE_LOG, COLETAS_DIR

def carregar_json_defensivo(caminho_path) -> dict:
    if not caminho_path.exists():
        return {}
    try:
        with open(caminho_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def fmt_num(valor, casas=0, default="—") -> str:
    """Formata números com separadores de milhar com segurança contra nulos."""
    if valor is None:
        return default
    try:
        v = float(valor)
        if casas == 0:
            return f"{v:,.0f}"
        return f"{v:,.{casas}f}"
    except:
        return default

def compilar_relatorio_executivo():
    print("=" * 60)
    print(" 🚀 INICIANDO GERADOR DE RELATÓRIO OPERACIONAL EXECUTIVO (V2)")
    print("=" * 60)

    # 1. Carrega os dados higienizados do ecossistema V2
    est_data = carregar_json_defensivo(FILE_ESTIMATIVA_ABERTURA)
    dec_data = carregar_json_defensivo(FILE_DECISAO_V2)
    log_data = carregar_json_defensivo(FILE_PIPELINE_LOG)

    if not est_data or not dec_data:
        print("❌ [ERRO] Arquivos de dados essenciais (Estimativas/Decisão) ausentes no disco.")
        return

    # 2. Captura metadados e fuso horário do pregão
    ts = est_data.get("metadata_calculo", {}).get("timestamp_calculo")
    hora_str = datetime.fromisoformat(ts).strftime("%d/%m/%Y às %H:%M") if ts else datetime.now().strftime("%d/%m/%Y às %H:%M")

    win_est = est_data.get("estimativa_abertura", {}).get("WIN_INDICE", {})
    pivots_win = est_data.get("pivot_points", {}).get("WIN_FUT", {})
    macro = est_data.get("resumo_macro", {})
    
    decisao_v2 = dec_data.get("decisao", {})
    vies_final = decisao_v2.get("vies_final", "NEUTRO")
    confianca = decisao_v2.get("confianca", 0)

    # Ícone direcional dinâmico para o cabeçalho do relatório
    icon_vies = "🟢" if "COMPRA" in vies_final.upper() or vies_final.upper() == "ALTA" else ("🔴" if "VENDA" in vies_final.upper() or vies_final.upper() == "BAIXA" else "⚖️")

    # 3. CONSTRUÇÃO DO CORPO DA MENSAGEM (MARKDOWN OPERACIONAL)
    linhas = [
        "📊 *QUANT TERMINAL B3 — MORNING REPORT V2* 📊",
        f"⏱ _Pregão Analisado: {hora_str}_",
        "--------------------------------------------------",
        "🎯 *ESTRUTURA DIRECIONAL CORE V2*",
        f"• **Viés Institucional:** `{vies_final}`",
        f"• **Força de Confluência:** `{icon_vies} {confianca}%`",
    ]

    # Injeta os gatilhos operacionais do robô se o mercado não estiver neutro
    if decisao_v2.get("entrada"):
        linhas.extend([
            f"• **Ordem Gatilho (Entry):** `{fmt_num(decisao_v2.get('entrada'))} pts`",
            f"• **Stop Loss Técnico:** `{fmt_num(decisao_v2.get('stop_loss'))} pts`",
            f"• **Alvo Fibonacci (T1):** `{fmt_num(decisao_v2.get('alvo_1'))} pts`",
        ])
    else:
        linhas.append("• **Ação Recomendada:** `Aguardando Quebra de Estrutura (BOS)`")

    linhas.extend([
        "",
        "--------------------------------------------------",
        "📈 *PREVISÃO DE ESTIMATIVA E GAP (WIN)*",
        f"• **Preço Teórico de Abertura:** `{fmt_num(win_est.get('abertura_teorica_pontos'))} pts`",
        f"• **Variação Estimada:** `{win_est.get('variacao_teorica_pct', 0.0):+.2f}%`",
        f"• **Ajuste Base Anterior:** `{fmt_num(win_est.get('pontos_ajuste_base'))} pts`",
        "",
        "📍 *Níveis Críticos de Pivô (Floor):*",
        f"• Resistência 2 (R2): `{fmt_num(pivots_win.get('R2'))}` | Resistência 1 (R1): `{fmt_num(pivots_win.get('R1'))}`",
        f"• **Ponto de Pivô (PP):** `{fmt_num(pivots_win.get('PP'))}`",
        f"• Suporte 1 (S1): `{fmt_num(pivots_win.get('S1'))}` | Suporte 2 (S2): `{fmt_num(pivots_win.get('S2'))}`",
        "",
        "--------------------------------------------------",
        "🌐 *TERMÔMETRO CONTEXTUAL MACRO*",
        f"• VIX Volatilidade : `{macro.get('vix', 'N/A')}`",
        f"• Minério de Ferro  : `US$ {macro.get('iron_ore', 'N/A')}`",
        f"• Petróleo WTI      : `US$ {macro.get('crude_oil', 'N/A')}`",
        f"• Curva de Juros    : DI27: `{macro.get('di1_2027', 'N/A')}%` | DI29: `{macro.get('di1_2029', 'N/A')}%`",
        "--------------------------------------------------",
        "⚠️ _Relatório quantitativo confidencial para apoio operacional à mesa._"
    ])

    mensagem_final = "\n".join(linhas)

    # 4. SALVAMENTO DO ARQUIVO OPERACIONAL EM DISCO
    # Caminho central de saída para relatórios textuais do projeto
    file_relatorio_txt = COLETAS_DIR / "Relatorio_Executivo.md"
    
    try:
        with open(file_relatorio_txt, "w", encoding="utf-8") as f:
            f.write(mensagem_final)
        print("✨ Mensagem compilada e formatada com sucesso!")
        print(f"✅ Arquivo salvo para integração em: {file_relatorio_txt.name}\n")
        
        # Opcional: Imprime no console para auditoria rápida do desenvolvedor
        print(mensagem_final)
        print("\n" + "=" * 60)
    except Exception as e:
        print(f"❌ Erro ao salvar arquivo Markdown: {e}")

if __name__ == "__main__":
    compilar_relatorio_executivo()
