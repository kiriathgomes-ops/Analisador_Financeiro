# Dump completo - NOVO_MOTOR_PREVISAO_ABERTURA

Gerado em: 2026-09-29 08:09:22
Total de arquivos: 11

## Arvore

```
NOVO_MOTOR_PREVISAO_ABERTURA
|-- __init__.py
|-- config/__init__.py
|-- core/__init__.py
|-- core/motor_ajuste.py
|-- core/motor_cenarios.py
|-- core/motor_gap.py
|-- core/motor_previsao.py
|-- core/motor_score.py
|-- dados/__init__.py
|-- dados/coletor_dados.py
`-- dados/schemas.py
```

## Conteudo dos arquivos

### `NOVO_MOTOR_PREVISAO_ABERTURA/__init__.py`

```python
# NOVO_MOTOR_PREVISAO_ABERTURA/__init__.py
"""
Novo Motor de Previsão de Abertura - Independente do sistema legado.
"""
```

### `NOVO_MOTOR_PREVISAO_ABERTURA/config/__init__.py`

```python
# NOVO_MOTOR_PREVISAO_ABERTURA/config/__init__.py
```

### `NOVO_MOTOR_PREVISAO_ABERTURA/core/__init__.py`

```python
# NOVO_MOTOR_PREVISAO_ABERTURA/core/__init__.py
```

### `NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_ajuste.py`

```python
# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_ajuste.py
from typing import Dict, Any
from ..dados.schemas import AnaliseAjuste


# Tolerância padrão para considerar o preço "neutro" em relação ao ajuste.
# O WIN tem tick de 5 pontos; 50 pontos representa 10 ticks de margem.
# Valores menores (ex: 0.5) classificam ruído como sinal.
TOLERANCIA_AJUSTE_PADRAO = 50.0


def analisar_ajuste(
    preco: float,
    ajuste: float,
    tolerancia: float = TOLERANCIA_AJUSTE_PADRAO,
) -> AnaliseAjuste:
    """
    Analisa a posição do preço em relação ao ajuste.

    Args:
        preco: preço atual ou projetado
        ajuste: valor do ajuste oficial
        tolerancia: pontos para considerar como "NEUTRO"
                    (default: 50 pts — calibrado para o WIN)

    Returns:
        AnaliseAjuste com distância e posição
    """
    if ajuste == 0:
        return AnaliseAjuste(
            distancia_pontos=0.0,
            distancia_percentual=0.0,
            posicao="NEUTRO",
        )

    distancia = preco - ajuste
    percentual = (distancia / ajuste) * 100

    if distancia > tolerancia:
        posicao = "ACIMA"
    elif distancia < -tolerancia:
        posicao = "ABAIXO"
    else:
        posicao = "NEUTRO"

    return AnaliseAjuste(
        distancia_pontos=distancia,
        distancia_percentual=round(percentual, 4),
        posicao=posicao,
    )


def atualizar_analise_pos_abertura(
    ajuste: AnaliseAjuste,
    preco_atual: float,
    ajuste_ref: float,
    preco_anterior: float = None,
) -> AnaliseAjuste:
    """
    Atualiza a análise após a abertura real, verificando se houve teste,
    rejeição, aceitação, perda ou recuperação.
    """
    nova = analisar_ajuste(preco_atual, ajuste_ref)

    if preco_anterior is None:
        return nova

    # Teste: cruzou o ajuste
    if (preco_anterior > ajuste_ref and preco_atual <= ajuste_ref) or \
       (preco_anterior < ajuste_ref and preco_atual >= ajuste_ref):
        nova.testou_ajuste = True

        if (preco_atual > ajuste_ref and preco_anterior > ajuste_ref) or \
           (preco_atual < ajuste_ref and preco_anterior < ajuste_ref):
            nova.rejeitou = True
        else:
            nova.aceitou = True

    # Perda
    if preco_anterior > ajuste_ref + TOLERANCIA_AJUSTE_PADRAO and \
       preco_atual < ajuste_ref - TOLERANCIA_AJUSTE_PADRAO:
        nova.perdeu = True

    # Recuperação
    if preco_anterior < ajuste_ref - TOLERANCIA_AJUSTE_PADRAO and \
       preco_atual > ajuste_ref + TOLERANCIA_AJUSTE_PADRAO:
        nova.recuperou = True

    return nova
```

### `NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_cenarios.py`

```python
# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_cenarios.py
from typing import Tuple, Dict
from ..dados.schemas import Cenario, ClassificacaoGAP, AnaliseAjuste


def _calcular_probabilidades(
    gap: ClassificacaoGAP, ajuste: AnaliseAjuste
) -> Dict[str, float]:
    """
    Calcula probabilidades (0-100) dos 5 comportamentos possíveis, com base
    na distância do preço até o ajuste e na intensidade do gap.

    Retorna dict normalizado (soma ~100):
      continuar | rejeitar | recuperar | retornar | falso
    """
    dist = abs(ajuste.distancia_pontos or 0.0)

    # Base por proximidade ao ajuste
    if dist <= 50:
        base = {"continuar": 15, "rejeitar": 30, "recuperar": 20, "retornar": 25, "falso": 10}
    elif dist <= 150:
        base = {"continuar": 30, "rejeitar": 25, "recuperar": 15, "retornar": 15, "falso": 15}
    elif dist <= 300:
        base = {"continuar": 35, "rejeitar": 15, "recuperar": 10, "retornar": 15, "falso": 25}
    else:
        base = {"continuar": 25, "rejeitar": 10, "recuperar": 10, "retornar": 20, "falso": 35}

    # Ajuste por intensidade do gap
    if gap.intensidade in ("FORTE", "EXTREMO"):
        base["continuar"] += 5
        base["retornar"] = max(5, base["retornar"] - 5)
        base["falso"] = max(5, base["falso"] - 3)

    # Normaliza
    total = sum(base.values()) or 1
    return {k: round(v / total * 100, 1) for k, v in base.items()}


