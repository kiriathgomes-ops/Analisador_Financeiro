# NOVO_MOTOR_PREVISAO_ABERTURA/dados/schemas.py
from dataclasses import dataclass, field, asdict
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
    # Permite Optional[float] internamente para evitar quebras quando 'close' ou 'change_percent' for None
    adrs: Dict[str, Dict[str, Optional[float]]] = field(default_factory=dict)
    indicador_mercado_externo: Optional[float] = None
    indicador_adrs_brasileiras: Optional[float] = None


@dataclass
class DadosAberturaTeorica:
    """Estimativa de abertura calculada pelo sistema legado."""
    variacao_teorica_pct: float = 0.0
    abertura_teorica_pontos: float = 0.0
    pontos_ajuste_base: float = 0.0
    gap_teorico: float = 0.0  # Calculado posteriormente pelo motor


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
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
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

    def to_dict(self) -> Dict[str, Any]:
        """Converte o objeto e suas sub-estruturas em um dicionário puro."""
        return asdict(self)


# ============================================================
# SAÍDAS DO NOVO MOTOR
# ============================================================

@dataclass
class ClassificacaoGAP:
    """Resultado da análise do GAP."""
    gap_pontos: float = 0.0
    gap_percentual: float = 0.0
    gap_contra_fechamento: float = 0.0
    gap_contra_ajuste: float = 0.0
    intensidade: str = "NEUTRO"  # MICRO, PEQUENO, MODERADO, FORTE, EXTREMO
    classificacao: str = ""       # Descrição textual


@dataclass
class AnaliseAjuste:
    """Posição relativa ao ajuste."""
    distancia_pontos: float = 0.0
    distancia_percentual: float = 0.0
    posicao: str = "NEUTRO"  # "ACIMA", "ABAIXO", "NEUTRO"
    # Para pós-abertura:
    testou_ajuste: bool = False
    rejeitou: bool = False
    aceitou: bool = False
    perdeu: bool = False
    recuperou: bool = False


@dataclass
class Cenario:
    """Cenário principal ou alternativo."""
    nome: str = "INDEFINIDO"  # "CONTINUACAO", "TESTE_REJEICAO", "PERDA_RECUPERACAO"
    descricao: str = ""
    condicao: str = ""
    gatilho_entrada: str = ""
    confirmacao: str = ""
    invalidacao: str = ""
    probabilidade_estimada: float = 0.0


@dataclass
class ScorePrevisao:
    """Score de confiança normalizado (0-100)."""
    valor: float = 0.0
    classificacao: str = "FRACO"  # FRACO, MODERADO, FORTE, MUITO FORTE
    detalhes: Dict[str, float] = field(default_factory=dict)


@dataclass
class ResultadoPrevisao:
    """Saída final do motor."""
    timestamp: datetime = field(default_factory=datetime.now)
    ativo: str = "WIN"
    abertura_projetada: float = 0.0
    faixa_provavel_inferior: float = 0.0
    faixa_provavel_superior: float = 0.0
    gap: ClassificacaoGAP = field(default_factory=ClassificacaoGAP)
    direcao_prevista: str = "NEUTRO"  # "COMPRA", "VENDA", "NEUTRO"
    analise_ajuste: AnaliseAjuste = field(default_factory=AnaliseAjuste)
    cenario_principal: Cenario = field(default_factory=Cenario)
    cenario_alternativo: Cenario = field(default_factory=Cenario)
    score: ScorePrevisao = field(default_factory=ScorePrevisao)
    metadados: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário com tratamento para o campo datetime."""
        dados = asdict(self)
        if isinstance(dados.get("timestamp"), datetime):
            dados["timestamp"] = dados["timestamp"].isoformat()
        return dados