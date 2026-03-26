# 🤖 Job Assistant IA

Sistema web para **personalização automática de currículos e cartas de apresentação** utilizando IA local com [Ollama](https://ollama.com). Analisa descrições de vagas, compara com o seu currículo e gera documentos otimizados sem enviar dados para a nuvem.

## ✨ Funcionalidades

- 📋 Cadastro de vagas com análise de **match score** (0–100%)
- 🔍 Extração automática de **keywords** da descrição da vaga
- 📄 Geração de **currículo personalizado** via IA local
- ✉️ Geração de **cover letter** profissional via IA local
- 📊 **Swagger UI** completo em `/api/docs`
- 🔐 Autenticação JWT + upload de currículo (PDF/DOCX)
- 🟢 Status do Ollama em tempo real na interface

## 🏗️ Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.12, Flask 3, Flask-RESTx |
| Banco de Dados | SQLite (padrão) ou MySQL |
| Autenticação | Flask-JWT-Extended |
| Frontend | Jinja2, Bootstrap 5, Vanilla JS |
| IA Local | Ollama (llama3, mistral, gemma:2b) |
| Arquivos | PyPDF2, python-docx |

---

## 🐧 Instalação no Linux

### Pré-requisitos

```bash
# Python 3.10+
sudo apt update && sudo apt install python3 python3-venv python3-pip -y

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

### 1. Clone e configure

```bash
git clone <url-do-repositorio>
cd integracao_cv

# Crie o arquivo de configuração
cp .env.example .env
nano .env   # edite se necessário (padrão usa SQLite, não precisa de MySQL)
```

### 2. Crie o ambiente virtual e instale dependências

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Inicie o Ollama e baixe um modelo

```bash
# Terminal 1 — servidor Ollama
ollama serve

# Terminal 2 — baixe pelo menos um modelo (escolha um):
ollama pull gemma:2b    # ~1.7 GB — mais rápido
ollama pull mistral     # ~4.1 GB — equilibrado
ollama pull llama3      # ~4.7 GB — melhor qualidade
```

### 4. Rode a aplicação

```bash
# Com o virtualenv ativo:
source venv/bin/activate
python run.py
```

---

## 🪟 Instalação no Windows

### Pré-requisitos

1. **Python 3.10+** → [python.org/downloads](https://www.python.org/downloads/)  
   ⚠️ Marque **"Add Python to PATH"** durante a instalação.

2. **Ollama** → [ollama.com/download](https://ollama.com/download)  
   Baixe e instale o instalador `.exe`.

3. **Git** (opcional) → [git-scm.com](https://git-scm.com) — ou baixe o projeto como `.zip`.

### 1. Clone e configure

```cmd
:: Abra o Prompt de Comando (cmd) ou PowerShell
git clone <url-do-repositorio>
cd integracao_cv

:: Crie o .env a partir do exemplo
copy .env.example .env
notepad .env   :: edite se necessário
```

### 2. Crie o ambiente virtual e instale dependências

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

> **PowerShell:** se aparecer erro de política de execução, rode antes:  
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 3. Inicie o Ollama e baixe um modelo

```cmd
:: O Ollama inicia automaticamente como serviço no Windows após a instalação.
:: Caso não esteja rodando, abra o app "Ollama" pela barra de tarefas.

:: Baixe um modelo (em um novo terminal):
ollama pull gemma:2b
```

### 4. Rode a aplicação

```cmd
:: Com o virtualenv ativo:
venv\Scripts\activate
python run.py
```

---

## 🌐 Acessando a aplicação

Após rodar `python run.py`, acesse:

| URL | Descrição |
|-----|-----------|
| http://localhost:5000 | Interface Web |
| http://localhost:5000/api/docs | **Swagger UI** |
| http://localhost:5000/api/ollama/status | Status do Ollama (JSON) |

---

## 🗄️ Banco de Dados

### SQLite (padrão — zero configuração)

O arquivo `.env` já vem configurado para SQLite. As tabelas são criadas automaticamente na primeira execução.

```ini
DATABASE_URL=sqlite:///job_assistant.db
```

### MySQL (opcional)

```bash
# Crie o banco:
sudo mysql -e "CREATE DATABASE job_assistant CHARACTER SET utf8mb4;"

# Atualize o .env:
DATABASE_URL=mysql+pymysql://usuario:senha@localhost:3306/job_assistant
```

---

## ⚙️ Variáveis de Ambiente (`.env`)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `SECRET_KEY` | `change-this...` | Chave secreta Flask |
| `JWT_SECRET_KEY` | `change-this...` | Chave secreta JWT |
| `DATABASE_URL` | `sqlite:///job_assistant.db` | URL do banco de dados |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL do servidor Ollama |
| `OLLAMA_TIMEOUT` | `120` | Timeout em segundos para a IA |
| `OLLAMA_DEFAULT_MODEL` | `llama3` | Modelo padrão usado pela IA |
| `DEBUG` | `True` | Modo debug do Flask |

---

## 🚀 Fluxo de uso

1. **Registre-se** em `/register` e faça upload do seu currículo (PDF ou DOCX)
2. **Adicione uma vaga** colando a descrição completa
3. Clique em **"Analisar com IA"** → extrai keywords e calcula o match score
4. Clique em **"Gerar Currículo"** → currículo personalizado para a vaga
5. Clique em **"Gerar Cover Letter"** → carta de apresentação profissional
6. Acesse **Documentos** para visualizar e copiar os textos gerados

---

## 📁 Estrutura do Projeto

```
integracao_cv/
├── run.py                  # Ponto de entrada
├── config.py               # Configurações
├── extensions.py           # Extensões Flask (db, jwt, bcrypt)
├── requirements.txt
├── .env.example
├── models/
│   ├── models.py           # Entidades SQLAlchemy
│   └── repositories.py     # Camada de acesso a dados
├── services/
│   ├── ollama_client.py    # Cliente HTTP do Ollama
│   ├── ai_local_service.py # Prompts e lógica de IA
│   └── resume_processor.py # Extração de texto PDF/DOCX
├── api/
│   ├── auth_routes.py      # /api/auth (RESTx)
│   ├── job_routes.py       # /api/jobs (RESTx)
│   ├── ollama_routes.py    # /api/ollama (RESTx)
│   └── web_routes.py       # Páginas Jinja2
├── templates/              # HTML (Jinja2 + Bootstrap 5)
└── static/                 # CSS, JS, uploads
```

---

## 🛑 Encerrando a aplicação

**Linux/Mac:**
```bash
# No terminal onde está rodando, pressione:
Ctrl + C
```

**Windows:**
```cmd
:: No prompt onde está rodando, pressione:
Ctrl + C
```
