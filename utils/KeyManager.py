# utils/KeyManager.py
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

class KeyManager:
    """
    Gerenciador de chaves API com rotação automática
    """
    
    def __init__(self):
        self.keys = self._carregar_chaves()
        self.index = 0
        self.log_file = Path("Coletas/token_usage.log")
        self.log_file.parent.mkdir(exist_ok=True)
    
    def _carregar_chaves(self) -> list:
        """Carrega todas as chaves do .env"""
        keys = []
        i = 1
        while True:
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if key:
                keys.append({
                    "key": key,
                    "nome": f"Key_{i}",
                    "ativa": True,
                    "ultimo_uso": None,
                    "total_tokens": 0,
                    "rate_limit_ate": None
                })
                i += 1
            else:
                break
        
        # Fallback: usa a chave padrão
        if not keys:
            key_padrao = os.getenv("GROQ_API_KEY")
            if key_padrao:
                keys.append({
                    "key": key_padrao,
                    "nome": "Key_Padrao",
                    "ativa": True,
                    "ultimo_uso": None,
                    "total_tokens": 0,
                    "rate_limit_ate": None
                })
        
        print(f"🔑 {len(keys)} chave(s) carregada(s)")
        return keys
    
    def get_next_key(self) -> Optional[str]:
        """Retorna a próxima chave disponível"""
        if not self.keys:
            print("❌ Nenhuma chave configurada!")
            return None
        
        tentativas = 0
        max_tentativas = len(self.keys)
        
        while tentativas < max_tentativas:
            key_info = self.keys[self.index]
            
            # Verifica se a chave está em rate limit
            if key_info["rate_limit_ate"]:
                if datetime.now() < key_info["rate_limit_ate"]:
                    self.index = (self.index + 1) % len(self.keys)
                    tentativas += 1
                    continue
            
            # Chave disponível
            key_info["ultimo_uso"] = datetime.now()
            self.index = (self.index + 1) % len(self.keys)
            print(f"🔑 Usando {key_info['nome']}")
            return key_info["key"]
        
        print("⚠️ Todas as chaves estão em rate limit!")
        return None
    
    def registrar_uso(self, key_utilizada: str, tokens_usados: int):
        """Registra o uso de uma chave"""
        for k in self.keys:
            if k["key"] == key_utilizada:
                k["total_tokens"] += tokens_usados
                k["ultimo_uso"] = datetime.now()
                
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"{k['nome']}: {tokens_usados} tokens | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                break
    
    def marcar_rate_limit(self, key_utilizada: str, tempo_espera_minutos: int = 120):
        """Marca uma chave como em rate limit"""
        for k in self.keys:
            if k["key"] == key_utilizada:
                k["rate_limit_ate"] = datetime.now() + timedelta(minutes=tempo_espera_minutos)
                print(f"⏳ {k['nome']} em rate limit até {k['rate_limit_ate'].strftime('%H:%M')}")
                break
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna o status de todas as chaves"""
        status = {}
        for k in self.keys:
            nome = k["nome"]
            status[nome] = {
                "ativa": k["ativa"],
                "total_tokens": k["total_tokens"],
                "rate_limit_ate": k["rate_limit_ate"].strftime("%H:%M") if k["rate_limit_ate"] else None,
                "ultimo_uso": k["ultimo_uso"].strftime("%H:%M:%S") if k["ultimo_uso"] else "Nunca"
            }
        return status

# Instância global
key_manager = KeyManager()

def get_groq_client():
    """Retorna um cliente Groq com a próxima chave disponível"""
    from groq import Groq
    
    key = key_manager.get_next_key()
    if not key:
        raise Exception("❌ Nenhuma chave API disponível no momento!")
    
    return Groq(api_key=key), key