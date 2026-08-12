#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Criador da estrutura V2 do Analisador Financeiro.
Execute uma vez para gerar a nova arquitetura isolada.
"""

import os
import sys
from pathlib import Path

# ============================================================
# CONTEÚDO DOS ARQUIVOS
# ============================================================

CONTRATO_MARKET = '''# core/contracts/market_context.py
"""
MarketContext: estado consolidado do mercado.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict
from datetime import datetime


@dataclass
class AtivoSnapshot:
    """Snapshot de um ativo financeiro."""
    preco: float
    variacao_pct: float
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None

    def __post_init__(self):
        self.variacao_pct = float(self.variacao_pct)


@dataclass
class MarketContext:
    """
    Contexto completo do mercado no momento da análise.
    """
    timestamp: datetime

    # Ativos principais
    win_fut: AtivoSnapshot
    wdo_fut: AtivoSnapshot
    win_ajuste: float
    wdo_ajuste: float
    ptax: float

    # Exterior
    sp500: AtivoSnapshot
    nasdaq: AtivoSnapshot
    vix: AtivoSnapshot
    dxy: AtivoSnapshot
    ewz: AtivoSnapshot

    # Commodities
    iron_ore: AtivoSnapshot
    crude_oil: AtivoSnapshot
    gold: AtivoSnapshot

    # ADRs Brasileiras
    adrs: Dict[str, AtivoSnapshot] = field(default_factory=dict)

    # Indicadores calculados
    indicador_mercado_externo: Optional[float] = None
    indicador_adrs_brasileiras: Optional[float] = None
    spread_wdo_ptax_pontos: Optional[float] = None
    inclinacao_di_bps: Optional[float] = None

    # Tendência de 15 minutos
    tendencia_win: Optional[str] = None
    tendencia_win_padrao: Optional[str] = None

    metadados: Dict = field(default_factory=dict)
'''

CONTRATO_PREDICTION = '''# core/contracts/prediction_context.py
"""
PredictionContext: saída do motor de previsão (Novo Motor).
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime


@dataclass
class PredictionContext:
    """
    Resultado da previsão de abertura gerada pelo Novo Motor.
    """
    timestamp: datetime
    ativo: str
    abertura_projetada: float
    faixa_provavel_inferior: float
    faixa_provavel_superior: float

    gap_pontos: float
    gap_percentual: float
    gap_intensidade: str
    classificacao_gap: str

    direcao_prevista: str
    score: float
    score_classificacao: str
    score_detalhes: Dict[str, float] = field(default_factory=dict)

    analise_ajuste: Dict = field(default_factory=dict)
    cenario_principal: Dict = field(default_factory=dict)
    cenario_alternativo: Dict = field(default_factory=dict)

    metadados: Dict = field(default_factory=dict)
'''

CONTRATO_NEWS = '''# core/contracts/news_context.py
"""
NewsContext: impacto de notícias econômicas.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime


@dataclass
class NewsContext:
    timestamp: datetime
    impacto_total: int
    classificacao_risco: str
    tem_3_estrelas_brasil_0900: bool
    tem_3_estrelas_outros_horarios: bool
    tem_multiplas_2_estrelas_mesmo_horario: bool
    risco_abertura_win: bool

    eventos_3_estrelas: List[Dict] = field(default_factory=list)
    horarios_multiplas_2_estrelas: List[Dict] = field(default_factory=list)
    metadados: Dict = field(default_factory=dict)
'''

CONTRATO_VISION = '''# core/contracts/vision_context.py
"""
VisionContext: análise estrutural SMC/ICT (futuro).
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class VisionContext:
    timestamp: datetime
    ativo: str
    direcao_estrutura: str
    bos: bool
    choch: bool
    liquidity_zones: List[float] = field(default_factory=list)
    order_blocks: List[Dict[str, float]] = field(default_factory=list)
    fair_value_gaps: List[Dict[str, float]] = field(default_factory=list)
    suportes: List[float] = field(default_factory=list)
    resistencias: List[float] = field(default_factory=list)
    entrada_sugerida: Optional[float] = None
    stop_sugerido: Optional[float] = None
    alvos: List[float] = field(default_factory=list)
    confianca_visual: int = 0
    metadados: Dict = field(default_factory=dict)
'''

CONTRATO_DECISION = '''# core/contracts/decision_context.py
"""
DecisionContext: decisão operacional final.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime


