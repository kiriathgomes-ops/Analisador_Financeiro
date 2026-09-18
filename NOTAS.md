@"
# Notas de Desenvolvimento — Analisador Financeiro

Última atualização: 15/09/2026
Branch atual: feature/LeitorOCR_PrecoTeorico
Versão do motor: V3.2-VisaoC

## 🎯 Estado atual

- Pipeline completo rodando em ~2.5s (`python main_pipeline.py`)
- Confluência obrigatória entre SMC (técnico) e NOVO_MOTOR (macro)
- Visão C: bloqueia operação quando NOVO_MOTOR tem divergência interna
- Score direcional (COMPRA/VENDA/NEUTRO + força)
- Cenários probabilísticos (números, não só texto)
- Aberturas duplas (OCR leilão + Calculadora) no Decisao_V2.json
- Page Streamlit com confluência visual

## ⚠️ Pendências conhecidas

### Alta prioridade
1. **OCR com poucas leituras**
   - `win_abertura_sniper.py` capturou só 11 leituras em 15/09
   - Esperado: 30-50 leituras entre 08:55 e 09:05
   - Investigar: região capturada, âncora do ponto, frequência

2. **Variação teórica da Calculadora oscila**
   - Base já está fixa (ajuste oficial)
   - Mas `variacao_teorica_pct` muda com EWZ/S&P durante o dia
   - Solução futura: congelar cálculo por dia

### Média prioridade
3. **Pesos da confluência (SMC 60% + NM 40%)** — chute
   - Precisa backtest com Coletas/Historico_Aberturas/

4. **Limiares do motor_gap** (MICRO/PEQUENO/MODERADO/FORTE/EXTREMO)
   - Valores empíricos, não calibrados

### Baixa prioridade
5. **Falso positivo no Temp_Validacao_Smoke.py**
   - Procura `processar_calculos`, mas o nome real é `processar_calculos_operacionais`
   - Correção: 1 linha

6. **Dedup OB por ativo no Motor_SMC_Regras.py**
   - Threshold fixo de 10 pts é pouco pro WIN
   - Ideal: 50 pts WIN, 5 pts WDO

## 📁 Estrutura de arquivos chave

- `main_pipeline.py` — orquestrador do pipeline
- `v2/core/engines/v2_orchestrator.py` — decisão final (V3.2-VisaoC)
- `v2/core/services/leilao_service.py` — leitura do OCR
- `v2/core/services/prediction_service.py` — ponte para o NOVO_MOTOR
- `NOVO_MOTOR_PREVISAO_ABERTURA/` — motor de previsão
- `Coletas/preco_teorico_win_fluxo.csv` — CSV do OCR
- `Coletas/Decisao_V2.json` — output final

## 🔑 Comandos rápidos

- Rodar pipeline: `python main_pipeline.py`
- Rodar só decisão: `python v2_rodar_decisao_completa.py`
- Ver decisão atual: `python -c "import json; d = json.load(open('Coletas/Decisao_V2.json', encoding='utf-8')); print(json.dumps(d, indent=2, ensure_ascii=False))"`
- Rodar Streamlit: `streamlit run app_home.py`
- Testar LeilaoService: `python -m v2.core.services.leilao_service`

## 📊 Último teste (15/09/2026 11:11)

- SMC: VENDA (85%)
- NOVO_MOTOR: VENDA gap -710 pts, score NEUTRO (conflito interno)
- Decisão: NEUTRO (0%) por Visão C (bloqueio por divergência)
"@ | Out-File -FilePath NOTAS.md -Encoding utf8