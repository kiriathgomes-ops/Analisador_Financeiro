# ============================================================
# gerar_relatorio_pdf_final.py
# Gera PDF com reportlab, removendo tags HTML problemáticas
# ============================================================

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import os
from datetime import datetime

# ------------------------------------------------------------
# CONTEÚDO DO RELATÓRIO (MESMO TEXTO)
# ------------------------------------------------------------
CONTEUDO = """
Perfeito. O entendimento está confirmado. Com base no `App_Completo.txt` (que contém todos os seus módulos) e no JSON de exemplo, mapeei integralmente o fluxo de dados, as dependências e os scripts órfãos.

Abaixo está o **relatório completo em tabelas**, estruturado em quatro blocos:
1. **Coleta** – origens brutas e periodicidade.
2. **Processamento** – transformações e encadeamento.
3. **Consumidores Finais (UI)** – quais páginas utilizam quais JSONs.
4. **Scripts Inativos / Órfãos** – com sugestão de ação (deletar ou mover para reserva).

---

## 1. TABELA DE COLETA (DADOS BRUTOS)

| Script | O que coleta | Fonte (De onde) | Frequência | Quem consome (próximo elo) |
| :--- | :--- | :--- | :--- | :--- |
| `Coletor.py` | • PTAX oficial (USD_BRL) <br> • Ajuste B3 (WIN_AJUSTE / WDO_AJUSTE) <br> • 21 ativos globais (VIX, S&P, NASDAQ, DXY, ADRs, Minério, Petróleo, etc.) <br> • Último tick (last) via MT5 (WIN/WDO) – na janela de ajuste | BACEN SGS (API), TradingView Scanner API, MetaTrader 5 (v2.2 preferencial / v1 fallback) | A cada 5 min (disparado pelo Agendador) | `Validador.py` e `Limpar_Imagens_TradingView.py` (paralelo) |
| `Coleta_Noticias_Calendario.py` | Calendário econômico Brasil e EUA (eventos 2★ e 3★) | TradingView Economic Calendar API | 1 vez ao dia (cache reutilizado se já coletado hoje) | `Analise_Noticias.py` |
| `Coletor_MT5_v2_2.py` (preferencial) <br> `Coletor_MT5.py` (fallback) | Last / Bid / Ask / Volume dos contratos WIN, WDO, DI1 (seleção dinâmica do contrato mais líquido) | MetaTrader 5 (terminal) | Apenas quando chamado pelo `Coletor.py` (dentro da janela de ajuste 19:00–08:50) | `Coletor.py` (integração via `capturar_last_do_mt5()`) |

---

## 2. TABELA DE PROCESSAMENTO (TRANSFORMAÇÕES E AGREGAÇÕES)

| Script | Informação gerada | Insumos (dependências) | Frequência | Quem consome o resultado |
| :--- | :--- | :--- | :--- | :--- |
| `Limpar_Imagens_TradingView.py` | Gerencia imagens de gráficos (move as 2 mais recentes para `Coletas/WIN_1min.png` e `WIN_5min.png`) | Imagens baixadas na pasta `Downloads` do usuário | Executado no pipeline (etapa 0) | Páginas de análise visual (UI) – `7_🤖_IA_Imagem.py`, `7_🤖_IA_Gemini.py`, `8_📥_Gerador_Profit_Pro.py` |
| `Validador.py` | `Dados_Validados.json` (sanitiza e padroniza os 24 ativos) | `Coleta_rom-0.json` | A cada 5 min (pipeline) | `Calculadora.py`, `CalculadoraEstimativaAbertura.py` |
| `Analise_Noticias.py` | `Noticias_Impacto_Dia.json` (classificação de risco, alertas 3★, múltiplas 2★) | `Noticias_Calendario.json` | 1x ao dia (ou quando chamado) | `Engine_Vies.py`, UI (`pages/13_📅_Noticias.py`) |
| `MapearTendencia15Min.py` | `Analise_Tendencias.json` (comportamento das últimas 3 coletas: rom-10 → rom-5 → rom-0) | `Coleta_rom-10.json`, `Coleta_rom-5.json`, `Coleta_rom-0.json` | A cada 5 min (pipeline) | `Engine_Vies.py`, UI (`pages/6_🔬_Analise_Tendencia.py`, `pages/1_🎯_Setup_Abertura.py`) |
| `Calculadora.py` | `Metricas_Calculadas.json` (spreads, curva DI, VIX, indicador mercado externo, indicador ADRs) | `Dados_Validados.json` | A cada 5 min (pipeline) | `Engine_Vies.py`, UI (`pages/4_🔢_Calculadora.py`, `pages/5_⚙️_Core_Engine.py`) |
| `CalculadoraEstimativaAbertura.py` | `EstimativaAbertura.json` (abertura teórica WIN/WDO, pivôs, resumo macro) | `Dados_Validados.json` | A cada 5 min (pipeline) | `Engine_Vies.py`, `Gerar_Resultado_Operacional_Abertura.py`, UI (`pages/4_🔢_Calculadora.py`) |
| `Motor_SMC_Regras.py` (via `Rodar_SMC_Regras.py`) | `AnaliseGraficaSMC_Regras.json` (OB, FVG, BOS/CHoCH, liquidez, níveis) | MetaTrader 5 (candles 5min) | A cada 5 min (pipeline) | `Engine_Vies.py` (via UI/prompt), UI (`pages/9_📊_SMC_Regras.py`, `pages/1_🎯_Setup_Abertura.py`) |
| `Engine_Vies.py` | `Decisao_Core.json` (viés final e score para WIN e WDO, com fatores relevantes) | `EstimativaAbertura.json`, `Metricas_Calculadas.json`, `Noticias_Impacto_Dia.json`, `DadosAtivosUnificados.json`, `Analise_Tendencias.json`, `AnaliseGraficaSMC_Regras.json` | A cada 5 min (pipeline) | UI (`pages/5_⚙️_Core_Engine.py`, `pages/1_🎯_Setup_Abertura.py`), `Gerar_Resultado_Operacional_Abertura.py` |
| `Gerar_Resultado_Operacional_Abertura.py` | `Resultado_Calculadora_Operacional_Abertura.json` (consolida todos os indicadores + classificação operacional) | `Metricas_Calculadas.json`, `EstimativaAbertura.json`, `Decisao_Core.json`, `DadosAtivosUnificados.json`, `Analise_Tendencias.json`, `Noticias_Calendario_0900.json` | A cada 5 min (pipeline) | UI (`pages/1_🎯_Setup_Abertura.py`, `pages/4_🔢_Calculadora.py`) |
| `Gerar_Relatorio.py` | `Relatorio_Executivo.md` (relatório macro em Markdown) | `Metricas_Calculadas.json` | A cada 5 min (pipeline) | UI (exibição textual) |
| `Gerar_Relatorio_Mensagem.py` | Relatório de abertura (texto) | `EstimativaAbertura.json` | A cada 5 min (pipeline) | UI (utilizado em algumas páginas como resumo) |
| `v2_gravar_sessao_win.py` | Histórico de sessão em `Coletas/Historico_Aberturas/YYYY-MM-DD.json` (usando a nova arquitetura V2) | Todos os dados via `build_win_session()` + `opening_scenario_engine` | A cada 5 min (pipeline) | UI V2 (`pages/20_📈_Previsao_Abertura_WINFUT.py`, `pages/21_📈_Historico_Macro.py`) |
| `Gerar_Mapa_Projeto.py`, `Gerar_Mapa_Fluxo.py`, `Gerar_ArquivosApp.py` | Mapas de documentação (`Mapa_Projeto.json`, `Mapa_Fluxo.json`, `ArquivosApp.py`) | Escaneamento do sistema de arquivos (sem insumos de dados) | **Manual / sob demanda** (não está no pipeline operacional) | UI (`pages/15_🗺️_Mapa_da_Aplicacao.py`) |

---

## 3. TABELA DE CONSUMIDORES FINAIS (INTERFACE / DASHBOARDS)

Estas páginas **não produzem dados para outras etapas**; apenas leem os JSONs gerados para exibição.

| Página Streamlit | JSONs / Dados que consome |
| :--- | :--- |
| `pages/1_🎯_Setup_Abertura.py` | `Noticias_Calendario_0900.json`, `Metricas_Calculadas.json`, `EstimativaAbertura.json`, `Decisao_Core.json`, `DadosAtivosUnificados.json`, `Analise_Tendencias.json`, `Resultado_Calculadora_Operacional_Abertura.json`, `AnaliseGraficaSMC_Regras.json` |
| `pages/4_🔢_Calculadora.py` | `EstimativaAbertura.json`, `Resultado_Calculadora_Operacional_Abertura.json`, `Metricas_Calculadas.json`, `DadosAtivosUnificados.json`, `Analise_Tendencias.json` |
| `pages/5_⚙️_Core_Engine.py` | `Decisao_Core.json`, `Dados_Validados.json`, `Noticias_Impacto_Dia.json`, `Metricas_Calculadas.json`, `Analise_Tendencias.json`, `EstimativaAbertura.json` |
| `pages/6_🔬_Analise_Tendencia.py` | `Analise_Tendencias.json` |
| `pages/9_📊_SMC_Regras.py` | `AnaliseGraficaSMC_Regras.json`, `AnaliseGraficaSMC.json` (visão IA, se existir) |
| `pages/13_📅_Noticias.py` | `Noticias_Impacto_Dia.json`, `Noticias_Calendario.json` |
| `pages/14_📡_Ativos_Monitorados.py` | `DadosAtivosUnificados.json` |
| `pages/15_🗺️_Mapa_da_Aplicacao.py` | `Mapa_Projeto.json`, `Mapa_Fluxo.json`, `Pipeline_Log.json` |
| `pages/16_📊_Dados_MT5.py` | `Dados_MT5.json` (via `Coletor_MT5`) |
| `pages/18_🔮_Previsao_Inteligente_Abertura.py` | Dados do novo motor (via `NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_previsao.py`) |
| `pages/19_🔮_Previsao_Inteligente_Abertura_Comparador.py` | Mesmo do 18 + comparação com legado (`Decisao_Core.json`) |
| `pages/20_📈_Previsao_Abertura_WINFUT.py` | V2 (`build_win_session()`, `opening_scenario_engine`) |
| `pages/21_📈_Historico_Macro.py` | `Coleta_rom-*.json` (leitura direta dos ROMs) |
| `pages/7_🤖_IA_Gemini.py` | Imagens (`WIN_1min.png`, `WIN_5min.png`) – gera `AnaliseGraficaSMC.json` (visão IA) |
| `pages/7_🤖_IA_Imagem.py` | Imagens + dados do pipeline (via `KeyManager` e leitura dos JSONs) |
| `pages/8_📥_Gerador_Profit_Pro.py` | `AnaliseGraficaSMC_Regras.json`, `AnaliseGraficaSMC.json` ou texto colado |

---

## 4. TABELA DE SCRIPTS INATIVOS / ÓRFÃOS (NÃO UTILIZADOS NO PIPELINE OPERACIONAL)

| Script | Motivo / Status | Ação sugerida |
| :--- | :--- | :--- |
| `Coletor copy.py` | Cópia exata do `Coletor.py`. Não é chamado por ninguém. | 🗑️ **Deletar** (redundante) |
| `Monitor_WIN_Leilao.py` | Monitor avulso de leilão (não integrado ao pipeline). | 📁 **Mover para pasta `_reservados/`** |
| `Teste_Book_WIN.py`, `Teste_Historico_Ticks_WIN.py`, `Teste_Leilao_MT5.py`, `Teste_MT5.py`, `Teste_Vencimento_MT5.py` | Scripts de teste/debug do MT5. Não chamados por nenhum módulo. | 📁 **Mover para `_reservados/testes/`** |
| `test_import.py`, `teste_motor.py` | Testes de importação do `KeyManager` e do novo motor. | 📁 **Mover para `_reservados/testes/`** |
| `diagnostico_env.py` | Diagnóstico de variáveis de ambiente (.env). | 📁 **Mover para `_reservados/utilitarios/`** |
| `Gerar_ArquivosApp.py`, `Gerar_Mapa_Inventario_Tecnico.py` | Geradores de inventário (substituídos por `Gerar_Mapa_Projeto.py` e `Gerar_Mapa_Fluxo.py`). | 🗑️ **Deletar** ou 📁 **Mover para `_reservados/legado/`** |
| `pages/3_🎯_Setup_Abertura_10h.py` | Página separada para setup das 10h (não linkada no menu principal do `app_home.py`). Aparentemente obsoleta (unificada na `pages/1_...`). | 📁 **Mover para `_reservados/pages_antigas/`** |
| `pages/8_📥_Gerador_Profit_Pro_Orignal.py` | Cópia antiga do gerador Profit Pro (substituída pela versão atual `8_📥_Gerador_Profit_Pro.py`). | 🗑️ **Deletar** |
| `pages/20_📈_Previsao_Abertura_WINFUTa.py` e `...s.py` | Versões intermediárias da página V2 (não linkadas). | 📁 **Mover para `_reservados/pages_antigas/`** |
| `pages/21_📈_Historico_Macro copy.py` e `copy 2.py` | Cópias antigas da página de histórico macro. | 🗑️ **Deletar** ou 📁 **Mover para `_reservados/pages_antigas/`** |

---

**Resumo executivo**:
- O pipeline tem **8 etapas de coleta/processamento ativas** que se encadeiam corretamente.
- A maioria dos scripts órfãos são **testes, duplicatas ou utilitários de documentação** que não afetam a operação.
- Recomendo criar a pasta `_reservados/` na raiz e mover todos os listados como "📁 Mover" para manter o projeto limpo, sem perdê-los.
"""

