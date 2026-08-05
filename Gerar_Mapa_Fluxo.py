# ============================================================
# ARQUIVO: Mapa_Fluxo.py
#
# MAPA DE FLUXO DO ANALISADOR FINANCEIRO
#
# Objetivo:
# Documentar entrada -> processamento -> saída
#
# Projeto:
# Analisador_Financeiro
#
# Data:
# 2026-07-31
#
# ============================================================


import json
import os
from datetime import datetime


ARQUIVO_SAIDA = (
    "Coletas/Mapa_Fluxo.json"
)


# ============================================================
# DEFINIÇÃO DO FLUXO DO SISTEMA
# ============================================================


FLUXO_APLICACAO = {


    "metadata": {

        "projeto":
            "Analisador_Financeiro",

        "gerado_em":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "tipo":
            "Mapa de fluxo de dados"

    },


    "pipeline": [


        {


            "etapa":
                1,

            "nome":
                "COLETA",

            "descricao":
                "Aquisição dos dados externos",

            "arquivos": [

                "Coletor.py",

                "Coleta_Noticias_Calendario.py"

            ],

            "entrada": [

                "TradingView",

                "Investing.com",

                "B3",

                "APIs"

            ],

            "saida": [

                "Coleta_ram.json",

                "Coleta_rom-0.json",

                "Noticias_Calendario.json"

            ]

        },


        {


            "etapa":
                2,

            "nome":
                "VALIDAÇÃO",

            "descricao":
                "Confere qualidade dos dados",

            "arquivos": [

                "Validador.py",

                "Testador_Fontes.py"

            ],

            "entrada": [

                "Dados coletados"

            ],

            "saida": [

                "Dados_Validados.json"

            ]

        },


        {


            "etapa":
                3,

            "nome":
                "ANÁLISE",

            "descricao":
                "Transforma dados em informações",

            "arquivos": [

                "Analise_Noticias.py",

                "Calculadora.py"

            ],

            "entrada": [

                "Dados_Validados.json",

                "Noticias_Calendario.json"

            ],

            "saida": [

                "Noticias_Impacto_Dia.json",

                "Metricas_Calculadas.json"

            ]

        },


        {


            "etapa":
                4,

            "nome":
                "CORE",

            "descricao":
                "Motor de decisão",

            "arquivos": [

                "Engine_Vies.py",

                "Gerar_Resultado_Operacional.py"

            ],

            "entrada": [

                "Metricas_Calculadas.json",

                "Noticias_Impacto_Dia.json"

            ],

            "saida": [

                "Decisao_Core.json",

                "Resultado_Calculadora_Operacional.json"

            ]

        },


        {


            "etapa":
                5,

            "nome":
                "RELATÓRIO",

            "descricao":
                "Apresentação da decisão",

            "arquivos": [

                "Relatorio.py",

                "Gerar_Relatorio_Mensagem.py"

            ],

            "entrada": [

                "Decisao_Core.json"

            ],

            "saida": [

                "Relatorio_Executivo.md"

            ]

        },


        {


            "etapa":
                6,

            "nome":
                "INTERFACE",

            "descricao":
                "Visualização pelo usuário",

            "arquivos": [

                "app_home.py",

                "pages/"

            ],

            "entrada": [

                "Arquivos JSON",

                "Relatórios"

            ],

            "saida": [

                "Dashboard"

            ]

        }


    ]

}



# ============================================================
# SALVAR
# ============================================================


def gerar():

    os.makedirs(
        "Coletas",
        exist_ok=True
    )


    with open(
        ARQUIVO_SAIDA,
        "w",
        encoding="utf-8"
    ) as arquivo:


        json.dump(

            FLUXO_APLICACAO,

            arquivo,

            indent=4,

            ensure_ascii=False

        )



    print("=" * 60)
    print(" MAPA DE FLUXO GERADO ")
    print("=" * 60)

    print()

    print(
        "Etapas:",
        len(
            FLUXO_APLICACAO["pipeline"]
        )
    )

    print()

    print(
        "Arquivo:"
    )

    print(
        os.path.abspath(
            ARQUIVO_SAIDA
        )
    )

    print("=" * 60)



if __name__ == "__main__":

    gerar()