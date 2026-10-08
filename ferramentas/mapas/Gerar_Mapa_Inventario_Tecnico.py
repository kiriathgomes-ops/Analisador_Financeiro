# ============================================================
# GERADOR DE ARQUIVOS DO PROJETO - V2.1
#
# Projeto:
# Analisador_Financeiro
#
# Objetivo:
# Criar mapa estrutural do projeto para análise humana/IA
#
# Data alteração:
# 2026-07-31
#
# NÃO EDITAR O ARQUIVO GERADO MANUALMENTE
# ============================================================


import os
import datetime


# ============================================================
# CONFIGURAÇÃO
# ============================================================

PASTA_PROJETO = r"E:\ProjetosPython\Analisador_Financeiro"

PASTA_SAIDA = os.path.join(
    PASTA_PROJETO,
    "Coletas"
)

ARQUIVO_SAIDA = os.path.join(
    PASTA_SAIDA,
    "ArquivosApp.py"
)


# Pastas antigas/backups

PASTAS_IGNORAR = {

    "__pycache__",
    ".git",
    "1",
    "2",
    "1_Olds"

}


# Arquivos que não entram no mapa

ARQUIVOS_IGNORAR = {

    "Gerar_ArquivosApp.py",
    "ArquivosApp.py"

}



# ============================================================
# CLASSIFICAR ARQUIVO
# ============================================================

def classificar_categoria(caminho):

    caminho = caminho.lower()


    if "coletas" in caminho:
        return "DADOS"


    if "relatorios" in caminho:
        return "RELATORIOS"


    if "pages" in caminho:
        return "INTERFACE"


    if "teste" in caminho:
        return "TESTE"


    return "CORE"



# ============================================================
# TAMANHO
# ============================================================

def tamanho_kb(caminho):

    try:

        return round(
            os.path.getsize(caminho) / 1024,
            2
        )

    except:

        return 0



# ============================================================
# DATA ALTERAÇÃO
# ============================================================

def data_alteracao(caminho):

    try:

        data = datetime.datetime.fromtimestamp(
            os.path.getmtime(caminho)
        )

        return data.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    except:

        return ""



# ============================================================
# COLETAR ARQUIVOS
# ============================================================

def coletar_arquivos():

    lista = []


    for raiz, pastas, arquivos in os.walk(
        PASTA_PROJETO
    ):


        pastas[:] = [

            p for p in pastas

            if p not in PASTAS_IGNORAR

        ]


        for arquivo in arquivos:


            if arquivo in ARQUIVOS_IGNORAR:
                continue



            caminho = os.path.join(
                raiz,
                arquivo
            )


            relativo = os.path.relpath(
                caminho,
                PASTA_PROJETO
            )


            extensao = os.path.splitext(
                arquivo
            )[1]


            tipo = extensao.replace(
                ".",
                ""
            ).upper()



            lista.append({

                "arquivo": arquivo,

                "categoria":
                    classificar_categoria(
                        relativo
                    ),

                "local":
                    relativo,

                "tipo":
                    tipo,

                "tamanho_kb":
                    tamanho_kb(
                        caminho
                    ),

                "ultima_alteracao":
                    data_alteracao(
                        caminho
                    )

            })


    return sorted(
        lista,
        key=lambda x:x["local"]
    )



# ============================================================
# RESUMO
# ============================================================

def gerar_resumo(lista):

    resumo = {}


    for item in lista:

        tipo = item["tipo"]

        resumo[tipo] = resumo.get(
            tipo,
            0
        ) + 1


    return resumo



# ============================================================
# GERAR ARQUIVO
# ============================================================

def gerar():

    arquivos = coletar_arquivos()

    resumo = gerar_resumo(
        arquivos
    )


    data = datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    with open(
        ARQUIVO_SAIDA,
        "w",
        encoding="utf-8"
    ) as f:


        f.write(
f"""# ============================================================
# MAPA DO PROJETO - ANALISADOR FINANCEIRO
#
# GERADO AUTOMATICAMENTE
#
# Data geração:
# {data}
#
# Arquivos catalogados:
# {len(arquivos)}
#
# NÃO EDITAR MANUALMENTE
# ============================================================


ARQUIVOS_PROJETO = [
"""
        )


        for item in arquivos:

            f.write(
                repr(item)
            )

            f.write(
                ",\n"
            )


        f.write(
"""
]


RESUMO_PROJETO = """
        )


        f.write(
            repr(resumo)
        )


        f.write(
"""


def listar_arquivos():

    for item in ARQUIVOS_PROJETO:

        print("="*60)

        print("Arquivo:", item["arquivo"])

        print("Categoria:", item["categoria"])

        print("Local:", item["local"])

        print("Tipo:", item["tipo"])

        print("Tamanho KB:", item["tamanho_kb"])

        print(
            "Última alteração:",
            item["ultima_alteracao"]
        )



def listar_resumo():

    print("="*60)

    print(
        "RESUMO PROJETO ANALISADOR FINANCEIRO"
    )

    print("="*60)

    print(
        "Total arquivos:",
        len(ARQUIVOS_PROJETO)
    )


    print()


    for tipo,qtd in RESUMO_PROJETO.items():

        print(
            tipo,
            ":",
            qtd
        )



if __name__ == "__main__":

    listar_resumo()

"""
        )



    print()

    print("="*60)

    print(
        " GERADOR DE ARQUIVOS DO PROJETO V2.1"
    )

    print("="*60)

    print()

    print(
        "Arquivos encontrados:",
        len(arquivos)
    )

    print()

    print(
        "Catálogo gerado:"
    )

    print(
        ARQUIVO_SAIDA
    )

    print("="*60)



# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    gerar()