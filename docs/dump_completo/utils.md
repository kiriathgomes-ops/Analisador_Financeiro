# Dump completo - utils

Gerado em: 2026-09-27 22:07:53
Total de arquivos: 2

## Arvore

```
utils
|-- AnaliseGraficaSMC_Regras.json
`-- KeyManager.py
```

## Conteudo dos arquivos

### `utils/AnaliseGraficaSMC_Regras.json`

```json
{
  "timestamp": "2026-08-14T08:49:04.755778",
  "ativo": "WIN",
  "timeframe": "5m",
  "fonte": "regras_smc",
  "preco_atual": 170775.0,
  "timeframes_identificados": "5m",
  "bias_direcional": "ALTA",
  "direcao_estrutura": "ALTA",
  "bos": true,
  "choch": true,
  "confianca_visual": 95,
  "order_blocks": [
    {
      "tipo": "COMPRA",
      "preco": 170107.5,
      "high": 170150.0,
      "low": 170065.0
    },
    {
      "tipo": "COMPRA",
      "preco": 170267.5,
      "high": 170325.0,
      "low": 170210.0
    },
    {
      "tipo": "COMPRA",
      "preco": 170252.5,
      "high": 170280.0,
      "low": 170225.0
    }
  ],
  "fair_value_gaps": [
    {
      "tipo": "VENDA",
      "superior": 171615.0,
      "inferior": 171495.0,
      "preenchido": false
    },
    {
      "tipo": "VENDA",
      "superior": 171365.0,
      "inferior": 171140.0,
      "preenchido": false
    },
    {
      "tipo": "VENDA",
      "superior": 171100.0,
      "inferior": 170985.0,
      "preenchido": false
    },
    {
      "tipo": "COMPRA",
      "superior": 170000.0,
      "inferior": 169950.0,
      "preenchido": false
    },
    {
      "tipo": "COMPRA",
      "superior": 170310.0,
      "inferior": 170280.0,
      "preenchido": false
    },
    {
      "tipo": "COMPRA",
      "superior": 170515.0,
      "inferior": 170440.0,
      "preenchido": false
    },
    {
      "tipo": "COMPRA",
      "superior": 170600.0,
      "inferior": 170545.0,
      "preenchido": false
    },
    {
      "tipo": "COMPRA",
      "superior": 170725.0,
      "inferior": 170680.0,
      "preenchido": false
    }
  ],
  "liquidez": {
    "bsl": [
      170692.5,
      170342.5
    ],
    "ssl": []
  },
  "eventos_estrutura": [
    {
      "tipo": "CHOCH",
      "direcao": "BAIXA",
      "preco": 170340.0,
      "time": "2026-08-13T12:55:00"
    },
    {
      "tipo": "CHOCH",
      "direcao": "ALTA",
      "preco": 170685.0,
      "time": "2026-08-13T15:10:00"
    },
    {
      "tipo": "CHOCH",
      "direcao": "BAIXA",
      "preco": 170280.0,
      "time": "2026-08-13T13:15:00"
    },
    {
      "tipo": "CHOCH",
      "direcao": "ALTA",
      "preco": 170430.0,
      "time": "2026-08-13T15:00:00"
    },
    {
      "tipo": "BOS",
      "direcao": "ALTA",
      "preco": 170335.0,
      "time": "2026-08-13T14:00:00"
    },
    {
      "tipo": "BOS",
      "direcao": "ALTA",
      "preco": 170350.0,
      "time": "2026-08-13T15:15:00"
    }
  ],
  "swings_recentes": [
    {
      "tipo": "LOW",
      "preco": 170340.0,
      "time": "2026-08-13T11:50:00"
    },
    {
      "tipo": "HIGH",
      "preco": 170685.0,
      "time": "2026-08-13T12:10:00"
    },
    {
      "tipo": "LOW",
      "preco": 170280.0,
      "time": "2026-08-13T12:40:00"
    },
    {
      "tipo": "HIGH",
      "preco": 170430.0,
      "time": "2026-08-13T12:50:00"
    },
    {
      "tipo": "LOW",
      "preco": 170045.0,
      "time": "2026-08-13T13:15:00"
    },
    {
      "tipo": "HIGH",
      "preco": 170335.0,
      "time": "2026-08-13T13:25:00"
    },
    {
      "tipo": "HIGH",
      "preco": 170350.0,
      "time": "2026-08-13T13:40:00"
    },
    {
      "tipo": "LOW",
      "preco": 170100.0,
      "time": "2026-08-13T13:55:00"
    },
    {
      "tipo": "LOW",
      "preco": 170210.0,
      "time": "2026-08-13T14:50:00"
    },
    {
      "tipo": "HIGH",
      "preco": 170970.0,
      "time": "2026-08-13T15:15:00"
    }
  ],
  "estruturas_coletadas": [
    "170970: Swing High",
    "170108: OB COMPRA (170065-170150)",
    "170268: OB COMPRA (170210-170325)",
    "170252: OB COMPRA (170225-170280)",
    "171555: FVG VENDA (171495-171615)",
    "171252: FVG VENDA (171140-171365)",
    "171042: FVG VENDA (170985-171100)",
    "169975: FVG COMPRA (169950-170000)",
    "170295: FVG COMPRA (170280-170310)",
    "170478: FVG COMPRA (170440-170515)",
    "170572: FVG COMPRA (170545-170600)",
    "170702: FVG COMPRA (170680-170725)"
  ],
  "liquidez_relevante": [
    "BSL: 170692 (equal highs / liquidez de compra acima)",
    "BSL: 170342 (equal highs / liquidez de compra acima)"
  ],
  "zonas_de_interesse_e_cenarios": [
    "Cenário Comprador: defesa na região 170252 (OB/FVG de compra) visando 170692.",
    "Cenário alternativo: varredura de liquidez abaixo antes da continuação de alta."
  ],
  "entrada_sugerida": 170280.0,
  "stop_sugerido": 170175.0,
  "alvos": [
    170692.0,
    170342.0
  ],
  "metadados": {
    "n_candles": 120,
    "n_swings": 26,
    "n_fvgs_abertos": 8,
    "n_obs": 3,
    "config": {
      "swing_left": 2,
      "swing_right": 2,
      "fvg_min_pontos": 20.0,
      "eq_tol_pontos": 15.0,
      "max_niveis": 12,
      "max_fvgs": 8,
      "max_obs": 6,
      "lookback": 120
    }
  },
  "simbolo_mt5": "WINV26"
}
```

### `utils/KeyManager.py`

```python
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

```
