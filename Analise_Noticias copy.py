# ============================================================
# ARQUIVO: Analise_Noticias.py
# OBJETIVO:
#   Analisar impacto das notícias econômicas coletadas
#
# REGRAS:
#   ⭐   = 1 ponto
#   ⭐⭐  = 3 pontos
#   ⭐⭐⭐ = 6 pontos
#
# ALERTAS:
#   1. Notícia ⭐⭐⭐ no Brasil às 09:00
#   2. Notícias ⭐⭐⭐ em outros horários (Brasil / USD)
#   3. 2 ou mais ⭐⭐ no mesmo horário
#
# DATA ALTERAÇÃO: 2026-07-31
# ============================================================


import json
import os
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")

ARQUIVO_ENTRADA = os.path.join(COLETAS_DIR, "Noticias_Calendario.json")

ARQUIVO_SAIDA = os.path.join(COLETAS_DIR, "Noticias_Impacto_Dia.json")


# ============================================================
# PESO DAS ESTRELAS
# ============================================================

PESO_ESTRELAS = {1: 1, 2: 3, 3: 6}


# ============================================================
# CLASSIFICAÇÃO
# ============================================================


def classificar_risco(pontos):

    if pontos >= 15:
        return "EXTREMO"

    elif pontos >= 9:
        return "ALTO"

    elif pontos >= 4:
        return "ATENÇÃO"

    else:
        return "BAIXO"


# ============================================================
# ANALISE PRINCIPAL
# ============================================================


def analisar_noticias():

    with open(ARQUIVO_ENTRADA, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    eventos = dados.get("eventos", [])

    agrupados = {}
    impacto_total = 0

    # Estruturas para novos alertas
    alerta_3_estrelas_brasil_0900 = False
    noticias_3_estrelas_outros_horarios = []
    horarios_com_multiplas_2_estrelas = []

    for evento in eventos:

        hora = evento.get("hora", "")
        importancia = int(evento.get("importancia", 0))
        pais = evento.get("pais", "")
        moeda = evento.get("moeda", "")
        nome_evento = evento.get("evento", "")

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

        # 1. CHECAGEM: ⭐⭐⭐ no Brasil às 09:00
        if hora == "09:00" and importancia == 3 and pais == "Brasil":
            alerta_3_estrelas_brasil_0900 = True

        # 2. CHECAGEM: ⭐⭐⭐ em outros horários no Brasil e USD (USD / BRL)
        if importancia == 3 and hora != "09:00":
            noticias_3_estrelas_outros_horarios.append({
                "hora": hora,
                "pais": pais,
                "moeda": moeda,
                "evento": nome_evento,
            })

    analise_horarios = []

    for hora, dados_hora in agrupados.items():

        qtd_duas = 0

        for ev in dados_hora["eventos"]:
            if ev["estrelas"] == 2:
                qtd_duas += 1

        # 3. CHECAGEM: 2 ou mais notícias de 2 estrelas no mesmo horário
        tem_duas_ou_mais_2_estrelas = qtd_duas >= 2
        if tem_duas_ou_mais_2_estrelas:
            horarios_com_multiplas_2_estrelas.append({
                "hora": hora,
                "quantidade_2_estrelas": qtd_duas,
            })

        analise_horarios.append({
            "hora": hora,
            "pontuacao": dados_hora["pontuacao"],
            "classificacao": classificar_risco(dados_hora["pontuacao"]),
            "quantidade_eventos": len(dados_hora["eventos"]),
            "duas_estrelas_equivalente_alta": tem_duas_ou_mais_2_estrelas,
            "eventos": dados_hora["eventos"],
        })

    resultado = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "fonte": "Analise Noticias Investing",
        },
        "resumo": {
            "impacto_total": impacto_total,
            "classificacao": classificar_risco(impacto_total),
        },
        "alertas": {
            "tem_3_estrelas_brasil_0900": alerta_3_estrelas_brasil_0900,
            "tem_3_estrelas_outros_horarios": len(
                noticias_3_estrelas_outros_horarios
            )
            > 0,
            "noticias_3_estrelas_outros_horarios": noticias_3_estrelas_outros_horarios,
            "tem_multiplas_2_estrelas_mesmo_horario": len(
                horarios_com_multiplas_2_estrelas
            )
            > 0,
            "horarios_multiplas_2_estrelas": horarios_com_multiplas_2_estrelas,
            "risco_abertura_WIN": impacto_total >= 10,
        },
        "horarios": analise_horarios,
    }

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as arquivo:
        json.dump(resultado, arquivo, indent=4, ensure_ascii=False)

    return resultado


# ============================================================
# EXECUÇÃO
# ============================================================


if __name__ == "__main__":

    resultado = analisar_noticias()

    print()
    print("=" * 60)
    print(" ANALISE DE IMPACTO DAS NOTICIAS ")
    print("=" * 60)

    print("Impacto total:", resultado["resumo"]["impacto_total"])

    print("Classificação:", resultado["resumo"]["classificacao"])

    print()

    # Exibição dos Alertas Especificados
    if resultado["alertas"]["tem_3_estrelas_brasil_0900"]:
        print("🚨 ALERTA 1: Notícia ⭐⭐⭐ no Brasil às 09:00!")

    if resultado["alertas"]["tem_3_estrelas_outros_horarios"]:
        print("\n🚨 ALERTA 2: Notícias ⭐⭐⭐ em outros horários (BR / USD):")
        for item in resultado["alertas"][
            "noticias_3_estrelas_outros_horarios"
        ]:
            print(
                f"   • {item['hora']} | [{item['moeda']}] {item['pais']} - {item['evento']}"
            )

    if resultado["alertas"]["tem_multiplas_2_estrelas_mesmo_horario"]:
        print(
            "\n⚠️ ALERTA 3: 2 ou mais notícias de ⭐⭐ encontradas no mesmo horário:"
        )
        for item in resultado["alertas"]["horarios_multiplas_2_estrelas"]:
            print(
                f"   • Horário: {item['hora']} | Qtd Noticias ⭐⭐: {item['quantidade_2_estrelas']}"
            )

    if resultado["alertas"]["risco_abertura_WIN"]:
        print("\n⚠️ ALERTA: Risco elevado na abertura do WIN (Mini Índice)")

    print()
    print("Arquivo gerado:")
    print(ARQUIVO_SAIDA)
    print("=" * 60)