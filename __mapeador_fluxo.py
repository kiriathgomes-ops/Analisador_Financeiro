# -*- coding: utf-8 -*-
"""
Mapeador de Fluxo de Dados e Dependências
Lê os arquivos .py do diretório atual, extrai imports e arquivos JSON manipulados.
Gera um diagrama Mermaid no arquivo 'fluxo_do_app.md'.
"""

import ast
import os
import re

# Pasta onde estão seus scripts (ajuste se necessário)
PASTA_RAIZ = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_SAIDA = os.path.join(PASTA_RAIZ, "fluxo_do_app.md")

# Regex para encontrar nomes de arquivos JSON no código
REGEX_JSON = re.compile(r'["\']([a-zA-Z0-9_\-\.\\/]+\.json)["\']')

def analisar_arquivo(caminho):
    """Analisa um arquivo .py e extrai imports e arquivos JSON."""
    imports = []
    jsons = set()
    
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = f.read()
            
        # 1. Encontra os JSONs via Regex (mais seguro para caminhos dinâmicos)
        matches = REGEX_JSON.findall(conteudo)
        for m in matches:
            # Pega apenas o nome do arquivo, ignorando o caminho completo
            nome_json = os.path.basename(m)
            jsons.add(nome_json)
            
        # 2. Encontra os imports via AST (Abstract Syntax Tree)
        arvore = ast.parse(conteudo)
        for node in ast.walk(arvore):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.append(n.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
                    
    except Exception as e:
        print(f"Erro ao ler {caminho}: {e}")
        
    return imports, jsons

def mapear_projeto():
    scripts = [f for f in os.listdir(PASTA_RAIZ) if f.endswith(".py") and f != os.path.basename(__file__)]
    
    mermaid_lines = ["```mermaid", "graph TD"]
    
    # Estilos
    mermaid_lines.append("    classDef script fill:#2b313c,stroke:#00d4ff,stroke-width:2px,color:#fff;")
    mermaid_lines.append("    classDef data fill:#0d381e,stroke:#22c55e,stroke-width:2px,color:#fff;")
    mermaid_lines.append("    classDef ext fill:#382b0d,stroke:#ffab00,stroke-width:2px,color:#fff;")
    
    todos_jsons = set()
    
    for script in scripts:
        caminho = os.path.join(PASTA_RAIZ, script)
        imports, jsons = analisar_arquivo(caminho)
        
        script_id = f"S_{script.replace('.', '_').replace('-', '_')}"
        mermaid_lines.append(f'    {script_id}["📄 {script}"]:::script')
        
        # Mapeia imports entre scripts locais
        for imp in imports:
            imp_script = f"{imp}.py"
            if imp_script in scripts:
                imp_id = f"S_{imp_script.replace('.', '_').replace('-', '_')}"
                mermaid_lines.append(f"    {script_id} -->|importa| {imp_id}")
                
        # Mapeia arquivos JSON
        for j in jsons:
            todos_jsons.add(j)
            json_id = f"D_{j.replace('.', '_').replace('-', '_')}"
            
            # Como não sabemos se lê ou escreve apenas olhando o nome, 
            # assumimos que o script se conecta ao dado.
            mermaid_lines.append(f"    {script_id} -.->|usa| {json_id}")
            
    # Adiciona os JSONs no gráfico
    for j in todos_jsons:
        json_id = f"D_{j.replace('.', '_').replace('-', '_')}"
        mermaid_lines.append(f'    {json_id}[("💾 {j}")]:::data')
        
    mermaid_lines.append("```")
    
    # Salva o resultado
    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        f.write("# 🗺️ Mapa de Fluxo do Aplicativo\n\n")
        f.write("Este diagrama foi gerado automaticamente pela análise estática dos scripts.\n\n")
        f.write("\n".join(mermaid_lines))
        
    print(f"✅ Mapa gerado com sucesso em: {ARQUIVO_SAIDA}")

if __name__ == "__main__":
    mapear_projeto()