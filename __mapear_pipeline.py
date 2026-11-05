# -*- coding: utf-8 -*-
import ast
import os

ARQUIVO_ALVO = "main_pipeline.py"
PASTA_RAIZ = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_SAIDA = os.path.join(PASTA_RAIZ, "fluxo_pipeline.md")

def analisar_main_pipeline():
    caminho = os.path.join(PASTA_RAIZ, ARQUIVO_ALVO)
    
    if not os.path.exists(caminho):
        print(f"❌ Arquivo {ARQUIVO_ALVO} não encontrado na pasta.")
        return

    with open(caminho, "r", encoding="utf-8") as f:
        conteudo = f.read()

    arvore = ast.parse(conteudo)
    imports_locais = []

    for node in ast.walk(arvore):
        # Pega 'import script' e 'from script import x'
        if isinstance(node, ast.Import):
            for n in node.names:
                imports_locais.append(f"{n.name}.py")
        elif isinstance(node, ast.ImportFrom):
            if node.module and not node.module.startswith("config"):
                imports_locais.append(f"{node.module}.py")

    # Remove duplicatas e ordena
    imports_locais = sorted(list(set(imports_locais)))

    # Constrói o Mermaid
    mermaid_lines = ["```mermaid", "graph TD"]
    mermaid_lines.append("    classDef main fill:#0e4b99,stroke:#00d4ff,stroke-width:3px,color:#fff;")
    mermaid_lines.append("    classDef script fill:#2b313c,stroke:#8b949e,stroke-width:2px,color:#fff;")
    mermaid_lines.append(f'    MAIN["🎯 {ARQUIVO_ALVO}"]:::main')
    
    for imp in imports_locais:
        if os.path.exists(os.path.join(PASTA_RAIZ, imp)): # Só desenha se o arquivo existir na pasta
            node_id = imp.replace(".", "_").replace("-", "_")
            mermaid_lines.append(f'    S_{node_id}["📄 {imp}"]:::script')
            mermaid_lines.append(f"    MAIN -->|chama| S_{node_id}")
            
    mermaid_lines.append("```")

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        f.write(f"# 🗺️ Mapa Focado: {ARQUIVO_ALVO}\n\n")
        f.write(f"O arquivo `{ARQUIVO_ALVO}` atua como maestro, chamando os seguintes módulos:\n\n")
        f.write("\n".join(mermaid_lines))
        
    print(f"✅ Mapa gerado: {ARQUIVO_SAIDA}")
    print(f"Total de scripts chamados: {len(imports_locais)}")

if __name__ == "__main__":
    analisar_main_pipeline()