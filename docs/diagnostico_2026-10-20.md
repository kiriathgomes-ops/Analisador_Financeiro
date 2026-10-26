# Diagnóstico — 2026-10-20 23:17


Gerado por `ferramentas/auditoria/diagnostico.py`


## 1. Inventário

| Pasta | Arquivos | Tamanho |
|---|---:|---:|
| `Historico_Decisoes_V2` | 1269 | 8.02 MB |
| `Historico_MT5` | 847 | 7.58 MB |
| `Coletas` | 42 | 1.02 MB |
| `Analisador_Financeiro` | 41 | 462.5 KB |
| `fixes` | 36 | 258.9 KB |
| `Historico_Aberturas` | 34 | 9.44 MB |
| `pages` | 22 | 339.8 KB |
| `coleta_preco_teorico_historico` | 22 | 95.6 KB |
| `PromptIA` | 14 | 50.6 KB |
| `docs` | 13 | 95.9 KB |
| `ferramentas` | 13 | 73.8 KB |
| `auditoria` | 9 | 400.1 KB |
| `services` | 9 | 53.7 KB |
| `core` | 7 | 29.1 KB |
| `contracts` | 7 | 14.7 KB |
| `cache` | 7 | 885.1 KB |
| `engines` | 5 | 52.0 KB |
| `analises` | 5 | 23.0 KB |
| `dados` | 3 | 15.7 KB |
| `mapas` | 3 | 20.4 KB |
| `Imagens` | 2 | 343.3 KB |
| `v2` | 2 | 2.8 KB |
| `config` | 2 | 0.7 KB |
| `debug` | 2 | 5.0 KB |
| `arquivo` | 2 | 1.73 MB |
| `NOVO_MOTOR_PREVISAO_ABERTURA` | 1 | 0.1 KB |
| `utils` | 1 | 3.5 KB |
| `tests` | 1 | 2.6 KB |

### Top 30 maiores arquivos

| Arquivo | KB | Modificado |
|---|---:|---|
| `Coletas\Historico_MT5\arquivo\2026-10.zip` | 1099.8 | 2026-10-20 20:10 |
| `Coletas\Historico_MT5\arquivo\2026-09.zip` | 675.9 | 2026-10-13 16:01 |
| `Coletas\Historico_Aberturas\2026-10-15.json` | 626.7 | 2026-10-15 23:00 |
| `Coletas\Historico_Aberturas\2026-10-20.json` | 549.3 | 2026-10-20 23:15 |
| `Coletas\Historico_Aberturas\2026-09-09.json` | 473.4 | 2026-09-09 23:54 |
| `Coletas\Historico_Aberturas\2026-09-10.json` | 465.9 | 2026-09-10 21:39 |
| `Coletas\Historico_Aberturas\2026-09-11.json` | 463.8 | 2026-09-11 18:49 |
| `Coletas\Historico_Aberturas\2026-10-14.json` | 461.0 | 2026-10-14 23:25 |
| `Coletas\Historico_Aberturas\2026-10-06.json` | 451.7 | 2026-10-06 20:15 |
| `Coletas\Historico_Aberturas\2026-10-07.json` | 434.2 | 2026-10-07 22:40 |
| `Coletas\Historico_Aberturas\2026-09-23.json` | 410.4 | 2026-09-23 18:04 |
| `Coletas\Historico_Aberturas\2026-09-16.json` | 397.8 | 2026-09-16 19:19 |
| `Coletas\Historico_Aberturas\2026-09-18.json` | 373.3 | 2026-09-18 17:04 |
| `Coletas\Historico_Aberturas\2026-09-08.json` | 370.4 | 2026-09-08 23:29 |
| `Coletas\Historico_Aberturas\2026-09-21.json` | 367.4 | 2026-09-21 19:14 |
| `Coletas\Historico_Aberturas\2026-10-19.json` | 364.0 | 2026-10-19 18:35 |
| `Coletas\Historico_Aberturas\2026-10-13.json` | 361.5 | 2026-10-13 20:05 |
| `Coletas\Historico_Aberturas\2026-09-25.json` | 349.3 | 2026-09-25 18:59 |
| `Coletas\Historico_Aberturas\2026-09-17.json` | 326.6 | 2026-09-17 17:59 |
| `Coletas\Historico_Aberturas\2026-10-01.json` | 323.9 | 2026-10-01 17:14 |
| `Coletas\Historico_Aberturas\2026-10-09.json` | 310.0 | 2026-10-09 15:55 |
| `Coletas\Historico_Aberturas\2026-09-24.json` | 294.7 | 2026-09-24 15:09 |
| `Imagens\SpikeIAGrande.jpg` | 260.6 | 2026-08-01 22:00 |
| `Coletas\cache\candles_WINZ26_5m.json` | 255.5 | 2026-10-20 23:15 |
| `Coletas\Historico_Aberturas\2026-10-08.json` | 251.7 | 2026-10-08 16:35 |
| `auditoria\relatorio_mapeamento.md` | 233.1 | 2026-10-08 08:09 |
| `Coletas\Historico_Aberturas\2026-09-28.json` | 232.7 | 2026-09-28 15:04 |
| `Coletas\WIN_15min.png` | 216.5 | 2026-10-20 10:40 |
| `Coletas\WIN_1min.png` | 211.5 | 2026-09-23 08:11 |
| `Coletas\WIN_5min.png` | 206.6 | 2026-10-20 10:40 |

## 2. Integridade


✅ **154 arquivos .py compilam OK**

✅ **2191 arquivos .json parseiam OK** (26.06 MB)

## 3. Freshness dos JSONs de produção

| Arquivo | Idade | Limite | Status |
|---|---:|---:|---|
| `Decisao_V2.json` | 3m | 10m | ✅ OK |
| `DadosAtivosUnificados.json` | 3m | 10m | ✅ OK |
| `Dados_Validados.json` | 3m | 10m | ✅ OK |
| `Dados_MT5_v2_2.json` | 3m | 10m | ✅ OK |
| `Coleta_rom-0.json` | 3m | 10m | ✅ OK |
| `Coleta_ram.json` | 3m | 10m | ✅ OK |
| `Metricas_Calculadas.json` | 3m | 10m | ✅ OK |
| `Analise_Tendencias.json` | 0m | 10m | ✅ OK |
| `AnaliseGraficaSMC_Regras.json` | 3m | 15m | ✅ OK |
| `AnaliseGraficaSMC_MTF.json` | 3m | 15m | ✅ OK |
| `EstimativaAbertura.json` | 3m | 10m | ✅ OK |
| `Resultado_Calculadora_Operacional_Abertura.json` | 3m | 10m | ✅ OK |
| `Noticias_Calendario.json` | 3m | 1440m | ✅ OK |
| `Noticias_Impacto_Dia.json` | 3m | 1440m | ✅ OK |
| `config_regiao.json` | 27.5d | 525600m | ✅ OK |
| `LastTick_Congelado.json` | 3m | 525600m | ✅ OK |
| `EstimativaAbertura_Cache.json` | 2.1h | 1440m | ✅ OK |