# ------------------------------------------------------------
# FUNÇÃO PARA LIMPAR TAGS HTML E CARACTERES PROBLEMÁTICOS
# ------------------------------------------------------------
def limpar_texto(texto):
    # Remove tags <br> e <br /> (substitui por espaço)
    texto = texto.replace('<br>', ' ').replace('<br />', ' ')
    # Remove outros caracteres de controle
    texto = texto.replace('\x00', '')
    return texto

# ------------------------------------------------------------
# GERAR PDF
# ------------------------------------------------------------
def gerar_pdf():
    nome_arquivo = f"Relatorio_Fluxo_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    doc = SimpleDocTemplate(nome_arquivo, pagesize=A4,
                            rightMargin=40, leftMargin=40,
                            topMargin=40, bottomMargin=30)

    styles = getSampleStyleSheet()
    style_normal = styles['Normal']
    style_normal.fontSize = 9
    style_normal.leading = 12

    style_title = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontSize=14,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=12
    )

    style_subtitle = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=11,
        leading=14,
        spaceAfter=6,
        spaceBefore=10
    )

    story = []
    story.append(Paragraph("RELATÓRIO DE FLUXO - ANALISADOR FINANCEIRO", style_title))
    story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", style_normal))
    story.append(Spacer(1, 12))

    # Processa o conteúdo linha a linha
    linhas = CONTEUDO.split('\n')
    for linha in linhas:
        linha_limpa = linha.strip()
        if not linha_limpa:
            story.append(Spacer(1, 6))
            continue

        # Limpa tags HTML
        linha_limpa = limpar_texto(linha_limpa)

        # Detecta cabeçalhos
        if linha_limpa.startswith('##') or linha_limpa.startswith('**'):
            texto = linha_limpa.replace('##', '').replace('**', '').strip()
            story.append(Paragraph(texto, style_subtitle))
        else:
            story.append(Paragraph(linha_limpa, style_normal))

    doc.build(story)
    print(f"✅ PDF gerado com sucesso: {nome_arquivo}")
    print(f"   Local: {os.path.abspath(nome_arquivo)}")

if __name__ == "__main__":
    gerar_pdf()