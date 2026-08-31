# -*- coding: utf-8 -*-
"""
Módulo: Analise_Noticias.py
Versão: 2.5 - Produção Pipeline V2
Objetivo: Processar o impacto das notícias macro em lote e gerar travas de volatilidade.
"""

import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Ingestão de caminhos, pesos e constantes unificadas do seu config.py
from config import (
    FILE_NOTICIAS_CALENDARIO,
    FILE_NOTICIAS_IMPACTO,
    PESO_ESTRELAS,
    COLETAS_DIR
)

def classificar_risco(pontos: int) -> str:
    """Classifica a intensidade do risco com base no somatório de pesos das notícias."""
    if pontos >= 15:
        return "EXTREMO"
    elif pontos >= 9:
        return "ALTO"
    elif pontos >= 4:
        return "ATENÇÃO"
    return "BAIXO"

def analisar_noticias_lote() -> dict:
    print("=" * 60)
    print(" 📰 INICIANDO COMPILADOR QUANTITATIVO DE IMPACTO MACRO (V2)")
    print("=" * 60)
    print(f"🕒 Horário do Processamento: {datetime.now().strftime('%H:%M:%S')}")
    
    timestamp_iso = datetime.now().isoformat()
    
    # Estrutura defensiva padrão (Fallback Neutro) caso o JSON de entrada falhe
    resultado_padrao = {
        "metadata": {
            "timestamp": timestamp_iso,
            "fonte": "Analise Noticias TV API V2 (Fallback)",
        },
        "resumo": {
            "impacto_total": 0,
            "classificacao": "BAIXO",
        },
        "alertas": {
            "tem_3_estrelas_brasil_0900": False,
            "tem_3_estrelas_outros_horarios": False,
            "noticias_3_estrelas_outros_horarios": [],
            "tem_multiplas_2_estrelas_mesmo_horario": False,
            "horarios_multiplas_2_estrelas": [],
            "risco_abertura_WIN": False,
        },
        "horarios": [],
    }

    # 1. VALIDAÇÃO DEFENSIVA DE ENTRADA DO ARQUIVO BRUTO
    if not FILE_NOTICIAS_CALENDARIO.exists():
        print(f"⚠️ [AVISO] Calendário econômico bruto ausente: {FILE_NOTICIAS_CALENDARIO.name}")
        print("   -> Gerando payload padrão com risco BAIXO para liberar o pipeline.")
        with open(FILE_NOTICIAS_IMPACTO, "w", encoding="utf-8") as arquivo:
            json.dump(resultado_padrao, arquivo, indent=4, ensure_ascii=False)
        return resultado_padrao

    try:
        # 2. LEITURA DOS DADOS COLETADOS PELO PIPELINE
        with open(FILE_NOTICIAS_CALENDARIO, "r", encoding="utf-8") as arquivo:
            dados_brutos = json.load(arquivo)

        # Ajuste adaptativo para aceitar os dois schemas possíveis do seu coletor
        eventos = dados_brutos.get("calendario_eventos", {}).get("eventos", []) or dados_brutos.get("eventos", [])

        agrupados = {}
        impacto_total = 0

        # Estruturas de controle para os alertas institucionais de risco
        alerta_3_estrelas_brasil_0900 = False
        noticias_3_estrelas_outros_horarios = []
        horarios_com_multiplas_2_estrelas = []

        # 3. PROCESSAMENTO MATEMÁTICO DOS PESOS EM LOTE
        for evento in eventos:
            hora = evento.get("hora", "")
            importancia = int(evento.get("importancia", 0))
            pais = evento.get("pais", "")
            moeda = evento.get("moeda", "")
            nome_evento = evento.get("evento", "")

            # Captura o peso configurado centralizadamente no config.py (A2)
            peso = PESO_ESTRELAS.get(importancia, 0)
            impacto_total += peso

            if hora not in agrupados:
                agrupados[hora] = {"pontuacao": 0, "eventos": []}

            agrupados[hora]["pontuacao"] += peso
            agrupados[hora]["eventos"].append({
                "nome": nome_evento,
                "pais": pais,
                "moeda": moeda,
                "estrelas": importancia,
                "peso": peso,
            })

            # CHECAGEM 1: Notícia Máxima de 3 Estrelas no Brasil exatamente às 09:00h
            if hora == "09:00" and importancia == 3 and (pais == "Brazil" or moeda == "BRL"):
                alerta_3_estrelas_brasil_0900 = True

            # CHECAGEM 2: Notícias de 3 Estrelas em outros horários operacionais relevantes
            if importancia == 3 and hora != "09:00":
                noticias_3_estrelas_outros_horarios.append({
                    "hora": hora,
                    "pais": pais,
                    "moeda": moeda,
                    "evento": nome_evento,
                })

        # 4. COMPILAÇÃO CHRONOLÓGICA E CHECAGEM DE ACÚMULO DE SPREAD
        analise_horarios = []
        for hora, dados_hora in agrupados.items():
            qtd_duas_estrelas = sum(1 for ev in dados_hora["eventos"] if ev["estrelas"] == 2)

            # CHECAGEM 3: Concentração de 2 ou mais notícias de 2 estrelas no mesmo slot
            tem_multiplas_2 = qtd_duas_estrelas >= 2
            if tem_multiplas_2:
                horarios_com_multiplas_2_estrelas.append({
                    "hora": hora,
                    "quantidade_2_estrelas": qtd_duas_estrelas,
                })

            analise_horarios.append({
                "hora": hora,
                "pontuacao": dados_hora["pontuacao"],
                "classificacao": classificar_risco(dados_hora["pontuacao"]),
                "quantidade_eventos": len(dados_hora["eventos"]),
                "duas_estrelas_equivalente_alta": tem_multiplas_2,
                "eventos": dados_hora["eventos"],
            })

        # 5. MONTAGEM DO PAYLOAD CONSOLIDADO V2
        resultado = {
            "metadata": {
                "timestamp": timestamp_iso,
                "fonte": "Analise Noticias TV API V2",
            },
            "resumo": {
                "impacto_total": impacto_total,
                "classificacao": classificar_risco(impacto_total),
            },
            "alertas": {
                "tem_3_estrelas_brasil_0900": alerta_3_estrelas_brasil_0900,
                "tem_3_estrelas_outros_horarios": len(noticias_3_estrelas_outros_horarios) > 0,
                "noticias_3_estrelas_outros_horarios": noticias_3_estrelas_outros_horarios,
                "tem_multiplas_2_estrelas_mesmo_horario": len(horarios_com_multiplas_2_estrelas) > 0,
                "horarios_multiplas_2_estrelas": horarios_com_multiplas_2_estrelas,
                "risco_abertura_WIN": impacto_total >= 10,
            },
            "horarios": sorted(analise_horarios, key=lambda x: x["hora"]),
        }

        # 6. SALVAMENTO DA TOMADA DE DECISÃO MACRO NO DISCO
        COLETAS_DIR.mkdir(parents=True, exist_ok=True)
        with open(FILE_NOTICIAS_IMPACTO, "w", encoding="utf-8") as arquivo:
            json.dump(resultado, arquivo, indent=4, ensure_ascii=False)

        # Painel Informativo de Console (Lote logs)
        print(f"  └─ Impacto Global Processado : {impacto_total} pontos")
        print(f"  └─ Classificação Operacional : {resultado['resumo']['classificacao']}")
        print(f"  └─ Risco de Abertura WIN     : {'⚠️ ELEVADO' if resultado['alertas']['risco_abertura_WIN'] else '🟢 SEGURO'}")
        if alerta_3_estrelas_brasil_0900:
            print("  🚨 [TRAVA ATIVADA]: Evento 3 Estrelas BRL agendado para às 09:00h!")
        print(f"✅ Arquivo de impacto gravado com sucesso em: {FILE_NOTICIAS_IMPACTO.name}\n")
        
        return resultado

    except Exception as e:
        print(f"❌ [ERRO CRÍTICO NO MÓDULO NOTÍCIAS]: {e}")
        traceback.print_exc()
        
        # Isola a falha e grava o payload defensivo para não derrubar o main_pipeline.py
        with open(FILE_NOTICIAS_IMPACTO, "w", encoding="utf-8") as arquivo:
            json.dump(resultado_padrao, arquivo, indent=4, ensure_ascii=False)
        return resultado_padrao

if __name__ == "__main__":
    analisar_noticias_lote()
