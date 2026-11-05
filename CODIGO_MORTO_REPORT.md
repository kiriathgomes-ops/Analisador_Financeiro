# 🔍 Relatório de Código Morto — V2

**Raiz:** `E:\ProjetosPython\Analisador_Financeiro`

## 📊 Sumário

| Categoria | Quantidade |
|---|---|
| 🔴 Código morto real | **18** |
| 👻 Arquivos fantasmas | **0** |
| 🚪 Entry points (Streamlit/app) | 22 |
| 🔧 Ferramentas (uso manual) | 30 |
| 🧪 Testes (pytest) | 1 |
| ✅ Ativos | 43 |
| **Total** | **124** |

---

## 👻 Arquivos Fantasmas (0)

Estes arquivos são importados **apenas** por `__init__.py` que, por sua vez, não são usados por nenhum código real. São zumbis — parecem vivos (têm importadores), mas o importador está morto também.

**Candidatos a `_legado/` com prioridade máxima.**

✅ Nenhum fantasma detectado.


---

## 🔴 Código Morto Real (18)

Não é importado por ninguém, não está em `ferramentas/`, não é teste, não é entry point. **Pode ser deletado ou movido para `_legado/`.**

| Arquivo | Linhas | Tem `__main__` |
|---|---|---|
| `__mapeador_fluxo.py` | 101 | ✅ |
| `__mapear_pipeline.py` | 57 | ✅ |
| `_auditar_coleta_dupla.py` | 84 | ✅ |
| `_auditoria_final_coletas.py` | 87 | ✅ |
| `_auditoria_geral_coletas.py` | 113 | ✅ |
| `_checar_coletas_agora.py` | 96 | ✅ |
| `_checkup_geral.py` | 139 | ✅ |
| `_detector_codigo_morto.py` | 475 | ✅ |
| `_diagnostico_S1_S4_S5.py` | 285 | ✅ |
| `_mapear_dados_spike.py` | 122 | ✅ |
| `_testar_adr_api.py` | 50 | ❌ |
| `_testar_session_close.py` | 19 | ❌ |
| `_varrer_except_pass.py` | 217 | ✅ |
| `Agendador.py` | 125 | ✅ |
| `ativar_cloudflared.py` | 130 | ✅ |
| `Coletas\ArquivosApp.py` | 2891 | ✅ |
| `main_pipeline.py` | 174 | ✅ |
| `win_abertura_sniper.py` | 570 | ✅ |

---

## 🚪 Entry Points (22)

- ✅ `app_home.py` — *Entry point principal*
- ✅ `lixeira_analise\main.py` — *Entry point principal*
- ✅ `pages\1_⚡_Dashboard_Leilao_AoVivo.py` — *Streamlit page*
- ✅ `pages\2_🎯_Setup_Abertura.py` — *Streamlit page*
- ✅ `pages\3_⚡_Monitor_Abertura_Leilao.py` — *Streamlit page*
- ✅ `pages\4_⚡_WINFUT_Intraday.py` — *Streamlit page*
- ✅ `pages\5_📡_Ativos_Monitorados.py` — *Streamlit page*
- ✅ `pages\6_📈_Matriz_de_Influencia.py` — *Streamlit page*
- ✅ `pages\7.1_📊_SMC_Regras.py` — *Streamlit page*
- ✅ `pages\7.2_🤖_IA_SpikeImagem.py` — *Streamlit page*
- ✅ `pages\7.3_📥_Gerador_Profit_Pro.py` — *Streamlit page*
- ✅ `pages\7.4_🤖_IA_Spike_Texto.py` — *Streamlit page*
- ✅ `pages\7.5_📅_Noticias.py` — *Streamlit page*
- ✅ `pages\7_🔬_Analise_Tendencia.py` — *Streamlit page*
- ✅ `pages\8.1_🗺️_Mapa_da_Aplicacao.py` — *Streamlit page*
- ✅ `pages\8.2_🔢_Calculadora.py` — *Streamlit page*
- ✅ `pages\8.3_🔑_Status_Chaves.py` — *Streamlit page*
- ✅ `pages\9.5_📈_Historico_Macro.py` — *Streamlit page*
- ✅ `pages\99_🗺️_Mapa_Mina.py` — *Streamlit page*
- ✅ `v2\pages\1_dashboard_v2.py` — *Streamlit page*
- ✅ `v2\pages\2_analise_detalhada.py` — *Streamlit page*
- ✅ `v2\pages\3_page_cockpit_pregao.py` — *Streamlit page*

---

## 🔧 Ferramentas (30)

Scripts executados manualmente. **Não são código morto.**

- 🔧 `ferramentas\_debug_regiao.py`
- 🔧 `ferramentas\_gerar_arvore.py`
- 🔧 `ferramentas\analises\analisar_divergencia.py`
- 🔧 `ferramentas\analises\analisar_historico.py`
- 🔧 `ferramentas\analises\analisar_historico_v2.py`
- 🔧 `ferramentas\analises\analise_divergencia_smc_nm.py`
- 🔧 `ferramentas\analises\analise_trilha_c_v2.py`
- 🔧 `ferramentas\analises\backtest_bias_estabilidade.py`
- 🔧 `ferramentas\auditar_coletas.py`
- 🔧 `ferramentas\auditoria\audit_camada1.py`
- 🔧 `ferramentas\auditoria\audit_camada2.py`
- 🔧 `ferramentas\auditoria\diagnostico.py`
- 🔧 `ferramentas\auditoria\limpar_lixo.py`
- 🔧 `ferramentas\buscar_nome_correto.py`
- 🔧 `ferramentas\debug\diag_orb_10h.py`
- 🔧 `ferramentas\debug\ver_componentes_hoje.py`
- 🔧 `ferramentas\docs\gerar_docs.py`
- 🔧 `ferramentas\docs\gerar_dump_completo.py`
- 🔧 `ferramentas\gerar_guia_execucao.py`
- 🔧 `ferramentas\investigar_fantasmas.py`
- 🔧 `ferramentas\mapas\Gerar_Mapa_Inventario_Tecnico.py`
- 🔧 `ferramentas\mapear_dados.py`
- 🔧 `ferramentas\mapear_fluxo.py`
- 🔧 `ferramentas\mapear_regiao_ocr.py`
- 🔧 `ferramentas\minerador.py`
- 🔧 `ferramentas\rastrear_pai.py`
- 🔧 `ferramentas\teste_ocr_direto.py`
- 🔧 `ferramentas\ver_fantasmas.py`
- 🔧 `ferramentas\verificar_escrita.py`
- 🔧 `utils\KeyManager.py`

---

## 🧪 Testes (1)

- 🧪 `v2\tests\test_contracts.py`
