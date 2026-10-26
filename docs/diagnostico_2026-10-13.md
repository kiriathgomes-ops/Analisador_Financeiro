# Diagnóstico — 2026-10-13 16:07


Gerado por `ferramentas/auditoria/diagnostico.py`


## 1. Inventário

| Pasta | Arquivos | Tamanho |
|---|---:|---:|
| `Historico_MT5` | 478 | 4.39 MB |
| `Historico_Decisoes_V2` | 470 | 2.46 MB |
| `Coletas` | 40 | 780.7 KB |
| `Analisador_Financeiro` | 36 | 474.9 KB |
| `fixes` | 36 | 258.9 KB |
| `Historico_Aberturas` | 28 | 7.17 MB |
| `pages` | 27 | 499.1 KB |
| `coleta_preco_teorico_historico` | 18 | 74.4 KB |
| `PromptIA` | 14 | 50.6 KB |
| `ferramentas` | 12 | 67.0 KB |
| `docs` | 10 | 85.4 KB |
| `auditoria` | 9 | 400.1 KB |
| `services` | 9 | 53.7 KB |
| `core` | 7 | 29.1 KB |
| `contracts` | 7 | 14.7 KB |
| `engines` | 5 | 52.0 KB |
| `analises` | 5 | 23.0 KB |
| `cache` | 4 | 405.4 KB |
| `dados` | 3 | 15.7 KB |
| `mapas` | 3 | 20.4 KB |
| `Imagens` | 2 | 343.3 KB |
| `v2` | 2 | 2.8 KB |
| `config` | 2 | 0.7 KB |
| `debug` | 2 | 5.0 KB |
| `arquivo` | 2 | 1.08 MB |
| `NOVO_MOTOR_PREVISAO_ABERTURA` | 1 | 0.1 KB |
| `utils` | 1 | 3.5 KB |
| `tests` | 1 | 2.6 KB |

### Top 30 maiores arquivos

| Arquivo | KB | Modificado |
|---|---:|---|
| `Coletas\Historico_MT5\arquivo\2026-09.zip` | 675.9 | 2026-10-13 16:01 |
| `Coletas\Historico_Aberturas\2026-09-09.json` | 473.4 | 2026-09-09 23:54 |
| `Coletas\Historico_Aberturas\2026-09-10.json` | 465.9 | 2026-09-10 21:39 |
| `Coletas\Historico_Aberturas\2026-09-11.json` | 463.8 | 2026-09-11 18:49 |
| `Coletas\Historico_Aberturas\2026-10-06.json` | 451.7 | 2026-10-06 20:15 |
| `Coletas\Historico_Aberturas\2026-10-07.json` | 434.2 | 2026-10-07 22:40 |
| `Coletas\Historico_MT5\arquivo\2026-10.zip` | 427.2 | 2026-10-13 16:01 |
| `Coletas\Historico_Aberturas\2026-09-23.json` | 410.4 | 2026-09-23 18:04 |
| `Coletas\Historico_Aberturas\2026-09-16.json` | 397.8 | 2026-09-16 19:19 |
| `Coletas\Historico_Aberturas\2026-09-18.json` | 373.3 | 2026-09-18 17:04 |
| `Coletas\Historico_Aberturas\2026-09-08.json` | 370.4 | 2026-09-08 23:29 |
| `Coletas\Historico_Aberturas\2026-09-21.json` | 367.4 | 2026-09-21 19:14 |
| `Coletas\Historico_Aberturas\2026-09-25.json` | 349.3 | 2026-09-25 18:59 |
| `Coletas\Historico_Aberturas\2026-09-17.json` | 326.6 | 2026-09-17 17:59 |
| `Coletas\Historico_Aberturas\2026-10-01.json` | 323.9 | 2026-10-01 17:14 |
| `Coletas\Historico_Aberturas\2026-10-09.json` | 310.0 | 2026-10-09 15:55 |
| `Coletas\Historico_Aberturas\2026-09-24.json` | 294.7 | 2026-09-24 15:09 |
| `Imagens\SpikeIAGrande.jpg` | 260.6 | 2026-08-01 22:00 |
| `Coletas\Historico_Aberturas\2026-10-08.json` | 251.7 | 2026-10-08 16:35 |
| `auditoria\relatorio_mapeamento.md` | 233.1 | 2026-10-08 08:09 |
| `Coletas\Historico_Aberturas\2026-09-28.json` | 232.7 | 2026-09-28 15:04 |
| `Coletas\Historico_Aberturas\2026-10-13.json` | 230.5 | 2026-10-13 16:05 |
| `Coletas\WIN_1min.png` | 211.5 | 2026-09-23 08:11 |
| `Coletas\cache\candles_WINV26_1m.json.bak_teste` | 190.4 | 2026-10-09 08:33 |
| `Coletas\Historico_Aberturas\2026-10-05.json` | 183.9 | 2026-10-05 18:20 |
| `Coletas\Historico_Aberturas\2026-09-30.json` | 173.2 | 2026-09-30 15:54 |
| `Coletas\WIN_5min.png` | 171.5 | 2026-09-23 08:11 |
| `Coletas\Mapa_Projeto.json` | 146.5 | 2026-09-24 08:18 |
| `Coletas\Historico_Aberturas\2026-10-02.json` | 129.7 | 2026-10-02 12:28 |
| `Coletas\cache\candles_WINV26_1m.json` | 121.7 | 2026-10-13 16:05 |

## 2. Integridade


✅ **147 arquivos .py compilam OK**

✅ **1013 arquivos .json parseiam OK** (14.58 MB)

## 3. Freshness dos JSONs de produção

| Arquivo | Idade | Limite | Status |
|---|---:|---:|---|
| `Decisao_V2.json` | 2m | 10m | ✅ OK |
| `DadosAtivosUnificados.json` | 2m | 10m | ✅ OK |
| `Dados_Validados.json` | 2m | 10m | ✅ OK |
| `Dados_MT5_v2_2.json` | 2m | 10m | ✅ OK |
| `Coleta_rom-0.json` | 2m | 10m | ✅ OK |
| `Coleta_ram.json` | 2m | 10m | ✅ OK |
| `Metricas_Calculadas.json` | 2m | 10m | ✅ OK |
| `Analise_Tendencias.json` | 2m | 10m | ✅ OK |
| `AnaliseGraficaSMC_Regras.json` | 2m | 15m | ✅ OK |
| `AnaliseGraficaSMC_MTF.json` | 2m | 15m | ✅ OK |
| `EstimativaAbertura.json` | 2m | 10m | ✅ OK |
| `Resultado_Calculadora_Operacional_Abertura.json` | 2m | 10m | ✅ OK |
| `Noticias_Calendario.json` | 2m | 1440m | ✅ OK |
| `Noticias_Impacto_Dia.json` | 2m | 1440m | ✅ OK |
| `config_regiao.json` | 20.2d | 525600m | ✅ OK |
| `LastTick_Congelado.json` | 4.3d | 525600m | ✅ OK |
| `EstimativaAbertura_Cache.json` | 6.0h | 1440m | ✅ OK |