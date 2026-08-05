# ============================================================
# GERADOR APP COMPLETO - ANALISADOR FINANCEIRO
#
# Função:
# Unificar todos os arquivos .py do projeto
# em um único arquivo para análise.
#
# Saída:
# Coletas\App_Completo.py
#
# NÃO EDITAR O ARQUIVO GERADO
# ============================================================


import os
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PASTA_SAIDA = os.path.join(
    BASE_DIR,
    "Coletas"
)


ARQUIVO_SAIDA = os.path.join(
    PASTA_SAIDA,
    "App_Completo.txt"
)


IGNORAR_PASTAS = {
    "Coletas",
    "__pycache__",
    ".git",
    "venv",
    ".venv"
}


IGNORAR_ARQUIVOS = {
    "Gerar_App_Completo.py",
    "App_Completo.py"
}



def encontrar_python():

    arquivos = []

    for raiz, pastas, arquivos_nome in os.walk(BASE_DIR):

        # remove pastas ignoradas
        pastas[:] = [
            p for p in pastas
            if p not in IGNORAR_PASTAS
        ]


        for arquivo in arquivos_nome:

            if not arquivo.endswith(".py"):
                continue


            if arquivo in IGNORAR_ARQUIVOS:
                continue


            caminho = os.path.join(
                raiz,
                arquivo
            )

            arquivos.append(caminho)


    return sorted(arquivos)



def gerar():

    if not os.path.exists(PASTA_SAIDA):

        os.makedirs(PASTA_SAIDA)



    arquivos = encontrar_python()


    print("="*60)
    print(" GERADOR APP COMPLETO ")
    print("="*60)

    print()

    print(
        "Arquivos encontrados:",
        len(arquivos)
    )


    with open(
        ARQUIVO_SAIDA,
        "w",
        encoding="utf-8"
    ) as saida:


        saida.write(
f"""
# ============================================================
# APP COMPLETO - ANALISADOR FINANCEIRO
#
# GERADO AUTOMATICAMENTE
#
# Data geração:
# {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
#
# Arquivos unificados:
# {len(arquivos)}
#
# NÃO EDITAR MANUALMENTE
# ============================================================


"""
        )


        for caminho in arquivos:


            relativo = os.path.relpath(
                caminho,
                BASE_DIR
            )


            data = datetime.fromtimestamp(
                os.path.getmtime(caminho)
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )


            saida.write(
f"""



# ============================================================
# ARQUIVO:
# {relativo}
#
# ÚLTIMA ALTERAÇÃO:
# {data}
# ============================================================



"""
            )


            try:

                with open(
                    caminho,
                    "r",
                    encoding="utf-8"
                ) as origem:


                    conteudo = origem.read()


                    saida.write(conteudo)



            except Exception as erro:


                saida.write(
f"""

# ERRO AO LER ARQUIVO:
# {erro}

"""
                )


    print()

    print(
        "Arquivo gerado:"
    )

    print(
        ARQUIVO_SAIDA
    )

    print("="*60)



if __name__ == "__main__":

    gerar()