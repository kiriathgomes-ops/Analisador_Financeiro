# NOVO_MOTOR_PREVISAO_ABERTURA/dados/schemas.py
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class DadosAtivo:
    """Representa um ativo com preço e variação."""
    preco: float
    variacao_pct: float


@dataclass
class DadosContexto:
    """Contexto externo (mercados, ADRs, commodities, etc.)."""
    vix: Optional[float] = None
    vix_var: Optional[float] = None
    sp500: Optional[float] = None
    sp500_var: Optional[float] = None
    nasdaq: Optional[float] = None
    nasdaq_var: Optional[float] = None
    ewz: Optional[float] = None
    ewz_var: Optional[float] = None
    dxy: Optional[float] = None
    dxy_var: Optional[float] = None
    iron_ore: Optional[float] = None
    iron_var: Optional[float] = None
    crude_oil: Optional[float] = None
    crude_var: Optional[float] = None
    adrs: Dict[str, Dict[str, float]] = field(default_factory=dict)
    indicador_mercado_externo: Optional[float] = None
    indicador_adrs_brasileiras: Optional[float] = None


@dataclass
class DadosAberturaTeorica:
    """Estimativa de abertura calculada pelo sistema legado."""
    variacao_teorica_pct: float
    abertura_teorica_pontos: float
    pontos_ajuste_base: float
    gap_teorico: float = 0.0  # calculado posteriormente


@dataclass
class DadosPivot:
    pp: float = 0.0
    r1: float = 0.0
    r2: float = 0.0
    s1: float = 0.0
    s2: float = 0.0


@dataclass
class DadosTendencia:
    """Tendência de 15min (padrão, variação, direção)."""
    padrao: str = "N/A"
    variacao_pct: float = 0.0
    tendencia: str = "N/A"


@dataclass
class DadosNoticias:
    """Alertas de notícias de alto impacto."""
    tem_3_estrelas_brasil_0900: bool = False
    tem_3_estrelas_outros: bool = False
    tem_multiplas_2_estrelas: bool = False
    classificacao_impacto: str = "BAIXO"
    risco_abertura_win: bool = False


@dataclass
class DadosEntrada:
    """Todos os dados necessários para a previsão."""
    timestamp: str
    fechamento_anterior_win: Optional[float] = None
    ajuste_win: Optional[float] = None
    preco_atual_win: Optional[float] = None
    maxima_pre_abertura: Optional[float] = None
    minima_pre_abertura: Optional[float] = None
    abertura_teorica: Optional[DadosAberturaTeorica] = None
    pivot_win: Optional[DadosPivot] = None
    contexto: Optional[DadosContexto] = None
    tendencia_win: Optional[DadosTendencia] = None
    noticias: Optional[DadosNoticias] = None
    core_win_vies: Optional[str] = None
    core_win_score: Optional[float] = None


# ============================================================
# SAÍDAS DO NOVO MOTOR
# ============================================================

@dataclass
class ClassificacaoGAP:
    """Resultado da análise do GAP."""
    gap_pontos: float
    gap_percentual: float
    gap_contra_fechamento: float
    gap_contra_ajuste: float
    intensidade: str  # MICRO, PEQUENO, MODERADO, FORTE, EXTREMO
    classificacao: str  # descrição textual


@dataclass
class AnaliseAjuste:
    """Posição relativa ao ajuste."""
    distancia_pontos: float
    distancia_percentual: float
    posicao: str  # "ACIMA", "ABAIXO", "NEUTRO"
    # Para pós-abertura:
    testou_ajuste: bool = False
    rejeitou: bool = False
    aceitou: bool = False
    perdeu: bool = False
    recuperou: bool = False


@dataclass
class Cenario:
    """Cenário principal ou alternativo."""
    nome: str  # "CONTINUACAO", "TESTE_REJEICAO", "PERDA_RECUPERACAO"
    descricao: str
    condicao: str
    gatilho_entrada: str
    confirmacao: str
    invalidacao: str
    probabilidade_estimada: float = 0.0  # futuramente calibrada


@dataclass
class ScorePrevisao:
    """Score de confiança normalizado (0-100)."""
    valor: float
    classificacao: str  # FRACO, MODERADO, FORTE, MUITO FORTE
    detalhes: Dict[str, float] = field(default_factory=dict)


@dataclass
class ResultadoPrevisao:
    """Saída final do motor."""
    timestamp: datetime
    ativo: str  # "WIN"
    abertura_projetada: float
    faixa_provavel_inferior: float
    faixa_provavel_superior: float
    gap: ClassificacaoGAP
    direcao_prevista: str  # "COMPRA", "VENDA", "NEUTRO"
    analise_ajuste: AnaliseAjuste
    cenario_principal: Cenario
    cenario_alternativo: Cenario
    score: ScorePrevisao
    metadados: Dict[str, Any] = field(default_factory=dict)