def gerar_cenarios(
    gap: ClassificacaoGAP, ajuste: AnaliseAjuste
) -> Tuple[Cenario, Cenario]:
    """
    Gera cenários principal e alternativo com probabilidades numéricas.

    A probabilidade_estimada é preenchida com o valor do comportamento
    dominante (principal) ou do alternativo.
    """
    probs = _calcular_probabilidades(gap, ajuste)

    # ---- Caso 1: Gap extremo ou forte ----
    if gap.intensidade in ("EXTREMO", "FORTE"):
        if gap.gap_pontos > 0:
            principal = Cenario(
                nome="CONTINUACAO_COMPRA",
                descricao="GAP positivo forte/extremo. Tendência compradora predominante.",
                condicao="Abertura com gap significativo acima do ajuste.",
                gatilho_entrada="Pullback com rejeição ou rompimento de topo.",
                confirmacao="Fechamento acima do ajuste após 15min.",
                invalidacao="Fechamento abaixo do ajuste ou perda total do gap.",
                probabilidade_estimada=probs["continuar"],
            )
            alternativo = Cenario(
                nome="TESTE_REJEICAO",
                descricao="Preço testa o gap e rejeita, mantendo viés comprador.",
                condicao="Retorno à zona do gap com candle de rejeição.",
                gatilho_entrada="Rejeição confirmada no nível do gap.",
                confirmacao="Fechamento acima do gap.",
                invalidacao="Perda total do gap com aceitação abaixo.",
                probabilidade_estimada=probs["rejeitar"],
            )
        else:
            principal = Cenario(
                nome="CONTINUACAO_VENDA",
                descricao="GAP negativo forte/extremo. Tendência vendedora predominante.",
                condicao="Abertura com gap significativo abaixo do ajuste.",
                gatilho_entrada="Pullback com rejeição ou rompimento de fundo.",
                confirmacao="Fechamento abaixo do ajuste após 15min.",
                invalidacao="Fechamento acima do ajuste ou recuperação total do gap.",
                probabilidade_estimada=probs["continuar"],
            )
            alternativo = Cenario(
                nome="RECUPERACAO",
                descricao="Preço testa o gap e o recupera, invertendo para compra.",
                condicao="Retorno ao gap com rompimento e aceitação acima.",
                gatilho_entrada="Romper o gap com volume.",
                confirmacao="Fechamento acima do gap.",
                invalidacao="Rejeição no gap e continuação da queda.",
                probabilidade_estimada=probs["recuperar"],
            )
        return principal, alternativo

    # ---- Caso 2: Gap moderado / pequeno → posição vs ajuste ----
    if ajuste.posicao == "ACIMA":
        principal = Cenario(
            nome="CONTINUACAO",
            descricao="Preço acima do ajuste. Viés comprador.",
            condicao="Abertura acima do ajuste e manutenção.",
            gatilho_entrada="Pullback com rejeição ou rompimento de topo.",
            confirmacao="Fechamento acima do ajuste após 15min.",
            invalidacao="Perda do ajuste com aceitação abaixo.",
            probabilidade_estimada=probs["continuar"],
        )
        alternativo = Cenario(
            nome="TESTE_REJEICAO",
            descricao="Testa o ajuste e rejeita, reforçando compra.",
            condicao="Retorno ao ajuste com candle de rejeição.",
            gatilho_entrada="Rejeição confirmada no ajuste.",
            confirmacao="Fechamento acima do ajuste.",
            invalidacao="Perda do ajuste com aceitação abaixo.",
            probabilidade_estimada=probs["rejeitar"],
        )
    elif ajuste.posicao == "ABAIXO":
        principal = Cenario(
            nome="CONTINUACAO",
            descricao="Preço abaixo do ajuste. Viés vendedor.",
            condicao="Abertura abaixo do ajuste e manutenção.",
            gatilho_entrada="Pullback com rejeição ou rompimento de fundo.",
            confirmacao="Fechamento abaixo do ajuste após 15min.",
            invalidacao="Recuperação do ajuste com aceitação acima.",
            probabilidade_estimada=probs["continuar"],
        )
        alternativo = Cenario(
            nome="RECUPERACAO",
            descricao="Testa o ajuste e o recupera, invertendo para compra.",
            condicao="Retorno ao ajuste com rompimento e aceitação acima.",
            gatilho_entrada="Romper o ajuste com volume.",
            confirmacao="Fechamento acima do ajuste.",
            invalidacao="Rejeição no ajuste e volta para baixo.",
            probabilidade_estimada=probs["recuperar"],
        )
    else:  # NEUTRO
        principal = Cenario(
            nome="NEUTRO",
            descricao="Preço próximo ao ajuste, aguardar definição.",
            condicao="Preço dentro da faixa de tolerância (±50 pts).",
            gatilho_entrada="Aguardar rompimento de topo ou fundo.",
            confirmacao="Fechamento fora da faixa com volume.",
            invalidacao="Permanência na faixa por mais de 15min.",
            probabilidade_estimada=probs["retornar"],
        )
        alternativo = principal

    return principal, alternativo
```

### `NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_gap.py`

```python
# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_gap.py
#
# ATUALIZAÇÃO 18/09/2026:
#   Limiares de classificação migraram de pontos absolutos para % do
#   preço de referência. Ver LIMIARES_PCT para detalhes da calibração.
from typing import Dict, Any
from ..dados.schemas import ClassificacaoGAP

