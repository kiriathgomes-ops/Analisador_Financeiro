from Coletas.ArquivosApp import ARQUIVOS_PROJETO


print("=" * 60)
print("TESTE INVENTÁRIO DO PROJETO")
print("=" * 60)


print("Quantidade de arquivos:", len(ARQUIVOS_PROJETO))


tipos = {}

for item in ARQUIVOS_PROJETO:
    tipo = item["tipo"]

    if tipo not in tipos:
        tipos[tipo] = 0

    tipos[tipo] += 1


print("\nArquivos por tipo:")

for tipo, quantidade in tipos.items():
    print(tipo, ":", quantidade)


print("\nÚltimos arquivos alterados:")

ordenados = sorted(
    ARQUIVOS_PROJETO,
    key=lambda x: x["ultima_alteracao"],
    reverse=True
)


for item in ordenados[:5]:
    print(
        item["arquivo"],
        "|",
        item["ultima_alteracao"]
    )