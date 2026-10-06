import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from config import ENGINE_VIES_COMO_FALLBACK
except ImportError:
    ENGINE_VIES_COMO_FALLBACK = False

try:
    from NOVO_MOTOR_PREVISAO_ABERTURA.core.motor_previsao import executar_previsao
    NOVO_MOTOR_DISPONIVEL = True
except ImportError:
    NOVO_MOTOR_DISPONIVEL = False

try:
    from Engine_Vies import executar_core
    LEGADO_DISPONIVEL = True
except ImportError:
    LEGADO_DISPONIVEL = False

from ..contracts import PredictionContext


class PredictionService:
    def get_prediction(self) -> Optional[PredictionContext]:
        # ------------------------------------------------------------
        # 1. NOVO_MOTOR (fonte oficial) — aceita SEMPRE
        # ------------------------------------------------------------
        if NOVO_MOTOR_DISPONIVEL:
            try:
                dados = executar_previsao()
                if dados:
                    return self._criar_contexto_novo_motor(dados)
                else:
                    print("⚠️ PredictionService: NOVO_MOTOR retornou vazio.")
            except Exception as e:
                print(f"⚠️ PredictionService: erro no NOVO_MOTOR: {e}")

        # ------------------------------------------------------------
        # 2. Fallback condicional (Engine_Vies legado) — REMOVIDO (fix70)
        # ------------------------------------------------------------
        # fix70: bloco removido por ser codigo morto inalcancavel.
        # ENGINE_VIES_COMO_FALLBACK = False sempre (config.py nao exporta
        # a constante; ImportError na l.11-13 cai no default False).
        # Alem disso, lia chave "analise_operacional" que foi renomeada
        # para "estimativa_abertura" no calculador atual.
        # Se um dia o fallback legado voltar a ser necessario, reaproveitar
        # este bloco via commit 0ca5b5a (historico git) com a chave correta.

        # ------------------------------------------------------------
        # 3. Nenhuma fonte disponível
        # ------------------------------------------------------------
        print("❌ PredictionService: nenhuma fonte de previsão disponível.")
        return None

    def _criar_contexto_novo_motor(self, dados: Dict) -> PredictionContext:
        """
        Constrói o PredictionContext a partir do output do NOVO_MOTOR.
        Popula TODOS os campos novos (score direcional, divergência, aberturas, cenários).
        """
        score_obj = dados.get("score", {}) or {}
        cenario_p = dados.get("cenario_principal", {}) or {}
        cenario_a = dados.get("cenario_alternativo", {}) or {}

        return PredictionContext(
            # ---- Legados ----
            timestamp=datetime.fromisoformat(
                dados.get("timestamp", datetime.now().isoformat())
            ),
            ativo=dados.get("ativo", "WIN"),
            abertura_projetada=dados.get("abertura_projetada", 0.0),
            faixa_provavel_inferior=(
                dados["faixa_provavel"][0] if dados.get("faixa_provavel") else 0.0
            ),
            faixa_provavel_superior=(
                dados["faixa_provavel"][1] if dados.get("faixa_provavel") else 0.0
            ),
            gap_pontos=dados.get("gap", {}).get("pontos", 0.0),
            gap_percentual=dados.get("gap", {}).get("percentual", 0.0),
            gap_intensidade=dados.get("gap", {}).get("intensidade", "N/A"),
            classificacao_gap=dados.get("gap", {}).get("classificacao", "N/A"),
            # fix63b: gap_fonte pode vir nested (gap.fonte) ou top-level (gap_fonte)
            gap_fonte=(
                (dados.get("gap") or {}).get("fonte")
                or dados.get("gap_fonte")
                or "DESCONHECIDO"
            ),
            direcao_prevista=dados.get("direcao_prevista", "NEUTRO"),
            score=score_obj.get("valor", 0.0),
            score_classificacao=score_obj.get("classificacao", "N/A"),
            score_detalhes=score_obj.get("detalhes", {}),
            analise_ajuste=dados.get("analise_ajuste", {}),
            cenario_principal=cenario_p,
            cenario_alternativo=cenario_a,
            metadados=dados.get("metadados", {}),

            # ---- Score direcional ----
            score_direcao=score_obj.get("direcao", "NEUTRO"),
            score_forca=score_obj.get("forca", "FRACO"),
            score_magnitude=score_obj.get("valor", 0.0),

            # ---- Divergência ----
            divergencia_direcao=bool(dados.get("divergencia_direcao", False)),
            divergencia_detalhes=str(dados.get("divergencia_detalhes", "")),

            # ---- Aberturas ----
            abertura_leilao_real=dados.get("abertura_leilao_real"),
            abertura_leilao_timestamp=dados.get("abertura_leilao_timestamp"),
            abertura_teorica_calculada=dados.get("abertura_teorica_calculada"),
            fonte_abertura=dados.get("fonte_abertura", "DESCONHECIDA"),

            # ---- Cenários probabilísticos ----
            cenario_principal_nome=cenario_p.get("nome", ""),
            cenario_principal_probabilidade=float(
                cenario_p.get("probabilidade_estimada", 0.0) or 0.0
            ),
            cenario_alternativo_nome=cenario_a.get("nome", ""),
            cenario_alternativo_probabilidade=float(
                cenario_a.get("probabilidade_estimada", 0.0) or 0.0
            ),
        )

    def _criar_contexto_neutro(self, motivo: str) -> PredictionContext:
        """Retorna contexto NEUTRO com todos os campos novos zerados."""
        return PredictionContext(
            timestamp=datetime.now(),
            ativo="WIN",
            abertura_projetada=0.0,
            faixa_provavel_inferior=0.0,
            faixa_provavel_superior=0.0,
            gap_pontos=0.0,
            gap_percentual=0.0,
            gap_intensidade="N/A",
            classificacao_gap="N/A",
            direcao_prevista="NEUTRO",
            score=0.0,
            score_classificacao="FRACO",
            score_detalhes={},
            analise_ajuste={},
            cenario_principal={},
            cenario_alternativo={},
            metadados={"fonte": "FALLBACK_NEUTRO", "motivo_neutro": motivo},
            score_direcao="NEUTRO",
            score_forca="FRACO",
            score_magnitude=0.0,
        )