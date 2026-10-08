# -*- coding: utf-8 -*-
"""
Módulo: Gerar_Mapa_Projeto.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Classificar os arquivos do inventário técnico e gerar o Mapa_Projeto.json.
"""

import json
import os
from datetime import datetime
from config import COLETAS_DIR

# Definição segura do arquivo de saída baseado no config
FILE_MAPA_PROJETO = COLETAS_DIR / "Mapa_Projeto.json"

def classificar_arquivo(nome_arquivo: str, local_relativo: str) -> str:
    """
    Classifica os módulos do projeto em categorias lógicas baseadas 
    na nomenclatura e na estrutura de pastas da V1 e V2.
    """
    nome = nome_arquivo.lower()
    local = local_relativo.lower()

    # 1. Novas Estruturas e Contratos Oficiais da V2
    if "v2/" in local or "v2_" in nome:
        if "pages" in local or "page" in nome:
            return "INTERFACE_V2"
        return "CORE_V2"

    # 2. Módulos de Notícias, Calendário e Macro
    if "noticia" in nome or "calendario" in nome:
        if nome.endswith(".py"):
            return "NOTICIAS_MACRO"
        return "DADOS"

    # 3. Motores Ingestão e Coletores
    if "coleta" in nome or "coletor" in nome:
        return "COLETA"

    # 4. Sanitização, Validação e Testes Smoke
    if "valid" in nome or "teste" in nome or "smoke" in nome:
        return "VALIDACAO"

    # 5. Motores de Cálculo e Estimativas Quantitativas
    if "calcul" in nome or "metrica" in nome or "estimativa" in nome:
        return "CALCULOS"

    # 6. Orquestradores, Pipelines e Core Engines
    if "engine" in nome or "decisao" in nome or "pipeline" in nome:
        return "CORE_V1"

    # 7. Relatórios de Auditoria e Mensageria
    if "relatorio" in nome or "mensagem" in nome:
        return "RELATORIOS"

    # 8. Interfaces Visuais Standard (Streamlit Pages)
    if "app" in nome or "page" in nome or "pages/" in local:
        return "INTERFACE_V1"

    # 9. Arquivos de Dados Soltos
    if nome.endswith(".json") or nome.endswith(".csv") or nome.endswith(".log"):
        return "DADOS"

    return "OUTROS"

def executar_mapeamento_projeto():
    print("=" * 60)
    print(" 🗺️ EXECUTANDO ATUALIZAÇÃO DO MAPA LOGÍSTICO DO PROJETO (V2)")
    print("=" * 60)

    # Importa de forma segura o inventário gerado pela etapa anterior do pipeline
    try:
        from Coletas.ArquivosApp import ARQUIVOS_PROJETO
    except ImportError:
        print("❌ [ERRO] Inventário básico 'ArquivosApp.py' não localizado na pasta Coletas.")
        print("   -> Certifique-se de que a etapa 'Gerar_Mapa_Inventario_Tecnico.py' rodou primeiro.")
        return

    mapa = {
        "metadata": {
            "projeto": "Analisador_Financeiro",
            "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fonte": "Coletas/ArquivosApp.py",
            "versao_arquitetura": "V2.0 (Fase 3 Unificada)"
        },
        "estrutura": {},
        "total_arquivos_catalogados": len(ARQUIVOS_PROJETO),
    }

    # Distribui os arquivos nas novas gavetas lógicas da V2
    for item in ARQUIVOS_PROJETO:
        categoria = classificar_arquivo(item["arquivo"], item["local"])

        if categoria not in mapa["estrutura"]:
            mapa["estrutura"][categoria] = []

        mapa["estrutura"][categoria].append({
            "arquivo": item["arquivo"],
            "local": item["local"],
            "tipo": item["tipo"],
            "tamanho_kb": item["tamanho_kb"],
            "ultima_alteracao": item["ultima_alteracao"],
        })

    # Persistência estável em disco do arquivo de auditoria consumido pelo Streamlit
    try:
        COLETAS_DIR.mkdir(parents=True, exist_ok=True)
        with open(FILE_MAPA_PROJETO, "w", encoding="utf-8") as arquivo:
            json.dump(mapa, arquivo, indent=4, ensure_ascii=False)
            
        print(f"📊 Inventário Analisado: {mapa['total_arquivos_catalogados']} arquivos.")
        for categoria, lista in mapa["grid_estrutura" if "grid" in mapa else "estrutura"].items():
            print(f"  • {categoria:<15} : {len(lista)} arquivos cadastrados")
            
        print(f"\n✅ Mapa do projeto gerado com sucesso em: {FILE_MAPA_PROJETO.name}\n")
    except Exception as e:
        print(f"❌ Erro ao salvar o arquivo Mapa_Projeto.json: {e}")

if __name__ == "__main__":
    executar_mapeamento_projeto()
