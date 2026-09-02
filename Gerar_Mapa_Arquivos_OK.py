# -*- coding: utf-8 -*-
"""
Módulo: Gerar_Mapa_Arquivos_OK.py
Objetivo: 
  1. Mapear 100% da árvore de arquivos e pastas do projeto (Sem filtros).
  2. Dump do conteúdo dos arquivos aplicando regras estritas de exclusão.
"""

import os
import fnmatch


def deve_ignorar_conteudo(caminho_relativo, nome_item, lista_ignorar):
    """
    Verifica se o CONTEÚDO de um arquivo deve ser ignorado na etapa de dump.
    Testa tanto pelo nome do item quanto pelo caminho relativo normalizado.
    """
    caminho_norm = caminho_relativo.replace("\\", "/")
    
    for padrao in lista_ignorar:
        padrao_norm = padrao.strip("/").strip("\\")
        
        # Testa pelo nome direto do item
        if fnmatch.fnmatch(nome_item, padrao) or fnmatch.fnmatch(nome_item, padrao_norm):
            return True
            
        # Testa pelo caminho relativo
        if fnmatch.fnmatch(caminho_norm, padrao) or fnmatch.fnmatch(caminho_norm, f"*{padrao_norm}*"):
            return True
            
    return False


def gerar_arvore_completa(diretorio, prefixo="", caminho_base=None):
    """Gera uma representação textual da árvore MAPPING 100% dos arquivos e pastas (sem exclusões)."""
    if caminho_base is None:
        caminho_base = diretorio

    linhas = []
    
    try:
        elementos = sorted(os.listdir(diretorio))
    except PermissionError:
        return [f"{prefixo}[Acesso Negado]"]

    total = len(elementos)

    for i, elemento in enumerate(elementos):
        caminho_completo = os.path.join(diretorio, elemento)
        eh_ultimo = (i == total - 1)
        ramo = "└── " if eh_ultimo else "├── "

        linhas.append(f"{prefixo}{ramo}{elemento}")

        if os.path.isdir(caminho_completo):
            extensao_prefixo = "    " if eh_ultimo else "│   "
            linhas.extend(
                gerar_arvore_completa(caminho_completo, prefixo + extensao_prefixo, caminho_base)
            )

    return linhas


def consolidar_arquivos(diretorio_raiz, arquivo_saida, ignorar_no_dump, extensoes_permitidas=None):
    """Consolida a árvore completa e faz o dump seletivo do conteúdo dos arquivos."""
    caminho_raiz = os.path.abspath(diretorio_raiz)
    arquivo_saida_abs = os.path.abspath(arquivo_saida)

    with open(arquivo_saida, "w", encoding="utf-8") as f_out:
        # ----------------------------------------------------------------------
        # ETAPA 1: MAPA DA ÁRVORE 100% COMPLETO (SEM NENHUM FILTRO)
        # ----------------------------------------------------------------------
        f_out.write("==================================================\n")
        f_out.write("     MAPA DA ÁRVORE DE ARQUIVOS (COMPLETO)       \n")
        f_out.write("==================================================\n")
        f_out.write(f"{os.path.basename(caminho_raiz)}/\n")

        linhas_arvore = gerar_arvore_completa(caminho_raiz)
        f_out.write("\n".join(linhas_arvore))
        f_out.write("\n\n" + "=" * 50 + "\n\n")

        # ----------------------------------------------------------------------
        # ETAPA 2: DUMP DO CONTEÚDO DOS ARQUIVOS (COM FILTROS DE EXCLUSÃO)
        # ----------------------------------------------------------------------
        f_out.write("==================================================\n")
        f_out.write("     DUMP DO CONTEÚDO DOS ARQUIVOS (FILTRADO)     \n")
        f_out.write("==================================================\n\n")

        for raiz, pastas, arquivos in os.walk(caminho_raiz):
            rel_raiz = os.path.relpath(raiz, caminho_raiz)

            # Otimização: Evita percorrer subpastas pesadas se elas estiverem na lista de exclusão
            pastas[:] = [
                p for p in pastas 
                if not deve_ignorar_conteudo(os.path.join(rel_raiz, p), p, ignorar_no_dump)
            ]

            for arquivo in sorted(arquivos):
                caminho_completo = os.path.join(raiz, arquivo)
                caminho_relativo = os.path.relpath(caminho_completo, caminho_raiz)

                # Evita ler o próprio arquivo final gerado
                if os.path.abspath(caminho_completo) == arquivo_saida_abs:
                    continue

                # Aplica as regras de exclusão no dump
                if deve_ignorar_conteudo(caminho_relativo, arquivo, ignorar_no_dump):
                    continue

                # Valida permissão de extensão (se informada)
                if extensoes_permitidas:
                    if not any(arquivo.lower().endswith(ext.lower()) for ext in extensoes_permitidas):
                        continue

                f_out.write("==================================================\n")
                f_out.write(f"ARQUIVO: {caminho_relativo}\n")
                f_out.write("==================================================\n\n")

                try:
                    with open(caminho_completo, "r", encoding="utf-8", errors="replace") as f_in:
                        conteudo = f_in.read()
                        f_out.write(conteudo)
                        if not conteudo.endswith("\n"):
                            f_out.write("\n")
                        f_out.write("\n\n")
                except Exception as e:
                    f_out.write(f"[ERRO AO LER ARQUIVO: {str(e)}]\n\n")