# ============================================================
# Limiares para classificação de GAP (% do preço de referência)
# ============================================================
# Antes eram pontos absolutos (20/50/100/200). Problema: não escalavam
# com o preço do WIN (que já esteve em 100k e hoje está em 188k).
# Um gap de 200 pts era 0.2% em 2026, mas seria 0.4% em 2020.
#
# Agora usamos % do preço de referência (fechamento anterior). Isso
# escala automaticamente com o tempo e com a inflação do índice.
#
# Valores calibrados com base no ATR M5 atual (~120 pts = 0.06%) e na
# experiência operacional do WIN:
#   MICRO    → até 0.05%    (~94 pts hoje)    — ruído de leilão
#   PEQUENO  → 0.05-0.15%   (~94-283 pts)     — gap normal
#   MODERADO → 0.15-0.30%   (~283-566 pts)    — gap relevante
#   FORTE    → 0.30-0.60%   (~566-1132 pts)   — gap de evento
#   EXTREMO  → >0.60%       (>1132 pts)       — gap histórico (raro)
# ============================================================
LIMIARES_PCT = {
    "MICRO": 0.05,
    "PEQUENO": 0.15,
    "MODERADO": 0.30,
    "FORTE": 0.60,
    "EXTREMO": 999.0
}

def classificar_gap(
    preco_abertura: float,
    referencia_fechamento: float,
    referencia_ajuste: float = None
) -> ClassificacaoGAP:
    """
    Classifica o GAP com base no preço de abertura projetado/real.
    
    Args:
        preco_abertura: preço de abertura (teórico ou real)
        referencia_fechamento: fechamento anterior (ou ajuste)
        referencia_ajuste: ajuste oficial (opcional, para gap contra ajuste)
    
    Returns:
        ClassificacaoGAP com todos os campos preenchidos
    """
    if referencia_fechamento == 0:
        referencia_fechamento = 1e-6  # evitar divisão por zero
    
    gap_pontos = preco_abertura - referencia_fechamento
    gap_percentual = (gap_pontos / referencia_fechamento) * 100
    
    # Gap contra ajuste (se fornecido)
    gap_ajuste = None
    if referencia_ajuste is not None:
        gap_ajuste = preco_abertura - referencia_ajuste
    
    # Classificação por % (não mais por pontos absolutos — ver LIMIARES_PCT)
    abs_gap_pct = abs(gap_percentual)
    
    if abs_gap_pct < LIMIARES_PCT["MICRO"]:
        intensidade = "MICRO"
    elif abs_gap_pct < LIMIARES_PCT["PEQUENO"]:
        intensidade = "PEQUENO"
    elif abs_gap_pct < LIMIARES_PCT["MODERADO"]:
        intensidade = "MODERADO"
    elif abs_gap_pct < LIMIARES_PCT["FORTE"]:
        intensidade = "FORTE"
    else:
        intensidade = "EXTREMO"
    
    # Log enxuto (facilita debug e ver o limiar aplicado)
    print(f"[GAP] {gap_pontos:+.0f} pts ({gap_percentual:+.4f}%) -> {intensidade}")
    
    return ClassificacaoGAP(
        gap_pontos=gap_pontos,
        gap_percentual=round(gap_percentual, 4),
        gap_contra_fechamento=gap_pontos,
        gap_contra_ajuste=gap_ajuste if gap_ajuste is not None else 0.0,
        intensidade=intensidade,
        classificacao=f"GAP {intensidade}"
    )
```

### `NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_previsao.py`

```python
# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_previsao.py
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

from config import JANELA_LEILAO_INICIO, JANELA_LEILAO_FIM

from ..dados.coletor_dados import coletar_dados_entrada
from ..dados.schemas import (
    DadosEntrada, ResultadoPrevisao, ClassificacaoGAP,
    AnaliseAjuste, Cenario, ScorePrevisao,
)
from .motor_gap import classificar_gap
from .motor_ajuste import analisar_ajuste
from .motor_cenarios import gerar_cenarios
from .motor_score import calcular_score


MAX_GAP_REALISTA = 1000.0
MARGEM_FAIXA_PADRAO = 100.0


