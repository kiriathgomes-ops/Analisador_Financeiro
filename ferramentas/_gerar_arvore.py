import os

# Pastas que não queremos na árvore (dados pesados, lixo, etc.)
IGNORAR = {
    '__pycache__', '.git', '.venv', 'venv', 'env', 
    'Coletas', 'Downloads', '.streamlit', 'lixeira_analise', 
    'ferramentas/fixes/backups', '.pytest_cache'
}

def gerar_arvore(diretorio, prefixo=""):
    linhas = []
    try:
        itens = sorted(os.listdir(diretorio))
    except PermissionError:
        return linhas
        
    # Filtra o que deve ser ignorado
    itens = [i for i in itens if i not in IGNORAR and not i.endswith('.pyc')]
    
    for i, item in enumerate(itens):
        caminho = os.path.join(diretorio, item)
        # Desenha os galhos
        conector = "└── " if i == len(itens) - 1 else "├── "
        
        if os.path.isdir(caminho):
            linhas.append(f"{prefixo}{conector}{item}/")
            # Se for pasta, entra recursivamente com o recuo correto
            novo_prefixo = prefixo + ("    " if i == len(itens) - 1 else "│   ")
            linhas.extend(gerar_arvore(caminho, novo_prefixo))
        else:
            linhas.append(f"{prefixo}{conector}{item}")
            
    return linhas

with open("arvore_projeto.txt", "w", encoding="utf-8") as f:
    f.write("Raiz do Projeto\n")
    for linha in gerar_arvore("."):
        f.write(linha + "\n")
        
print("✅ Árvore visual gerada com sucesso no arquivo: arvore_projeto.txt")