@dataclass
class DecisionContext:
    timestamp: datetime
    ativo: str
    vies_final: str
    confianca: int

    entrada: Optional[float] = None
    stop_loss: Optional[float] = None
    alvo_1: Optional[float] = None
    alvo_2: Optional[float] = None
    invalidacao: Optional[str] = None

    motivos: List[str] = field(default_factory=list)
    riscos: List[str] = field(default_factory=list)

    market_referencia: Optional[Dict] = None
    prediction_referencia: Optional[Dict] = None
    vision_referencia: Optional[Dict] = None
    news_referencia: Optional[Dict] = None

    metadados: Dict = field(default_factory=dict)
'''

CONTRACTS_INIT = '''# core/contracts/__init__.py
from .market_context import MarketContext, AtivoSnapshot
from .prediction_context import PredictionContext
from .news_context import NewsContext
from .vision_context import VisionContext
from .decision_context import DecisionContext

__all__ = [
    "MarketContext",
    "AtivoSnapshot",
    "PredictionContext",
    "NewsContext",
    "VisionContext",
    "DecisionContext",
]
'''

SERVICE_MARKET = '''# core/services/market_service.py
"""
MarketService: constrói o MarketContext a partir dos JSONs.
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from ..contracts import MarketContext, AtivoSnapshot


class MarketService:
    """
    Serviço que lê os dados brutos (JSONs) e monta o MarketContext.
    """

    def __init__(self, coletas_dir: Optional[Path] = None):
        if coletas_dir is None:
            # Assume que a pasta Coletas está na raiz do projeto
            self.coletas_dir = Path(__file__).resolve().parent.parent.parent / "Coletas"
        else:
            self.coletas_dir = coletas_dir

        self._ativos_data = None
        self._metricas_data = None
        self._tendencias_data = None

    def _carregar_json(self, nome: str) -> Dict[str, Any]:
        caminho = self.coletas_dir / nome
        if not caminho.exists():
            return {}
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def _carregar_dados(self):
        if self._ativos_data is None:
            self._ativos_data = self._carregar_json("DadosAtivosUnificados.json")
        if self._metricas_data is None:
            self._metricas_data = self._carregar_json("Metricas_Calculadas.json")
        if self._tendencias_data is None:
            self._tendencias_data = self._carregar_json("Analise_Tendencias.json")

    def _snapshot_from_dict(self, ativo_dict: Dict) -> AtivoSnapshot:
        if not ativo_dict:
            return AtivoSnapshot(preco=0.0, variacao_pct=0.0)
        return AtivoSnapshot(
            preco=float(ativo_dict.get("preco", 0.0)),
            variacao_pct=float(ativo_dict.get("variacao_pct", 0.0)),
            high=ativo_dict.get("high"),
            low=ativo_dict.get("low"),
            volume=ativo_dict.get("volume"),
        )

    def build(self) -> Optional[MarketContext]:
        """
        Constrói e retorna o MarketContext.
        Retorna None se não for possível ler os dados.
        """
        self._carregar_dados()

        if not self._ativos_data:
            print("❌ MarketService: DadosAtivosUnificados.json não encontrado.")
            return None

        ativos = self._ativos_data.get("ativos", {})

        # Função auxiliar para pegar um ativo
        def get_ativo(nome):
            return ativos.get(nome, {})

        # Construir snapshots
        win_fut = self._snapshot_from_dict(get_ativo("WIN_FUT"))
        wdo_fut = self._snapshot_from_dict(get_ativo("WDO_FUT"))
        sp500 = self._snapshot_from_dict(get_ativo("SP500_FUT"))
        nasdaq = self._snapshot_from_dict(get_ativo("NASDAQ_FUT"))
        vix = self._snapshot_from_dict(get_ativo("VIX"))
        dxy = self._snapshot_from_dict(get_ativo("DXY"))
        ewz = self._snapshot_from_dict(get_ativo("EWZ"))
        iron_ore = self._snapshot_from_dict(get_ativo("IRON_ORE"))
        crude_oil = self._snapshot_from_dict(get_ativo("CRUDE_OIL"))
        gold = self._snapshot_from_dict(get_ativo("GOLD"))

        win_ajuste = float(get_ativo("WIN_AJUSTE").get("preco", 0.0))
        wdo_ajuste = float(get_ativo("WDO_AJUSTE").get("preco", 0.0))
        ptax = float(get_ativo("USD_PTAX").get("preco", 0.0))

        # ADRs
        adrs = {}
        for ticker in ["VALE_ADR", "PETR_ADR", "ITUB_ADR", "BBAS_ADR", "BBD_ADR", "B3_ADR"]:
            data = get_ativo(ticker)
            if data:
                adrs[ticker] = self._snapshot_from_dict(data)

        # Métricas
        metricas = self._metricas_data
        indicadores = metricas.get("indicadores_compostos", {})
        cambio = metricas.get("cambio_e_arbitragem", {})
        curva = metricas.get("curva_juros_b3", {})

        # Tendências
        tendencias = self._tendencias_data
        tendencia_win = None
        tendencia_win_padrao = None
        if tendencias:
            win_tend = tendencias.get("WIN_FUT") or tendencias.get("BMFBOVESPA:WIN1!")
            if win_tend:
                tendencia_win = win_tend.get("intervalo_5_para_0", {}).get("tendencia")
                tendencia_win_padrao = win_tend.get("padrao_comportamento")

        return MarketContext(
            timestamp=datetime.now(),
            win_fut=win_fut,
            wdo_fut=wdo_fut,
            win_ajuste=win_ajuste,
            wdo_ajuste=wdo_ajuste,
            ptax=ptax,
            sp500=sp500,
            nasdaq=nasdaq,
            vix=vix,
            dxy=dxy,
            ewz=ewz,
            iron_ore=iron_ore,
            crude_oil=crude_oil,
            gold=gold,
            adrs=adrs,
            indicador_mercado_externo=indicadores.get("indicador_mercado_externo"),
            indicador_adrs_brasileiras=indicadores.get("indicador_adrs_brasileiras"),
            spread_wdo_ptax_pontos=cambio.get("spread_wdo_ptax_pontos"),
            inclinacao_di_bps=curva.get("inclinacao_29_27_bps"),
            tendencia_win=tendencia_win,
            tendencia_win_padrao=tendencia_win_padrao,
            metadados={"fonte_ativos": "DadosAtivosUnificados.json",
                       "fonte_metricas": "Metricas_Calculadas.json"}
        )
'''

SERVICE_PREDICTION = '''# core/services/prediction_service.py
"""
PredictionService: integração com o Novo Motor.
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Adiciona a raiz do projeto ao path para importar o Novo Motor
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from NOVO_MOTOR_PREVISAO_ABERTURA.core.motor_previsao import executar_previsao
from ..contracts import PredictionContext