class PrevisaoAberturaOrquestrador:
    def __init__(self):
        self.entrada: Optional[DadosEntrada] = None
        self.resultado: Optional[ResultadoPrevisao] = None

    def carregar_dados(self) -> bool:
        self.entrada = coletar_dados_entrada()
        return self.entrada is not None

    def executar_previsao(self) -> Optional[ResultadoPrevisao]:
        if not self.entrada:
            if not self.carregar_dados():
                return None

        abertura_teorica = float(
            (self.entrada.abertura_teorica.abertura_teorica_pontos if self.entrada.abertura_teorica else 0.0)
            or 0.0
        )
        ajuste = float(self.entrada.ajuste_win or 0.0)

        fechamento_anterior = self.entrada.fechamento_anterior_win
        if fechamento_anterior is None or float(fechamento_anterior or 0.0) <= 0:
            fechamento_anterior = ajuste if ajuste > 0 else abertura_teorica

        preco_atual = self.entrada.preco_atual_win
        if preco_atual is None or float(preco_atual or 0.0) <= 0:
            preco_atual = abertura_teorica

        # 1. GAP
        gap = classificar_gap(abertura_teorica, fechamento_anterior, ajuste)

        # 2. Análise de ajuste
        preco_para_ajuste = preco_atual if preco_atual else abertura_teorica
        ajuste_analise = analisar_ajuste(preco_para_ajuste, ajuste)

        # 3. Cenários
        cenario_principal, cenario_alternativo = gerar_cenarios(gap, ajuste_analise)

        # 4. Score
        score = calcular_score(
            contexto=self.entrada.contexto,
            tendencia=self.entrada.tendencia_win,
            noticias=self.entrada.noticias,
            gap=gap,
            ajuste=ajuste_analise,
        )

        # 5. Faixa provável
        faixa_inf, faixa_sup = self._calcular_faixa(abertura_teorica)

        # 6. Direção (baseada no gap + ajuste)
        direcao = self._determinar_direcao(gap, ajuste_analise, score.direcao)

        # 7. Divergência entre direcao_prevista e score.direcao
        div_flag, div_msg = self._calcular_divergencia(direcao, score.direcao)

        # 8. Legado
        legado = None
        if self.entrada.core_win_vies:
            legado = {
                "vies": self.entrada.core_win_vies,
                "score": self.entrada.core_win_score,
            }

        self.resultado = ResultadoPrevisao(
            timestamp=datetime.now(),
            ativo="WIN",
            abertura_projetada=abertura_teorica,
            faixa_provavel_inferior=faixa_inf,
            faixa_provavel_superior=faixa_sup,
            gap=gap,
            direcao_prevista=direcao,
            analise_ajuste=ajuste_analise,
            cenario_principal=cenario_principal,
            cenario_alternativo=cenario_alternativo,
            score=score,
            metadados={
                "fonte_dados": "Coletas/",
                "versao_motor": "1.6.0",
                "ajuste_utilizado": ajuste,
                "fechamento_anterior": fechamento_anterior,
                "preco_atual_utilizado": preco_para_ajuste,
                "max_pre_abertura": self.entrada.maxima_pre_abertura,
                "min_pre_abertura": self.entrada.minima_pre_abertura,
                "legado": legado,
                "abertura_leilao_real": self.entrada.abertura_leilao_real,
                "abertura_leilao_timestamp": self.entrada.abertura_leilao_timestamp,
                "abertura_teorica_calculada": self.entrada.abertura_teorica_calculada,
                "fonte_abertura": self.entrada.fonte_abertura,
                "divergencia_direcao": div_flag,
                "divergencia_detalhes": div_msg,
            },
        )
        return self.resultado

    def _calcular_faixa(self, abertura: float):
        return (
            abertura - MARGEM_FAIXA_PADRAO,
            abertura + MARGEM_FAIXA_PADRAO,
        )

    def _determinar_direcao(
        self, gap: ClassificacaoGAP, ajuste: AnaliseAjuste, score_direcao: str
    ) -> str:
        agora = datetime.now().time()
        fora_do_leilao = not (JANELA_LEILAO_INICIO <= agora <= JANELA_LEILAO_FIM)
        if fora_do_leilao:
            # Fora do leilao o gap de abertura nao opina mais.
            # NOVO_MOTOR passa a ser 100% score-driven.
            return score_direcao

        if abs(gap.gap_pontos) > MAX_GAP_REALISTA:
            return "NEUTRO"

        if gap.intensidade in ["EXTREMO", "FORTE"]:
            return "COMPRA" if gap.gap_pontos > 0 else "VENDA"
        if gap.gap_pontos > 50 and ajuste.posicao == "ACIMA":
            return "COMPRA"
        if gap.gap_pontos < -50 and ajuste.posicao == "ABAIXO":
            return "VENDA"
        if gap.gap_pontos > 100:
            return "COMPRA"
        if gap.gap_pontos < -100:
            return "VENDA"
        return "NEUTRO"

    def _calcular_divergencia(
        self, dir_prevista: str, dir_score: str
    ) -> Tuple[bool, str]:
        """
        Compara direção do gap-based com direção do score.

        Retorna (flag, mensagem):
          - flag: True se há divergência
          - mensagem: texto legível

        Casos:
          - Ambas iguais        → (False, "alinhadas")
          - Ambas NEUTRO        → (False, "ambas neutras")
          - Opostas             → (True, "divergência forte")
          - Uma neutra, outra não → (True, "divergência parcial")
        """
        if dir_prevista == dir_score:
            if dir_prevista == "NEUTRO":
                return False, "Ambas as direções neutras"
            return False, f"Ambas as direções alinhadas em {dir_prevista}"

        if dir_prevista == "NEUTRO" or dir_score == "NEUTRO":
            return True, (
                f"Divergência parcial: direção do gap é {dir_prevista}, "
                f"mas o score consolidado é {dir_score} (um dos dois é neutro)"
            )

        return True, (
            f"⚠️ DIVERGÊNCIA FORTE: direção do gap é {dir_prevista}, "
            f"mas o score consolidado aponta {dir_score} (opostas)"
        )

    def obter_resultado_json(self) -> Dict[str, Any]:
        if not self.resultado:
            return {"erro": "Nenhum resultado disponível"}

        ajuste_analise = self.resultado.analise_ajuste
        ajuste_dict = {
            "distancia_pontos": ajuste_analise.distancia_pontos,
            "distancia_percentual": ajuste_analise.distancia_percentual,
            "posicao": ajuste_analise.posicao,
            "testou_ajuste": ajuste_analise.testou_ajuste,
            "rejeitou": ajuste_analise.rejeitou,
            "aceitou": ajuste_analise.aceitou,
            "perdeu": ajuste_analise.perdeu,
            "recuperou": ajuste_analise.recuperou,
        }

        metadados = dict(self.resultado.metadados or {})
        pre_abertura = {
            "maxima": metadados.pop("max_pre_abertura", None),
            "minima": metadados.pop("min_pre_abertura", None),
            "preco_atual": metadados.pop("preco_atual_utilizado", None),
        }
        legado = metadados.pop("legado", None)

        abertura_leilao_real = metadados.pop("abertura_leilao_real", None)
        abertura_leilao_timestamp = metadados.pop("abertura_leilao_timestamp", None)
        abertura_teorica_calculada = metadados.pop("abertura_teorica_calculada", None)
        fonte_abertura = metadados.pop("fonte_abertura", "DESCONHECIDA")
        divergencia_direcao = metadados.pop("divergencia_direcao", False)
        divergencia_detalhes = metadados.pop("divergencia_detalhes", "")

        return {
            "timestamp": self.resultado.timestamp.isoformat(),
            "ativo": self.resultado.ativo,
            "abertura_projetada": self.resultado.abertura_projetada,
            "abertura_leilao_real": abertura_leilao_real,
            "abertura_leilao_timestamp": abertura_leilao_timestamp,
            "abertura_teorica_calculada": abertura_teorica_calculada,
            "fonte_abertura": fonte_abertura,
            "faixa_provavel": [
                self.resultado.faixa_provavel_inferior,
                self.resultado.faixa_provavel_superior,
            ],
            "gap": {
                "pontos": self.resultado.gap.gap_pontos,
                "percentual": self.resultado.gap.gap_percentual,
                "intensidade": self.resultado.gap.intensidade,
                "classificacao": self.resultado.gap.classificacao,
            },
            "direcao_prevista": self.resultado.direcao_prevista,
            "divergencia_direcao": divergencia_direcao,
            "divergencia_detalhes": divergencia_detalhes,
            "analise_ajuste": ajuste_dict,
            "cenario_principal": {
                "nome": self.resultado.cenario_principal.nome,
                "descricao": self.resultado.cenario_principal.descricao,
                "gatilho": self.resultado.cenario_principal.gatilho_entrada,
                "confirmacao": self.resultado.cenario_principal.confirmacao,
                "invalidacao": self.resultado.cenario_principal.invalidacao,
                "probabilidade_estimada": self.resultado.cenario_principal.probabilidade_estimada,
            },
            "cenario_alternativo": {
                "nome": self.resultado.cenario_alternativo.nome,
                "descricao": self.resultado.cenario_alternativo.descricao,
                "probabilidade_estimada": self.resultado.cenario_alternativo.probabilidade_estimada,
            },
            "score": {
                "valor": self.resultado.score.valor,
                "direcao": self.resultado.score.direcao,
                "forca": self.resultado.score.forca,
                "classificacao": self.resultado.score.classificacao,
                "detalhes": self.resultado.score.detalhes,
            },
            "pre_abertura": pre_abertura,
            "legado": legado,
            "metadados": metadados,
        }


