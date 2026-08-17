# ============================================================
# ARQUIVO: v2/core/services/session_history.py
# FASE 5 — Histórico de Sessões WINFUT
#
# Grava snapshots de WinSession + OpeningScenario
# em Coletas/Historico_Aberturas/YYYY-MM-DD.json
#
# Objetivo futuro: base estatística para probabilidades reais
# (romper / testar / rejeitar / retornar).
# ============================================================

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _raiz_projeto() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def _historico_dir() -> Path:
    d = _raiz_projeto() / "Coletas" / "Historico_Aberturas"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _serializar(obj: Any) -> Any:
    """Converte dataclasses, date, datetime para tipos JSON-safe."""
    if obj is None:
        return None
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serializar(v) for k, v in asdict(obj).items()}
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serializar(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serializar(x) for x in obj]
    if isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


class SessionHistoryService:
    """
    Persiste e lê o histórico de sessões WINFUT.

    Estrutura do arquivo diário:
      Coletas/Historico_Aberturas/2026-08-16.json
      {
        "data": "2026-08-16",
        "atualizacoes": [
          {
            "timestamp": "...",
            "metadata": {...},
            "precos": {...},
            "distancias": {...},
            "gap": {...},
            "cenario": {...},
            "contexto_resumo": [...],
            ...
          }
        ]
      }
    """

    def __init__(self, historico_dir: Optional[Path] = None):
        self.dir = Path(historico_dir) if historico_dir else _historico_dir()
        self.dir.mkdir(parents=True, exist_ok=True)

    def _caminho_dia(self, data_ref: date) -> Path:
        return self.dir / f"{data_ref.isoformat()}.json"

    def salvar_snapshot(
        self,
        session,
        cenario=None,
        tag: Optional[str] = None,
    ) -> Path:
        """
        Acrescenta um snapshot da sessão (e cenário, se houver) no arquivo do dia.

        session: WinSession
        cenario: OpeningScenario (opcional; usa session.cenario se None)
        """
        if cenario is None:
            cenario = getattr(session, "cenario", None)

        data_ref = session.metadata.data_sessao or date.today()
        caminho = self._caminho_dia(data_ref)

        registro: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "tag": tag,
            "metadata": _serializar(session.metadata),
            "precos": _serializar(session.precos),
            "distancias": _serializar(session.distancias),
            "gap": _serializar(session.gap),
            "niveis": _serializar(session.niveis),
            "cenario": _serializar(cenario) if cenario else None,
            "contexto_resumo": (
                list(cenario.contexto_resumo) if cenario and cenario.contexto_resumo else []
            ),
            "extras": _serializar(getattr(session, "extras", {})),
        }

        # Carrega arquivo do dia (se existir) e append
        if caminho.exists():
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    dia = json.load(f)
            except Exception:
                dia = {"data": data_ref.isoformat(), "atualizacoes": []}
        else:
            dia = {"data": data_ref.isoformat(), "atualizacoes": []}

        dia.setdefault("atualizacoes", []).append(registro)
        dia["ultima_atualizacao"] = registro["timestamp"]
        dia["total_snapshots"] = len(dia["atualizacoes"])

        # Resumo do último estado (atalho para leitura rápida)
        dia["ultimo"] = {
            "contrato": session.metadata.contrato_principal,
            "ajuste": session.precos.ajuste,
            "last_mt5": session.precos.last_mt5,
            "distancia_pts": session.distancias.last_vs_ajuste_pts,
            "posicao": (
                cenario.relacao_com_ajuste.posicao
                if cenario and cenario.relacao_com_ajuste
                else None
            ),
            "direcao": cenario.direcao_provavel if cenario else None,
            "cenario_principal": (
                cenario.relacao_com_ajuste.cenario_principal
                if cenario and cenario.relacao_com_ajuste
                else None
            ),
        }

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dia, f, ensure_ascii=False, indent=2)

        return caminho

    def carregar_dia(self, data_ref: Optional[date] = None) -> Dict[str, Any]:
        data_ref = data_ref or date.today()
        caminho = self._caminho_dia(data_ref)
        if not caminho.exists():
            return {"data": data_ref.isoformat(), "atualizacoes": []}
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"data": data_ref.isoformat(), "atualizacoes": []}

    def listar_dias(self) -> List[str]:
        arquivos = sorted(self.dir.glob("*.json"))
        return [a.stem for a in arquivos]

    def resumo_recente(self, n: int = 5) -> List[Dict[str, Any]]:
        """Retorna o campo 'ultimo' dos N dias mais recentes."""
        dias = self.listar_dias()[-n:]
        resultado = []
        for d in dias:
            try:
                data_ref = date.fromisoformat(d)
            except ValueError:
                continue
            dia = self.carregar_dia(data_ref)
            if dia.get("ultimo"):
                item = dict(dia["ultimo"])
                item["data"] = d
                resultado.append(item)
        return resultado


# ------------------------------------------------------------
# Atalhos
# ------------------------------------------------------------

def salvar_sessao_hoje(session, cenario=None, tag: Optional[str] = None) -> Path:
    return SessionHistoryService().salvar_snapshot(session, cenario, tag=tag)


# ------------------------------------------------------------
# Debug / gravação sob demanda
# ------------------------------------------------------------

if __name__ == "__main__":
    from v2.core.services.win_session_builder import build_win_session
    from v2.core.engines.opening_scenario_engine import gerar_cenario_abertura

    print("=" * 60)
    print(" SESSION HISTORY — gravando snapshot de hoje")
    print("=" * 60)

    session = build_win_session()
    cenario = gerar_cenario_abertura(session)
    session.cenario = cenario

    caminho = salvar_sessao_hoje(session, cenario, tag="manual_debug")
    print(f"Salvo em: {caminho}")

    svc = SessionHistoryService()
    dia = svc.carregar_dia()
    print(f"Snapshots no dia: {dia.get('total_snapshots')}")
    print(f"Último resumo  : {dia.get('ultimo')}")
    print("=" * 60)