class PredictionService:
    """
    Serviço que invoca o Novo Motor e retorna PredictionContext.
    """

    def get_prediction(self) -> Optional[PredictionContext]:
        try:
            dados = executar_previsao()
            if not dados:
                return None

            # Mapear os campos para o contrato
            return PredictionContext(
                timestamp=datetime.fromisoformat(dados.get("timestamp", datetime.now().isoformat())),
                ativo=dados.get("ativo", "WIN"),
                abertura_projetada=dados.get("abertura_projetada", 0.0),
                faixa_provavel_inferior=dados["faixa_provavel"][0] if dados.get("faixa_provavel") else 0.0,
                faixa_provavel_superior=dados["faixa_provavel"][1] if dados.get("faixa_provavel") else 0.0,
                gap_pontos=dados.get("gap", {}).get("pontos", 0.0),
                gap_percentual=dados.get("gap", {}).get("percentual", 0.0),
                gap_intensidade=dados.get("gap", {}).get("intensidade", "N/A"),
                classificacao_gap=dados.get("gap", {}).get("classificacao", "N/A"),
                direcao_prevista=dados.get("direcao_prevista", "NEUTRO"),
                score=dados.get("score", {}).get("valor", 0.0),
                score_classificacao=dados.get("score", {}).get("classificacao", "N/A"),
                score_detalhes=dados.get("score", {}).get("detalhes", {}),
                analise_ajuste=dados.get("analise_ajuste", {}),
                cenario_principal=dados.get("cenario_principal", {}),
                cenario_alternativo=dados.get("cenario_alternativo", {}),
                metadados=dados.get("metadados", {})
            )
        except Exception as e:
            print(f"❌ PredictionService: erro ao obter previsão: {e}")
            return None