def executar_previsao() -> Optional[Dict[str, Any]]:
    orquestrador = PrevisaoAberturaOrquestrador()
    resultado = orquestrador.executar_previsao()
    if resultado:
        return orquestrador.obter_resultado_json()
    return None
```

### `NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_score.py`

```python
# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_score.py
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from ..dados.schemas import (
    ScorePrevisao,
    DadosContexto,
    DadosTendencia,
    DadosNoticias,
    ClassificacaoGAP,
    AnaliseAjuste,
)


# Carregar configuração de pesos
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
PESOS_PATH = CONFIG_DIR / "pesos.yaml"


def carregar_pesos() -> Dict[str, Any]:
    if not PESOS_PATH.exists():
        return {
            "pesos": {
                "mercado_externo": 0.35,
                "adrs_brasileiras": 0.25,
                "vix": 0.10,
                "tendencia": 0.15,
                "gap_intensidade": 0.10,
                "noticias_impacto": 0.05,
            },
            "score_limiares": {
                "muito_forte": 80,
                "forte": 60,
                "moderado": 40,
                "fraco": 0,
            },
        }
    with open(PESOS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


CONFIG = carregar_pesos()
PESOS = CONFIG.get("pesos", {})
LIMIARES = CONFIG.get("score_limiares", {})


# Limiar de direção: abaixo disso em módulo, considera NEUTRO
LIMIAR_DIRECAO = 10.0


def _classificar_forca(magnitude: float) -> str:
    if magnitude >= LIMIARES.get("muito_forte", 80):
        return "MUITO FORTE"
    if magnitude >= LIMIARES.get("forte", 60):
        return "FORTE"
    if magnitude >= LIMIARES.get("moderado", 40):
        return "MODERADO"
    return "FRACO"


def calcular_score(
    contexto: Optional[DadosContexto],
    tendencia: Optional[DadosTendencia],
    noticias: Optional[DadosNoticias],
    gap: Optional[ClassificacaoGAP] = None,
    ajuste: Optional[AnaliseAjuste] = None,
) -> ScorePrevisao:
    """
    Calcula score direcional (signed interno).
    Retorna ScorePrevisao com valor (magnitude), direcao, forca, classificacao.
    """
    score_signed = 0.0  # positivo = COMPRA, negativo = VENDA
    detalhes: Dict[str, float] = {}

    # 1. Mercado Externo
    if contexto and contexto.indicador_mercado_externo is not None:
        me = contexto.indicador_mercado_externo
        peso = PESOS.get("mercado_externo", 0.35)
        contrib = me * peso * 10
        score_signed += contrib
        detalhes["mercado_externo"] = round(contrib, 2)

    # 2. ADRs Brasileiras
    if contexto and contexto.indicador_adrs_brasileiras is not None:
        adrs = contexto.indicador_adrs_brasileiras
        peso = PESOS.get("adrs_brasileiras", 0.25)
        contrib = adrs * peso * 10
        score_signed += contrib
        detalhes["adrs"] = round(contrib, 2)

    # 3. VIX (invertido: VIX sobe = risco = VENDA)
    if contexto and contexto.vix_var is not None:
        vix_var = contexto.vix_var
        peso = PESOS.get("vix", 0.10)
        contrib = -vix_var * peso * 5
        score_signed += contrib
        detalhes["vix"] = round(contrib, 2)

    # 4. Tendência
    if tendencia and tendencia.tendencia != "N/A":
        peso = PESOS.get("tendencia", 0.15)
        if tendencia.tendencia == "SUBIU":
            contrib = 5 * peso * 10
            score_signed += contrib
            detalhes["tendencia"] = round(contrib, 2)
        elif tendencia.tendencia == "DESCEU":
            contrib = -5 * peso * 10
            score_signed += contrib
            detalhes["tendencia"] = round(contrib, 2)

    # 5. GAP
    if gap:
        peso = PESOS.get("gap_intensidade", 0.10)
        mapa_intensidade = {
            "MICRO": 0,
            "PEQUENO": 2,
            "MODERADO": 5,
            "FORTE": 10,
            "EXTREMO": 15,
        }
        bonus = mapa_intensidade.get(gap.intensidade, 0)
        if gap.gap_pontos > 0:
            contrib = bonus * peso * 5
        else:
            contrib = -bonus * peso * 5
        score_signed += contrib
        detalhes["gap"] = round(contrib, 2)

    # 6. Notícias (sempre penaliza — risco não tem direção)
    if noticias:
        peso = PESOS.get("noticias_impacto", 0.05)
        if noticias.tem_3_estrelas_brasil_0900:
            contrib = -15 * peso * 10
            score_signed += contrib
            detalhes["noticia_3_estrelas"] = round(contrib, 2)
        elif noticias.classificacao_impacto == "EXTREMO":
            contrib = -10 * peso * 10
            score_signed += contrib
            detalhes["noticia_extrema"] = round(contrib, 2)

    # ---- Normalização e classificação ----
    score_signed = max(-100.0, min(100.0, score_signed))

    if score_signed > LIMIAR_DIRECAO:
        direcao = "COMPRA"
    elif score_signed < -LIMIAR_DIRECAO:
        direcao = "VENDA"
    else:
        direcao = "NEUTRO"

    magnitude = abs(score_signed)
    forca = _classificar_forca(magnitude)

    if direcao == "NEUTRO":
        classificacao = "NEUTRO"
    else:
        classificacao = f"{forca} {direcao}"

    return ScorePrevisao(
        valor=round(magnitude, 1),
        direcao=direcao,
        forca=forca,
        classificacao=classificacao,
        detalhes=detalhes,
    )

```

### `NOVO_MOTOR_PREVISAO_ABERTURA/dados/__init__.py`

```python
# NOVO_MOTOR_PREVISAO_ABERTURA/dados/__init__.py
```

### `NOVO_MOTOR_PREVISAO_ABERTURA/dados/coletor_dados.py`

```python
# NOVO_MOTOR_PREVISAO_ABERTURA/dados/coletor_dados.py
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from .schemas import (
    DadosEntrada, DadosAberturaTeorica, DadosPivot,
    DadosContexto, DadosTendencia, DadosNoticias,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
COLETAS_DIR = BASE_DIR / "Coletas"


# Import defensivo do LeilaoService (pode falhar se v2 não estiver no path)
try:
    from v2.core.services.leilao_service import LeilaoService
    LEILAO_SERVICE_DISPONIVEL = True
except ImportError:
    LEILAO_SERVICE_DISPONIVEL = False


def carregar_json(nome: str) -> Dict[str, Any]:
    caminho = COLETAS_DIR / nome
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _extrair_estimativa_win(estimativa: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrai o bloco 'estimativa_abertura.WIN_INDICE' do EstimativaAbertura.json,
    aceitando tanto 'estimativa_abertura' (singular) quanto 'estimativas_abertura' (plural).
    """
    if not isinstance(estimativa, dict):
        return {}

    for chave in ("estimativa_abertura", "estimativas_abertura"):
        bloco = estimativa.get(chave)
        if isinstance(bloco, dict):
            win = bloco.get("WIN_INDICE")
            if isinstance(win, dict) and win:
                return win

    return {}


def _extrair_preco_referencia_win(
    congelado: Dict[str, Any],
    validados: Dict[str, Any],
    mt5: Dict[str, Any],
) -> Optional[float]:
    """
    Busca o preço de referência do WIN (close do congelado).
    Prioridade:
      1. LastTick_Congelado.json → ticks.WIN_LAST_TICK.dados_reais.close
      2. Dados_Validados.json → WIN_FUT.close
      3. Dados_MT5_v2_2.json → ativos.WIN.last
    """
    if isinstance(congelado, dict):
        ticks = congelado.get("ticks") or {}
        win_tick = ticks.get("WIN_LAST_TICK") or {}
        dados = win_tick.get("dados_reais") or {}
        valor = dados.get("close")
        if valor is not None and float(valor) > 0:
            return float(valor)

    if isinstance(validados, dict):
        ativos_validados = validados.get("ativos_validados")
        if isinstance(ativos_validados, list):
            for item in ativos_validados:
                if not isinstance(item, dict):
                    continue
                if item.get("ativo_id") != "WIN_FUT":
                    continue
                valor = item.get("close")
                if valor is not None and float(valor) > 0:
                    return float(valor)
                break

    if isinstance(mt5, dict):
        win_mt5 = (mt5.get("ativos") or {}).get("WIN") or {}
        valor = win_mt5.get("last")
        if valor is not None and float(valor) > 0:
            return float(valor)

    return None


def _obter_abertura_leilao() -> Dict[str, Any]:
    """
    Chama o LeilaoService (OCR) e retorna dict com preco/timestamp/fonte.
    Em caso de falha, retorna indisponível.
    """
    indisponivel = {
        "disponivel": False,
        "preco": None,
        "timestamp": None,
        "fonte": "INDISPONIVEL",
    }

    if not LEILAO_SERVICE_DISPONIVEL:
        return indisponivel

    try:
        svc = LeilaoService(COLETAS_DIR)
        return svc.obter_preco_leilao()
    except Exception as e:
        print(f"⚠️ LeilaoService falhou: {e}")
        return indisponivel


def coletar_dados_entrada() -> Optional[DadosEntrada]:
    ativos = carregar_json("DadosAtivosUnificados.json").get("ativos", {})
    estimativa = carregar_json("EstimativaAbertura.json")
    validados = carregar_json("Dados_Validados.json")
    mt5 = carregar_json("Dados_MT5_v2_2.json")
    congelado = carregar_json("LastTick_Congelado.json")

    est_win = _extrair_estimativa_win(estimativa)
    pivots = estimativa.get("pivot_points", {}).get("WIN_FUT", {})

    metricas = carregar_json("Metricas_Calculadas.json")
    indicadores = metricas.get("indicadores_compostos", {})
    macro = metricas.get("indicadores_macro", {})
    adrs_data = metricas.get("performance_relativa", {}).get("adrs_brasileiras", {})

    decisao_v2 = carregar_json("Decisao_V2.json")
    win_core = decisao_v2.get("decisao", {})

    tendencias_raw = carregar_json("Analise_Tendencias.json")
    tendencia_win_data = None
    for chave in ["WIN_FUT", "BMFBOVESPA:WIN1!"]:
        if chave in tendencias_raw:
            tendencia_win_data = tendencias_raw[chave]
            break

    noticias = carregar_json("Noticias_Impacto_Dia.json")
    alertas = noticias.get("alertas", {})
    resumo_noticias = noticias.get("resumo", {})

    # ---- WIN: preço atual ----
    win_ativo = ativos.get("WIN_FUT", {})
    win_atual = win_ativo.get("preco")
    win_high = win_ativo.get("high")
    win_low = win_ativo.get("low")
    ajuste_win = ativos.get("WIN_AJUSTE", {}).get("preco")

    # ---- Preço do LEILÃO (OCR) ----
    leilao = _obter_abertura_leilao()

    # ---- Abertura teórica CALCULADA (do CalculadoraEstimativaAbertura) ----
    abertura_teorica_calculada = float(est_win.get("abertura_teorica_pontos", 0.0) or 0.0)

    # ---- Prioridade: OCR > Calculado > Ajuste ----
    abertura_leilao_real: Optional[float] = None
    abertura_leilao_timestamp: Optional[str] = None

    if leilao.get("disponivel") and leilao.get("preco"):
        abertura_projetada = float(leilao["preco"])
        fonte_abertura = "OCR_LEILAO"
        abertura_leilao_real = float(leilao["preco"])
        abertura_leilao_timestamp = leilao.get("timestamp")
    elif abertura_teorica_calculada > 0:
        abertura_projetada = abertura_teorica_calculada
        fonte_abertura = "CALCULADO"
    else:
        abertura_projetada = float(ajuste_win or 0.0)
        fonte_abertura = "AJUSTE"

    # Preço atual com fallback em cascata
    if win_atual is None or float(win_atual or 0.0) <= 0:
        win_atual = abertura_projetada or ajuste_win or 0.0

    # Fechamento anterior via 3 fontes
    fechamento_anterior = _extrair_preco_referencia_win(congelado, validados, mt5)
    if fechamento_anterior is None or fechamento_anterior <= 0:
        fechamento_anterior = float(ajuste_win or 0.0)

    # high/low do congelado (informativo)
    if (win_high is None or win_low is None) and isinstance(congelado, dict):
        ticks = congelado.get("ticks") or {}
        win_tick = ticks.get("WIN_LAST_TICK") or {}
        dados = win_tick.get("dados_reais") or {}
        if win_high is None:
            win_high = dados.get("high")
        if win_low is None:
            win_low = dados.get("low")

    abertura_teorica = DadosAberturaTeorica(
        variacao_teorica_pct=est_win.get("variacao_teorica_pct", 0.0),
        abertura_teorica_pontos=abertura_projetada,
        pontos_ajuste_base=est_win.get("preco_referencia_base", 0.0),
    )

    pivot = DadosPivot(
        pp=pivots.get("PP", 0.0),
        r1=pivots.get("R1", 0.0),
        r2=pivots.get("R2", 0.0),
        s1=pivots.get("S1", 0.0),
        s2=pivots.get("S2", 0.0),
    )

    contexto = DadosContexto(
        vix=macro.get("vix"),
        vix_var=macro.get("vix_change_pct"),
        sp500=ativos.get("SP500_FUT", {}).get("preco"),
        sp500_var=ativos.get("SP500_FUT", {}).get("variacao_pct"),
        nasdaq=ativos.get("NASDAQ_FUT", {}).get("preco"),
        nasdaq_var=ativos.get("NASDAQ_FUT", {}).get("variacao_pct"),
        ewz=ativos.get("EWZ", {}).get("preco"),
        ewz_var=ativos.get("EWZ", {}).get("variacao_pct"),
        dxy=ativos.get("DXY", {}).get("preco"),
        dxy_var=ativos.get("DXY", {}).get("variacao_pct"),
        iron_ore=ativos.get("IRON_ORE", {}).get("preco"),
        iron_var=ativos.get("IRON_ORE", {}).get("variacao_pct"),
        crude_oil=ativos.get("CRUDE_OIL", {}).get("preco"),
        crude_var=ativos.get("CRUDE_OIL", {}).get("variacao_pct"),
        adrs={
            ticker: {
                "close": data.get("close"),
                "change_percent": data.get("change_percent"),
            }
            for ticker, data in adrs_data.items()
        },
        indicador_mercado_externo=indicadores.get("indicador_mercado_externo"),
        indicador_adrs_brasileiras=indicadores.get("indicador_adrs_brasileiras"),
    )

    tendencia = DadosTendencia()
    if tendencia_win_data:
        tendencia.padrao = tendencia_win_data.get("padrao_comportamento", "N/A")
        tendencia.variacao_pct = tendencia_win_data.get("intervalo_5_para_0", {}).get("variacao_pct", 0.0)
        tendencia.tendencia = tendencia_win_data.get("intervalo_5_para_0", {}).get("tendencia", "N/A")

    noticias_obj = DadosNoticias(
        tem_3_estrelas_brasil_0900=alertas.get("tem_3_estrelas_brasil_0900", False),
        tem_3_estrelas_outros=alertas.get("tem_3_estrelas_outros_horarios", False),
        tem_multiplas_2_estrelas=alertas.get("tem_multiplas_2_estrelas_mesmo_horario", False),
        classificacao_impacto=resumo_noticias.get("classificacao", "BAIXO"),
        risco_abertura_win=alertas.get("risco_abertura_WIN", False),
    )

    return DadosEntrada(
        timestamp=datetime.now().isoformat(),
        fechamento_anterior_win=fechamento_anterior,
        ajuste_win=ajuste_win,
        preco_atual_win=win_atual,
        maxima_pre_abertura=win_high,
        minima_pre_abertura=win_low,
        abertura_teorica=abertura_teorica,
        pivot_win=pivot,
        contexto=contexto,
        tendencia_win=tendencia,
        noticias=noticias_obj,
        core_win_vies=win_core.get("vies_final"),
        core_win_score=win_core.get("score_numeric"),
        # Novos campos
        abertura_leilao_real=abertura_leilao_real,
        abertura_leilao_timestamp=abertura_leilao_timestamp,
        abertura_teorica_calculada=abertura_teorica_calculada,
        fonte_abertura=fonte_abertura,
    )
```

### `NOVO_MOTOR_PREVISAO_ABERTURA/dados/schemas.py`

```python
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
    adrs: Dict[str, Dict[str, Optional[float]]] = field(default_factory=dict)
    indicador_mercado_externo: Optional[float] = None
    indicador_adrs_brasileiras: Optional[float] = None


@dataclass
class DadosAberturaTeorica:
    """Estimativa de abertura calculada (ou OCR)."""
    variacao_teorica_pct: float = 0.0
    abertura_teorica_pontos: float = 0.0
    pontos_ajuste_base: float = 0.0
    gap_teorico: float = 0.0


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

    # ---- NOVOS CAMPOS (integração LeilaoService) ----
    abertura_leilao_real: Optional[float] = None        # valor do OCR
    abertura_leilao_timestamp: Optional[str] = None     # timestamp do OCR
    abertura_teorica_calculada: Optional[float] = None  # valor do CalculadoraEstimativaAbertura
    fonte_abertura: str = "CALCULADO"                   # "OCR_LEILAO" | "CALCULADO" | "AJUSTE"

    def to_dict(self) -> Dict[str, Any]:
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
    intensidade: str = "NEUTRO"
    classificacao: str = ""


@dataclass
class AnaliseAjuste:
    """Posição relativa ao ajuste."""
    distancia_pontos: float = 0.0
    distancia_percentual: float = 0.0
    posicao: str = "NEUTRO"
    testou_ajuste: bool = False
    rejeitou: bool = False
    aceitou: bool = False
    perdeu: bool = False
    recuperou: bool = False


@dataclass
class Cenario:
    """Cenário principal ou alternativo."""
    nome: str = "INDEFINIDO"
    descricao: str = ""
    condicao: str = ""
    gatilho_entrada: str = ""
    confirmacao: str = ""
    invalidacao: str = ""
    probabilidade_estimada: float = 0.0


@dataclass
class ScorePrevisao:
    """
    Score direcional normalizado.

    - `valor`     : magnitude da força (0-100)
    - `direcao`   : "COMPRA" | "VENDA" | "NEUTRO"
    - `forca`     : "FRACO" | "MODERADO" | "FORTE" | "MUITO FORTE"
    - `classificacao`: legível, ex: "FORTE COMPRA"
    - `detalhes`  : contribuição individual por fator
    """
    valor: float = 0.0
    direcao: str = "NEUTRO"
    forca: str = "FRACO"
    classificacao: str = "NEUTRO"
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
    direcao_prevista: str = "NEUTRO"
    analise_ajuste: AnaliseAjuste = field(default_factory=AnaliseAjuste)
    cenario_principal: Cenario = field(default_factory=Cenario)
    cenario_alternativo: Cenario = field(default_factory=Cenario)
    score: ScorePrevisao = field(default_factory=ScorePrevisao)
    metadados: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        dados = asdict(self)
        if isinstance(dados.get("timestamp"), datetime):
            dados["timestamp"] = dados["timestamp"].isoformat()
        return dados
```
