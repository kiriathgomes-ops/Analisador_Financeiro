# 📊 Analisador Financeiro - SpikeIA

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/github/stars/kiriathgomes-ops/Analisador_Financeiro)](https://github.com/kiriathgomes-ops/Analisador_Financeiro)

## 📋 Descrição

O **Analisador Financeiro - SpikeIA** é uma plataforma completa para **análise de mercado financeiro** com integração de **Inteligência Artificial**. O sistema oferece análise técnica, fundamentalista, notícias e tendências de mercado em tempo real, com uma interface interativa desenvolvida em **Streamlit**.

### 🎯 Principais Diferenciais

- **Análise SMC (Smart Money Concepts)** com IA
- **Setup de Abertura** (09h e 10h) automatizado
- **Análise de Notícias** com impacto no mercado
- **Estimativa de Abertura** de ativos
- **Dashboard interativo** com múltiplas visualizações

---

## 🚀 Funcionalidades Principais

### 📈 **Análise de Mercado**
- ✅ Análise técnica de ativos (WIN, PETR4, etc.)
- ✅ Tendências de 15 minutos
- ✅ Setup de abertura (09h e 10h)
- ✅ Calculadora operacional
- ✅ Estimativa de abertura de mercado

### 🤖 **Inteligência Artificial**
- ✅ Análise de imagens (gráficos TradingView)
- ✅ Prompts especializados (Analista SMC)
- ✅ Visão computacional para padrões de mercado
- ✅ Pipeline de decisão com IA

### 📰 **Notícias e Calendário**
- ✅ Coleta automática de notícias
- ✅ Análise de impacto no mercado
- ✅ Calendário de eventos econômicos
- ✅ Classificação de relevância

### 📊 **Dashboard Streamlit**
- ✅ Interface intuitiva e responsiva
- ✅ 10+ páginas de análise
- ✅ Visualizações interativas
- ✅ Atualização em tempo real

### 🔄 **Automação**
- ✅ Pipeline automatizado (3x ao dia)
- ✅ Geração de relatórios executivos
- ✅ Coleta programada de dados
- ✅ Logging completo

---

## 🛠️ Tecnologias Utilizadas

### **Core**
- **Python 3.8+** - Linguagem principal
- **Streamlit** - Framework de interface
- **Pandas** - Manipulação de dados
- **NumPy** - Computação numérica
- **Plotly** - Visualização interativa

### **Análise de Dados**
- **yfinance** - Dados financeiros
- **Pandas TA** - Indicadores técnicos
- **OpenAI API** - Integração com IA
- **Vision API** - Análise de imagens

### **Automação**
- **Schedule** - Agendamento de tarefas
- **Logging** - Sistema de logs
- **JSON** - Armazenamento de dados

---

## 📦 Instalação

### Pré-requisitos

- Python 3.8 ou superior
- Pip (gerenciador de pacotes)
- Git

### Passo a passo

1. **Clone o repositório**
```bash
git clone https://github.com/kiriathgomes-ops/Analisador_Financeiro.git
cd Analisador_Financeiro



Analisador_Financeiro/
│
├── 📄 app_home.py                    # Ponto de entrada do Streamlit
├── 📄 main_pipeline.py               # Pipeline principal
├── 📄 Agendador.py                   # Agendador de tarefas
├── 📄 Coletor.py                     # Coleta de dados
├── 📄 Calculadora.py                 # Cálculos financeiros
├── 📄 Validador.py                   # Validação de dados
├── 📄 Engine_Vies.py                 # Motor de decisão
│
├── 📁 pages/                         # Páginas Streamlit
│   ├── 1_🎯_Setup_Abertura_09h.py   # Setup 09h
│   ├── 3_🎯_Setup_Abertura_10h.py   # Setup 10h
│   ├── 4_🎯_Calculadora.py          # Calculadora
│   ├── 5_⚙️_Core_Engine.py         # Motor principal
│   ├── 6_Analise_Tendencia.py      # Análise de tendência
│   ├── 7_IA_Imagem.py              # IA para imagens
│   ├── 13_Noticias.py              # Notícias
│   ├── 14_🌐_Ativos_Monitorados.py # Ativos monitorados
│   └── 15_🗺️_Mapa_da_Aplicacao.py  # Mapa do projeto
│
├── 📁 Coletas/                       # Dados coletados
│   ├── DadosAtivosUnificados.json   # Dados consolidados
│   ├── EstimativaAbertura.json      # Estimativas
│   ├── Noticias_Calendario.json     # Notícias
│   ├── Pipeline_Log.json            # Logs do pipeline
│   ├── Relatorio_Executivo.md       # Relatórios
│   └── WIN_*.png                    # Gráficos TradingView
│
├── 📁 PromptIA/                      # Prompts para IA
│   ├── PromptMestre.txt             # Prompt principal
│   ├── Analista_SMC.txt             # Analista SMC
│   └── vision_prompt_config.json    # Configuração visão
│
├── 📁 Imagens/                       # Imagens do projeto
│   ├── SpikeIA.png                  # Logo
│   └── SpikeIAGrande.jpg            # Logo grande
│
├── 📄 .env                           # Variáveis de ambiente
├── 📄 .gitignore                     # Arquivos ignorados
├── 📄 requirements.txt               # Dependências
├── 📄 anotacoes.txt                  # Anotações
│
└── 📁 scripts/                       # Scripts auxiliares
    ├── rodar_tudo.bat               # Executa tudo
    ├── rodar_pipeline_3x.bat        # Pipeline 3x
    └── rodar_gerar_relatorios.bat   # Gera relatórios