# ==============================================================================
# CONFIGURAÇÃO DE EXCLUSÕES (EDITE AQUI PARA ADICIONAR MAIS FILTROS)
# ==============================================================================
if __name__ == "__main__":
    PASTA_ALVO = "."
    ARQUIVO_FINAL = "consolidado_projeto.txt"

    # --------------------------------------------------------------------------
    # 🔴 ÁREA DE CONFIGURAÇÃO DE EXCLUSÕES NO DUMP DO CONTEÚDO
    # Adicione ou remova padrões coringa (wildcards) na lista abaixo:
    # --------------------------------------------------------------------------
    EXCLUIR_DO_DUMP = [
        # Arquivos de Documentação e Leitura
        "*.md",               # Exclui todos os arquivos Markdown (.md)
        
        # Arquivos e Pastas do Sistema e Ambiente
        ".env*",              # Variáveis de ambiente
        ".git*",              # Diretório e configurações do Git
        "__pycache__",        # Cache compilado do Python
        ".venv",              # Ambientes virtuais
        "venv",
        ".vscode",            # Configurações do VSCode
        "*.pyc",              # Bytecodes compilados
        
        # Dados Temporários e Histórico
        "*_rom*.json",        # Arquivos temporários _rom
        "Historico",          # Pasta de histórico
        "*/Historico/*",
        "*/Limpar/*",
        
        # Mídias e Relatórios Gerados
        "*.png",              # Capturas de tela e imagens
        "*.jpg",
        "*.jpeg",
        "consolidado_*.txt"   # Evita ler consolidados antigos


        
        # ➕ Adicione aqui novos padrões para excluir no dump (ex: "*.log", "pasta_temp")
    ]

    # --------------------------------------------------------------------------
    # 🟢 EXTENSÕES PERMITIDAS PARA LEITURA NO DUMP
    # --------------------------------------------------------------------------
    EXTENSOES_PERMITIDAS_DUMP = [".py", ".json", ".txt", ".css", ".html"]

    consolidar_arquivos(
        PASTA_ALVO,
        ARQUIVO_FINAL,
        ignorar_no_dump=EXCLUIR_DO_DUMP,
        extensoes_permitidas=EXTENSOES_PERMITIDAS_DUMP
    )

    print(f"✅ Concluído! Árvore completa e dump filtrado gerados em: {ARQUIVO_FINAL}")