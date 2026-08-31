# -*- coding: utf-8 -*-
"""
Módulo: utils/KeyManager.py
Versão: 2.1 - Blindagem de Credenciais (V2)
Objetivo: Gerenciar, validar e mascarar chaves de API de forma segura.
"""

import os
import sys
import logging
from pathlib import Path

# Garante a carga das variáveis do .env a partir da raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=BASE_DIR / ".env")
except ImportError:
    pass

# Configuração básica de segurança de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

class KeyManager:
    """
    Centraliza a validação, carga e mascaramento de credenciais críticas
    do ecossistema quantitativo.
    """
    def __init__(self):
        # Definição das chaves obrigatórias mapeadas na V2
        self.chaves_requeridas = [
            "FINNHUB_API_KEY",
            "GROQ_API_KEY",
            "TELEGRAM_TOKEN",
            "TELEGRAM_CHAT",
            "MT5_LOGIN"
        ]

    def verificar_presenca_credenciais(self) -> dict:
        """
        Varre o ambiente e retorna um dicionário com o status de presença (True/False)
        de cada token, sem expor os valores confidenciais.
        """
        status_chaves = {}
        for chave in self.chaves_requeridas:
            valor = os.getenv(chave)
            status_chaves[chave] = bool(valor and len(valor.strip()) > 0)
        return status_chaves

    def obter_chave_mascarada(self, nome_chave: str) -> str:
        """
        Retorna uma versão higienizada e mascarada de uma chave para auditoria visual na UI.
        Exemplo: gsk_u...xxxx
        """
        valor = os.getenv(nome_chave)
        if not valor:
            return "❌ AUSENTE NO ARQUIVO .ENV"
        
        valor_limpo = valor.strip()
        if len(valor_limpo) <= 8:
            return "⚠️ CONFIGURAÇÃO INVÁLIDA / CHAVE CURTA CRÍTICA"
            
        # Máscara de segurança: mostra os primeiros 5 caracteres e os últimos 4
        return f"✅ ATIVO ({valor_limpo[:5]}...{valor_limpo[-4:]})"

    def obter_cliente_groq(self):
        """
        Instancia e retorna o cliente Groq de inferência de IA isolando erros de token
        para evitar queda total do orquestrador do pipeline.
        """
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            logging.error("[KEYMANAGER] GROQ_API_KEY não localizada no ambiente.")
            return None
            
        try:
            from groq import Groq
            # Retorna o cliente autenticado de forma isolada
            return Groq(api_key=groq_key.strip())
        except Exception as e:
            logging.error(f"[KEYMANAGER] Falha ao instanciar o cliente Groq Cloud: {e}")
            return None

# Instanciação global do módulo de controle de segurança do projeto
key_manager = KeyManager()

# Atalhos de compatibilidade (Aliases) para o pipeline principal
get_groq_client = key_manager.get_groq_client if hasattr(key_manager, 'get_groq_client') else key_manager.obter_cliente_groq

if __name__ == "__main__":
    print("=" * 60)
    print(" 🔒 AUDITORIA DE CRIPTOGRAFIA E CHAVES (SMOKE CHECK)")
    print("=" * 60)
    
    status = key_manager.verificar_presenca_credenciais()
    for k, v in status.items():
        status_txt = "PRESENTE (OK)" if v else "⚠️ AUSENTE"
        print(f"  • {k:<18} : {status_txt}")
        if v:
            print(f"    └─ Máscara UI  : {key_manager.obter_chave_mascarada(k)}")
    print("=" * 60)