'''

SERVICE_NEWS = '''# core/services/news_service.py
"""
NewsService: constrói NewsContext a partir de Noticias_Impacto_Dia.json.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from ..contracts import NewsContext


class NewsService:
    def __init__(self, coletas_dir: Optional[Path] = None):
        if coletas_dir is None:
            self.coletas_dir = Path(__file__).resolve().parent.parent.parent / "Coletas"
        else:
            self.coletas_dir = coletas_dir

    def _carregar_json(self, nome: str) -> Dict[str, Any]:
        caminho = self.coletas_dir / nome
        if not caminho.exists():
            return {}
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def get_news(self) -> Optional[NewsContext]:
        dados = self._carregar_json("Noticias_Impacto_Dia.json")
        if not dados:
            return None

        resumo = dados.get("resumo", {})
        alertas = dados.get("alertas", {})

        return NewsContext(
            timestamp=datetime.now(),
            impacto_total=resumo.get("impacto_total", 0),
            classificacao_risco=resumo.get("classificacao", "BAIXO"),
            tem_3_estrelas_brasil_0900=alertas.get("tem_3_estrelas_brasil_0900", False),
            tem_3_estrelas_outros_horarios=alertas.get("tem_3_estrelas_outros_horarios", False),
            tem_multiplas_2_estrelas_mesmo_horario=alertas.get("tem_multiplas_2_estrelas_mesmo_horario", False),
            risco_abertura_win=alertas.get("risco_abertura_WIN", False),
            eventos_3_estrelas=alertas.get("noticias_3_estrelas_outros_horarios", []),
            horarios_multiplas_2_estrelas=alertas.get("horarios_multiplas_2_estrelas", []),
            metadados={"fonte": "Noticias_Impacto_Dia.json"}
        )
'''

ENGINE_CONFLUENCE = '''# core/engines/confluence_engine.py
"""
ConfluenceEngine: combina os contextos e gera um viés consolidado.
"""
from typing import Dict, Any, Optional
from ..contracts import MarketContext, PredictionContext, NewsContext, VisionContext


class ConfluenceEngine:
    """
    Combina evidências de diferentes fontes e gera um score de confluência.
    """

    def __init__(self, pesos: Optional[Dict[str, float]] = None):
        self.pesos = pesos or {
            "market": 1.0,
            "prediction": 1.5,
            "news": 0.8,
            "vision": 1.2  # futuro
        }

    def _normalizar_direcao(self, direcao: str) -> int:
        if direcao.upper() == "COMPRA":
            return 1
        elif direcao.upper() == "VENDA":
            return -1
        return 0

    def _peso_do_score(self, score: float) -> float:
        if score >= 80:
            return 2.0
        elif score >= 60:
            return 1.5
        elif score >= 40:
            return 1.0
        elif score >= 20:
            return 0.5
        return 0.0

    def processar(
        self,
        market: MarketContext,
        prediction: Optional[PredictionContext] = None,
        news: Optional[NewsContext] = None,
        vision: Optional[VisionContext] = None
    ) -> Dict[str, Any]:
        """
        Retorna um dicionário com:
            - vies: "COMPRA" / "VENDA" / "NEUTRO"
            - confianca: int (0-100)
            - motivos: List[str]
            - riscos: List[str]
        """
        motivos = []
        riscos = []
        votos = {"COMPRA": 0.0, "VENDA": 0.0}
        confianca_total = 0.0
        peso_total = 0.0

        # 1. MarketContext
        if market:
            # Analisa indicadores
            if market.indicador_mercado_externo is not None:
                valor = market.indicador_mercado_externo
                if valor > 0.5:
                    votos["COMPRA"] += 1.0 * self.pesos["market"]
                    motivos.append(f"Mercado Externo: {valor:+.2f}% (COMPRA)")
                elif valor < -0.5:
                    votos["VENDA"] += 1.0 * self.pesos["market"]
                    motivos.append(f"Mercado Externo: {valor:+.2f}% (VENDA)")
                else:
                    motivos.append(f"Mercado Externo: {valor:+.2f}% (NEUTRO)")
                confianca_total += 0.5 * self.pesos["market"]
                peso_total += self.pesos["market"]

            if market.indicador_adrs_brasileiras is not None:
                valor = market.indicador_adrs_brasileiras
                if valor > 0.5:
                    votos["COMPRA"] += 0.8 * self.pesos["market"]
                    motivos.append(f"ADRs Brasileiras: {valor:+.2f}% (COMPRA)")
                elif valor < -0.5:
                    votos["VENDA"] += 0.8 * self.pesos["market"]
                    motivos.append(f"ADRs Brasileiras: {valor:+.2f}% (VENDA)")
                else:
                    motivos.append(f"ADRs Brasileiras: {valor:+.2f}% (NEUTRO)")
                confianca_total += 0.4 * self.pesos["market"]
                peso_total += self.pesos["market"]

            # Tendência
            if market.tendencia_win:
                if market.tendencia_win == "SUBIU":
                    votos["COMPRA"] += 0.6 * self.pesos["market"]
                    motivos.append(f"Tendência WIN: {market.tendencia_win}")
                elif market.tendencia_win == "DESCEU":
                    votos["VENDA"] += 0.6 * self.pesos["market"]
                    motivos.append(f"Tendência WIN: {market.tendencia_win}")
                confianca_total += 0.3 * self.pesos["market"]
                peso_total += self.pesos["market"]

            # Risco (VIX)
            if market.vix and market.vix.variacao_pct:
                if market.vix.variacao_pct > 3.0:
                    riscos.append(f"VIX em alta: {market.vix.variacao_pct:+.2f}%")
                    # Penaliza levemente
                    votos["COMPRA"] -= 0.3
                    votos["VENDA"] -= 0.3

        # 2. PredictionContext
        if prediction:
            peso = self.pesos["prediction"]
            direcao = self._normalizar_direcao(prediction.direcao_prevista)
            if direcao == 1:
                votos["COMPRA"] += 1.0 * peso
                motivos.append(f"Predição: {prediction.direcao_prevista} (score {prediction.score:.1f})")
            elif direcao == -1:
                votos["VENDA"] += 1.0 * peso
                motivos.append(f"Predição: {prediction.direcao_prevista} (score {prediction.score:.1f})")
            else:
                motivos.append(f"Predição: NEUTRO (score {prediction.score:.1f})")
            # Confiança baseada no score
            fator = self._peso_do_score(prediction.score)
            confianca_total += fator * peso
            peso_total += peso

            # GAP intensidade
            if prediction.gap_intensidade in ("FORTE", "EXTREMO"):
                riscos.append(f"GAP {prediction.gap_intensidade} detectado ({prediction.gap_pontos:+.0f} pts)")

        # 3. NewsContext
        if news:
            if news.classificacao_risco in ("EXTREMO", "ALTO"):
                riscos.append(f"Risco de notícias: {news.classificacao_risco}")
                if news.tem_3_estrelas_brasil_0900:
                    riscos.append("Notícia 3★ Brasil 09:00 – alta volatilidade")
                    # Reduz confiança geral
                    confianca_total *= 0.7
            if news.tem_multiplas_2_estrelas_mesmo_horario:
                riscos.append("Múltiplas notícias ⭐⭐ no mesmo horário")

        # 4. (Futuro) VisionContext

        # Decisão final
        total_compra = votos["COMPRA"]
        total_venda = votos["VENDA"]

        if total_compra > total_venda + 0.5:
            vies = "COMPRA"
        elif total_venda > total_compra + 0.5:
            vies = "VENDA"
        else:
            vies = "NEUTRO"

        # Confiança final (0-100)
        if peso_total > 0:
            confianca_bruta = (confianca_total / peso_total) * 100
        else:
            confianca_bruta = 0.0
        confianca = min(100, max(0, int(confianca_bruta)))

        # Ajuste por riscos
        if riscos:
            confianca = max(0, confianca - len(riscos) * 5)

        return {
            "vies": vies,
            "confianca": confianca,
            "motivos": motivos,
            "riscos": riscos,
            "votos": votos
        }
'''

ENGINE_DECISION = '''# core/engines/decision_engine.py
"""
DecisionEngine: transforma a confluência em uma operação concreta.
"""
from typing import Dict, Any, Optional
from ..contracts import MarketContext, DecisionContext


class DecisionEngine:
    """
    Define entrada, stop, alvos e invalidação com base no viés e nos níveis.
    """

    def __init__(self, ativo: str = "WIN"):
        self.ativo = ativo

    def gerar_decisao(
        self,
        confluence_result: Dict[str, Any],
        market: MarketContext
    ) -> DecisionContext:
        """
        Gera um DecisionContext a partir da confluência e do mercado.
        """
        vies = confluence_result["vies"]
        confianca = confluence_result["confianca"]
        motivos = confluence_result["motivos"]
        riscos = confluence_result["riscos"]

        # Se confiança baixa, não define entrada
        if confianca < 40:
            return DecisionContext(
                timestamp=datetime.now(),
                ativo=self.ativo,
                vies_final=vies,
                confianca=confianca,
                entrada=None,
                stop_loss=None,
                alvo_1=None,
                alvo_2=None,
                invalidacao="Confiança insuficiente (< 40%)",
                motivos=motivos,
                riscos=riscos
            )

        # Define níveis baseados no ativo
        if self.ativo == "WIN":
            ajuste = market.win_ajuste
            pp = market.win_fut.preco  # aqui poderíamos usar pivots, mas é um placeholder
            # Simplificação: usar preço atual +/-
            preco_atual = market.win_fut.preco
        else:
            ajuste = market.wdo_ajuste
            preco_atual = market.wdo_fut.preco
            pp = preco_atual

        entrada = None
        stop = None
        alvo1 = None
        alvo2 = None
        invalidacao = None

        if vies == "COMPRA" and confianca >= 60:
            entrada = preco_atual + 50  # placeholder
            stop = preco_atual - 150
            alvo1 = preco_atual + 250
            alvo2 = preco_atual + 500
            invalidacao = f"Fechamento abaixo de {ajuste}"
        elif vies == "VENDA" and confianca >= 60:
            entrada = preco_atual - 50
            stop = preco_atual + 150
            alvo1 = preco_atual - 250
            alvo2 = preco_atual - 500
            invalidacao = f"Fechamento acima de {ajuste}"
        else:
            invalidacao = "Aguardar definição"

        return DecisionContext(
            timestamp=datetime.now(),
            ativo=self.ativo,
            vies_final=vies,
            confianca=confianca,
            entrada=entrada,
            stop_loss=stop,
            alvo_1=alvo1,
            alvo_2=alvo2,
            invalidacao=invalidacao,
            motivos=motivos,
            riscos=riscos,
            market_referencia={"ajuste": ajuste, "preco_atual": preco_atual}
        )
'''

MAIN_PY = '''#!/usr/bin/env python3
# v2/main.py - Entrypoint para testar a nova arquitetura
import sys
from pathlib import Path
from datetime import datetime

# Adiciona a raiz ao path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from v2.core.services.market_service import MarketService
from v2.core.services.prediction_service import PredictionService
from v2.core.services.news_service import NewsService
from v2.core.engines.confluence_engine import ConfluenceEngine
from v2.core.engines.decision_engine import DecisionEngine


def main():
    print("=" * 60)
    print("🚀 ANALISADOR FINANCEIRO V2 - TESTE")
    print("=" * 60)

    # 1. MarketContext
    print("\n📊 Carregando MarketContext...")
    market_service = MarketService()
    market = market_service.build()
    if not market:
        print("❌ Falha ao carregar MarketContext")
        return
    print(f"✅ WIN: {market.win_fut.preco:.0f} ({market.win_fut.variacao_pct:+.2f}%)")
    print(f"✅ VIX: {market.vix.preco:.2f} ({market.vix.variacao_pct:+.2f}%)")

    # 2. PredictionContext
    print("\n🔮 Carregando PredictionContext...")
    pred_service = PredictionService()
    prediction = pred_service.get_prediction()
    if prediction:
        print(f"✅ Direção: {prediction.direcao_prevista} (score: {prediction.score:.1f})")
    else:
        print("⚠️ Prediction não disponível")

    # 3. NewsContext
    print("\n📰 Carregando NewsContext...")
    news_service = NewsService()
    news = news_service.get_news()
    if news:
        print(f"✅ Risco: {news.classificacao_risco} (impacto: {news.impacto_total})")
    else:
        print("⚠️ News não disponível")

    # 4. Confluência
    print("\n⚖️ Executando ConfluenceEngine...")
    engine = ConfluenceEngine()
    resultado = engine.processar(market, prediction, news)
    print(f"✅ Viés: {resultado['vies']} | Confiança: {resultado['confianca']}%")

    # 5. Decisão
    print("\n🎯 Gerando Decisão...")
    dec_engine = DecisionEngine(ativo="WIN")
    decisao = dec_engine.gerar_decisao(resultado, market)
    print(f"✅ Decisão: {decisao.vies_final} (confiança: {decisao.confianca}%)")
    if decisao.entrada:
        print(f"   Entrada: {decisao.entrada:.0f} | Stop: {decisao.stop_loss:.0f} | Alvo1: {decisao.alvo_1:.0f} | Alvo2: {decisao.alvo_2:.0f}")
    else:
        print("   ⏳ Aguardando confirmação")

    print("\n" + "=" * 60)
    print("✅ Teste concluído!")


if __name__ == "__main__":
    main()
'''

DASHBOARD_V2 = '''# v2/pages/dashboard_v2.py
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from v2.core.services.market_service import MarketService
from v2.core.services.prediction_service import PredictionService
from v2.core.services.news_service import NewsService
from v2.core.engines.confluence_engine import ConfluenceEngine
from v2.core.engines.decision_engine import DecisionEngine

st.set_page_config(page_title="Dashboard V2", layout="wide")
st.title("🚀 Dashboard V2 - Analisador Financeiro")

# Carregar dados
market = MarketService().build()
prediction = PredictionService().get_prediction()
news = NewsService().get_news()

if not market:
    st.error("❌ MarketContext não disponível. Execute o pipeline primeiro.")
    st.stop()

# Exibir resumo
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("WIN", f"{market.win_fut.preco:.0f}", f"{market.win_fut.variacao_pct:+.2f}%")
with col2:
    st.metric("WDO", f"{market.wdo_fut.preco:.2f}", f"{market.wdo_fut.variacao_pct:+.2f}%")
with col3:
    st.metric("VIX", f"{market.vix.preco:.2f}", f"{market.vix.variacao_pct:+.2f}%")

# Confluência
engine = ConfluenceEngine()
resultado = engine.processar(market, prediction, news)

col1, col2 = st.columns(2)
with col1:
    st.metric("Viés Consolidado", resultado["vies"], f"Confiança: {resultado['confianca']}%")
with col2:
    if prediction:
        st.metric("Predição (Novo Motor)", prediction.direcao_prevista, f"Score: {prediction.score:.0f}")

# Decisão
dec_engine = DecisionEngine()
decisao = dec_engine.gerar_decisao(resultado, market)

st.subheader("🎯 Decisão Operacional")
col1, col2 = st.columns(2)
with col1:
    st.metric("Decisão", decisao.vies_final)
    st.write(f"**Confiança:** {decisao.confianca}%")
with col2:
    if decisao.entrada:
        st.metric("Entrada", f"{decisao.entrada:.0f}")
        st.metric("Stop", f"{decisao.stop_loss:.0f}", delta="Loss")
        st.metric("Alvo 1", f"{decisao.alvo_1:.0f}", delta="Alvo")
        st.metric("Alvo 2", f"{decisao.alvo_2:.0f}", delta="Alvo")
    else:
        st.info(decisao.invalidacao)

# Motivos e riscos
with st.expander("📋 Motivos e Riscos"):
    st.write("**Motivos:**")
    for m in resultado["motivos"]:
        st.write(f"- {m}")
    st.write("**Riscos:**")
    for r in resultado["riscos"]:
        st.write(f"- {r}")
'''

TEST_CONTRACTS = '''# v2/tests/test_contracts.py
import unittest
from datetime import datetime
from v2.core.contracts import MarketContext, AtivoSnapshot


class TestContracts(unittest.TestCase):
    def test_ativo_snapshot(self):
        snap = AtivoSnapshot(preco=100.5, variacao_pct=1.2)
        self.assertEqual(snap.preco, 100.5)
        self.assertEqual(snap.variacao_pct, 1.2)

    def test_market_context(self):
        snap = AtivoSnapshot(100, 0.5)
        context = MarketContext(
            timestamp=datetime.now(),
            win_fut=snap,
            wdo_fut=snap,
            win_ajuste=100,
            wdo_ajuste=100,
            ptax=5.0,
            sp500=snap,
            nasdaq=snap,
            vix=snap,
            dxy=snap,
            ewz=snap,
            iron_ore=snap,
            crude_oil=snap,
            gold=snap
        )
        self.assertIsNotNone(context.win_fut)


if __name__ == "__main__":
    unittest.main()
'''

# ============================================================
# ESTRUTURA DE DIRETÓRIOS E ARQUIVOS
# ============================================================

ESTRUTURA = {
    "v2/__init__.py": "",
    "v2/main.py": MAIN_PY,
    "v2/core/__init__.py": "",
    "v2/core/contracts/__init__.py": CONTRACTS_INIT,
    "v2/core/contracts/market_context.py": CONTRATO_MARKET,
    "v2/core/contracts/prediction_context.py": CONTRATO_PREDICTION,
    "v2/core/contracts/news_context.py": CONTRATO_NEWS,
    "v2/core/contracts/vision_context.py": CONTRATO_VISION,
    "v2/core/contracts/decision_context.py": CONTRATO_DECISION,
    "v2/core/services/__init__.py": "",
    "v2/core/services/market_service.py": SERVICE_MARKET,
    "v2/core/services/prediction_service.py": SERVICE_PREDICTION,
    "v2/core/services/news_service.py": SERVICE_NEWS,
    "v2/core/engines/__init__.py": "",
    "v2/core/engines/confluence_engine.py": ENGINE_CONFLUENCE,
    "v2/core/engines/decision_engine.py": ENGINE_DECISION,
    "v2/pages/__init__.py": "",
    "v2/pages/dashboard_v2.py": DASHBOARD_V2,
    "v2/tests/__init__.py": "",
    "v2/tests/test_contracts.py": TEST_CONTRACTS,
}


def criar_estrutura():
    base = Path(".")
    for caminho_relativo, conteudo in ESTRUTURA.items():
        caminho = base / caminho_relativo
        # Cria diretório pai se não existir
        caminho.parent.mkdir(parents=True, exist_ok=True)
        # Escreve o arquivo
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        print(f"✅ Criado: {caminho}")

    print("\n🎉 Estrutura V2 criada com sucesso!")
    print("Para testar, execute:")
    print("  python v2/main.py")
    print("  streamlit run v2/pages/dashboard_v2.py")


if __name__ == "__main__":
    criar_estrutura()