import os


def deve_ignorar(nome, lista_ignorar):
    """Verifica se o arquivo ou pasta deve ser ignorado com base nas regras."""
    for padrao in lista_ignorar:
        # Trata seletores coringa simples como '.git*'
        if padrao.endswith("*"):
            if nome.startswith(padrao[:-1]):
                return True
        elif nome == padrao:
            return True
    return False


def gerar_arvore(diretorio, ignorar, prefixo=""):
    """Gera uma representação textual da árvore ignorando os padrões configurados."""
    linhas = []
    elementos = [
        item
        for item in sorted(os.listdir(diretorio))
        if not deve_ignorar(item, ignorar)
    ]
    total = len(elementos)

    for i, elemento in enumerate(elementos):
        caminho_completo = os.path.join(diretorio, elemento)
        eh_ultimo = i == total - 1
        ramo = "└── " if eh_ultimo else "├── "

        linhas.append(f"{prefixo}{ramo}{elemento}")

        if os.path.isdir(caminho_completo):
            extensao_prefixo = "    " if eh_ultimo else "│   "
            linhas.extend(
                gerar_arvore(caminho_completo, ignorar, prefixo + extensao_prefixo)
            )

    return linhas


def consolidar_arquivos(
    diretorio_raiz, arquivo_saida, ignorar, extensoes_permitidas=None
):
    """Consolida a árvore e o conteúdo dos arquivos ignorando os itens listados."""
    caminho_raiz = os.path.abspath(diretorio_raiz)

    with open(arquivo_saida, "w", encoding="utf-8") as f_out:
        # 1. Desenha o mapa da árvore filtrado
        f_out.write("==================================================\n")
        f_out.write("          MAPA DA ÁRVORE DE ARQUIVOS             \n")
        f_out.write("==================================================\n")
        f_out.write(f"{os.path.basename(caminho_raiz)}/\n")

        linhas_arvore = gerar_arvore(caminho_raiz, ignorar)
        f_out.write("\n".join(linhas_arvore))
        f_out.write("\n\n" + "=" * 50 + "\n\n")

        # 2. Leitura e junção dos conteúdos
        for raiz, pastas, arquivos in os.walk(caminho_raiz):
            # Filtra pastas para não entrar em diretórios ignorados (ex: .git)
            pastas[:] = [
                p for p in pastas if not deve_ignorar(p, ignorar)
            ]

            for arquivo in sorted(arquivos):
                if deve_ignorar(arquivo, ignorar):
                    continue

                caminho_completo = os.path.join(raiz, arquivo)

                # Evita ler o próprio arquivo final
                if os.path.abspath(caminho_completo) == os.path.abspath(
                    arquivo_saida
                ):
                    continue

                if extensoes_permitidas:
                    if not any(arquivo.endswith(ext) for ext in extensoes_permitidas):
                        continue

                caminho_relativo = os.path.relpath(caminho_completo, caminho_raiz)

                f_out.write(
                    f"==================================================\n"
                )
                f_out.write(f"ARQUIVO: {caminho_relativo}\n")
                f_out.write(
                    f"==================================================\n\n"
                )

                try:
                    with open(caminho_completo, "r", encoding="utf-8") as f_in:
                        f_out.write(f_in.read())
                        f_out.write("\n\n")
                except UnicodeDecodeError:
                    f_out.write(
                        "[AVISO: Arquivo binário ou codificação incompatível - Ignorado]\n\n"
                    )
                except Exception as e:
                    f_out.write(f"[ERRO AO LER ARQUIVO: {str(e)}]\n\n")


# --- CONFIGURAÇÕES ---
if __name__ == "__main__":
    PASTA_ALVO = "."
    ARQUIVO_FINAL = "consolidado_projeto.txt"

    # Arquivos, pastas ou extensões coringa para IGNORAR na varredura
    IGNORAR_PADROES = [
        ".env*",        # Pega .env, .env.local, .env.example, etc.
        ".git*",        # Pega a pasta .git, .gitignore, .gitattributes
        "__pycache__",  # Cache do Python
        ".venv",        # Ambientes virtuais
        "venv",
        "*_rom*.json",  # Qualquer arquivo que contenha '_rom' e termine com .json
    ]

    consolidar_arquivos(
        PASTA_ALVO, ARQUIVO_FINAL, ignorar=IGNORAR_PADROES
    )
    print(f"Arquivo gerado com sucesso sem os itens ignorados: {ARQUIVO_FINAL}")