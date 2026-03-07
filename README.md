# Descomplicita - POC v0.2

[![Backend Tests](https://github.com/tjsasakifln/PNCP-poc/actions/workflows/tests.yml/badge.svg)](https://github.com/tjsasakifln/PNCP-poc/actions/workflows/tests.yml)
[![CodeQL](https://github.com/tjsasakifln/PNCP-poc/actions/workflows/codeql.yml/badge.svg)](https://github.com/tjsasakifln/PNCP-poc/actions/workflows/codeql.yml)
[![Frontend Tests](https://github.com/tjsasakifln/PNCP-poc/actions/workflows/tests.yml/badge.svg?event=push)](https://github.com/tjsasakifln/PNCP-poc/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/Backend_Coverage-99.2%25-brightgreen)](./backend/htmlcov/index.html)
[![Coverage](https://img.shields.io/badge/Frontend_Coverage-91.5%25-brightgreen)](./frontend/coverage/index.html)

Sistema de busca e análise de licitações de uniformes do Portal Nacional de Contratações Públicas (PNCP).

## 📋 Sobre o Projeto

O **Descomplicita** é um POC (Proof of Concept) que automatiza a descoberta de oportunidades de licitações de uniformes e fardamentos através da API do PNCP (Portal Nacional de Contratações Públicas).

### Funcionalidades Principais

- ✅ **Filtragem inteligente** por estado, valor e keywords (~50 termos)
- ✅ **Geração automática de planilhas Excel** com formatação profissional
- ✅ **Resumo executivo via GPT-4.1-nano** com análise e destaques
- ✅ **Interface web responsiva** para seleção de parâmetros
- ✅ **Resiliência** - Retry logic com exponential backoff para API instável
- ✅ **Fallback offline** - Sistema funciona mesmo sem OpenAI API
- ✅ **Testes automatizados** - 99.2% coverage backend, 91.5% frontend, 25 E2E tests

## 🚀 Quick Start

### Opção 1: Docker (Recomendado)

#### Pré-requisitos
- Docker Engine 20.10+
- Docker Compose 2.0+
- OpenAI API key

#### Instalação

1. Clone o repositório:
```bash
git clone <repository-url>
cd pncp-poc
```

2. Configure variáveis de ambiente:
```bash
cp .env.example .env
# Edite .env e adicione sua OPENAI_API_KEY
```

3. Inicie os serviços com Docker Compose:
```bash
docker-compose up
```

4. Acesse os serviços:
- **Frontend**: http://localhost:3000 (Aplicação Next.js)
- **Backend API**: http://localhost:8000/docs (Swagger UI)

**📖 Guia completo de integração:** [docs/INTEGRATION.md](docs/INTEGRATION.md)

#### Testando a Aplicação

1. Abra http://localhost:3000 no navegador
2. Selecione 3 estados (ex: SC, PR, RS)
3. Use o período padrão (últimos 7 dias)
4. Clique em "🔍 Buscar Licitações de Uniformes"
5. Aguarde os resultados (5-30s)
6. Faça download do Excel gerado

**Detalhes completos:** Veja [Manual de Validação E2E](docs/INTEGRATION.md#manual-end-to-end-testing)

#### Comandos Docker Úteis

```bash
# Iniciar em background (detached)
docker-compose up -d

# Ver logs em tempo real
docker-compose logs -f

# Ver logs de um serviço específico
docker-compose logs -f backend

# Parar serviços
docker-compose down

# Rebuild após mudanças em dependências
docker-compose build --no-cache

# Ver status dos containers
docker-compose ps

# Executar comandos no container
docker-compose exec backend python -c "print('Hello from container')"
```

---

### Opção 2: Instalação Manual

#### Pré-requisitos
- Python 3.11+
- Node.js 18+
- OpenAI API key

#### Instalação

1. Clone o repositório:
```bash
git clone <repository-url>
cd pncp-poc
```

2. Configure variáveis de ambiente:
```bash
cp .env.example .env
# Edite .env e adicione sua OPENAI_API_KEY
```

3. Backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

4. Frontend:
```bash
cd frontend
npm install
npm run dev
```

5. Acesse: http://localhost:3000

## 📁 Estrutura de Diretórios

```
pncp-poc/
├── backend/                    # API Backend (FastAPI)
│   ├── main.py                # Entrypoint da aplicação FastAPI
│   ├── config.py              # Configurações e variáveis de ambiente
│   ├── pncp_client.py         # Cliente HTTP resiliente para API PNCP
│   ├── filter.py              # Motor de filtragem com keywords
│   ├── excel.py               # Gerador de planilhas Excel formatadas
│   ├── llm.py                 # Integração com GPT-4.1-nano
│   ├── schemas.py             # Modelos Pydantic para validação
│   ├── exceptions.py          # Exceções customizadas
│   ├── requirements.txt       # Dependências Python
│   ├── pyproject.toml         # Configuração pytest + coverage (70% threshold)
│   └── tests/                 # Testes automatizados (226 tests, 99.2% coverage)
│       ├── test_pncp_client.py   # 32 tests - retry, rate limiting, pagination
│       ├── test_filter.py        # 48 tests - keyword matching, normalization
│       ├── test_excel.py         # 20 tests - formatting, data integrity
│       ├── test_llm.py           # 15 tests - GPT integration, fallback
│       ├── test_main.py          # 14 tests - API endpoints
│       └── test_schemas.py       # 25 tests - Pydantic validation
│
├── frontend/                   # Interface Web (Next.js 16 + React 18)
│   ├── app/
│   │   ├── page.tsx           # Página principal (busca + resultados)
│   │   ├── layout.tsx         # Layout base da aplicação
│   │   ├── error.tsx          # Error boundary com fallback UI
│   │   ├── types.ts           # TypeScript interfaces
│   │   └── api/               # API Routes (proxy para backend)
│   │       ├── buscar/route.ts    # POST /api/buscar (search orchestration)
│   │       └── download/route.ts  # GET /api/download (Excel streaming)
│   ├── __tests__/             # Testes automatizados (94 tests, 91.5% coverage)
│   │   ├── page.test.tsx      # 44 tests - UI components, user interactions
│   │   ├── error.test.tsx     # 27 tests - error boundary, reset button
│   │   └── api/               # 23 tests - API routes, validation
│   ├── package.json           # Dependências Node.js
│   ├── jest.config.js         # Configuração Jest (60% threshold)
│   ├── tailwind.config.js     # Configuração Tailwind CSS
│   ├── tsconfig.json          # TypeScript strict mode
│   └── playwright.config.ts   # E2E testing configuration
│
├── docs/                       # Documentação
│   ├── framework/
│   │   ├── tech-stack.md      # Stack tecnológico e justificativas
│   │   ├── source-tree.md     # Estrutura de arquivos detalhada
│   │   └── coding-standards.md # Padrões de código Python/TypeScript
│   ├── INTEGRATION.md         # Guia de integração E2E (680 linhas)
│   ├── architecture/          # Decisões arquiteturais (ADRs)
│   ├── stories/               # Stories de desenvolvimento (AIOS)
│   │   └── backlog/           # Backlog gerenciado por @pm agent
│   └── qa/                    # QA reports e test plans
│
├── scripts/                   # Scripts de automação
│   └── verify-integration.sh  # Health check automatizado (238 linhas)
│
├── .aios-core/                # Framework AIOS (AI-Orchestrated Development)
│   ├── core-config.yaml       # Configuração do AIOS
│   ├── user-guide.md          # Comandos disponíveis
│   └── development/           # Agentes, tasks, workflows
│       ├── agents/            # 11 agentes (@dev, @qa, @architect, etc.)
│       ├── tasks/             # 115+ task definitions
│       └── workflows/         # 7 multi-step workflows
│
├── .claude/                   # Configurações Claude Code
│   ├── commands/              # Slash commands customizados
│   └── rules/                 # Regras de MCP usage
│
├── .github/                   # CI/CD Workflows
│   └── workflows/
│       ├── tests.yml          # Backend + Frontend + E2E tests
│       └── codeql.yml         # Security scanning + secret detection
│
├── PRD.md                     # Product Requirements Document (1900+ linhas)
├── ROADMAP.md                 # Roadmap do projeto (70.6% completo - 24/34 issues)
├── ISSUES-ROADMAP.md          # Breakdown estruturado de issues
├── CLAUDE.md                  # Instruções para Claude Code
├── .env.example               # Template de variáveis de ambiente
├── .gitignore                 # Arquivos ignorados pelo git
├── docker-compose.yml         # Orquestração de serviços (backend + frontend)
└── README.md                  # Este arquivo
```

## 📚 Documentação

- [PRD Técnico](./PRD.md) - Especificação completa (1900+ linhas)
- [Integration Guide](./docs/INTEGRATION.md) - Guia E2E de integração
- [Tech Stack](./docs/framework/tech-stack.md) - Tecnologias utilizadas
- [Source Tree](./docs/framework/source-tree.md) - Estrutura de arquivos
- [Coding Standards](./docs/framework/coding-standards.md) - Padrões de código
- [Roadmap](./ROADMAP.md) - Status do projeto e próximas issues

## 🤖 AIOS Framework

Este projeto utiliza o [AIOS Framework](https://github.com/tjsasakifln/aios-core) para desenvolvimento orquestrado por IA.

### Agentes Disponíveis

- **@dev** - Desenvolvimento e implementação
- **@qa** - Quality assurance e testes
- **@architect** - Decisões arquiteturais
- **@pm** - Gerenciamento de stories

### Comandos AIOS

```bash
# Criar nova story
/AIOS/story

# Review de código
/AIOS/review

# Gerar documentação
/AIOS/docs
```

Ver [User Guide](./.aios-core/user-guide.md) para lista completa de comandos.

## 🏗️ Arquitetura

```
┌─────────────┐
│   Next.js   │  Frontend (React + Tailwind)
└──────┬──────┘
       │ HTTP
┌──────▼──────┐
│   FastAPI   │  Backend (Python)
└──────┬──────┘
       │
       ├─────► PNCP API (Licitações)
       └─────► OpenAI API (Resumos)
```

## 📊 Fluxo de Dados

1. Usuário seleciona UFs e período
2. Backend consulta API PNCP com retry logic
3. Motor de filtragem aplica regras:
   - UF válida
   - R$ 50k - R$ 5M
   - Keywords de uniformes
   - Status aberto
4. GPT-4.1-nano gera resumo executivo
5. Excel formatado + resumo retornados

## 🧪 Testes

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

## 🚢 Deploy

### Docker Compose (Desenvolvimento)

O projeto inclui configuração completa do Docker Compose para ambiente de desenvolvimento:

**Características:**
- ✅ Hot-reload para backend (mudanças de código reiniciam automaticamente)
- ✅ Health checks para todos os serviços
- ✅ Volumes montados para desenvolvimento
- ✅ Network bridge para comunicação inter-serviços
- ✅ Variáveis de ambiente injetadas de `.env`

**Serviços:**
- `backend` - FastAPI em Python 3.11 (porta 8000)
- `frontend` - Placeholder nginx (porta 3000)

```bash
# Iniciar ambiente completo
docker-compose up -d

# Verificar saúde dos serviços
docker-compose ps

# Ver logs
docker-compose logs -f
```

### Deploy em Produção

**🌐 Live URLs:**
- **Frontend:** https://descomplicita.vercel.app _(após deploy)_
- **Backend API:** https://descomplicita-backend-production.up.railway.app _(após deploy)_
- **API Docs:** https://descomplicita-backend-production.up.railway.app/docs _(após deploy)_

**Plataformas:**
- **Frontend:** Vercel (Next.js otimizado)
- **Backend:** Railway (FastAPI containerizado)

**📖 Guia Completo:** Ver [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) para instruções passo a passo de deployment.

**Quick Deploy:**
```bash
# 1. Backend (Railway)
npm install -g @railway/cli
railway login
cd backend && railway up

# 2. Frontend (Vercel)
npm install -g vercel
cd frontend && vercel --prod
```

**💰 Custo Estimado:** $5-10/mês (Railway Hobby + Vercel Free tier)

## 📝 Variáveis de Ambiente

Configure as variáveis abaixo no arquivo `.env` (copie de `.env.example`):

```env
# === REQUIRED ===
OPENAI_API_KEY=sk-...              # Obrigatória - Get from https://platform.openai.com/api-keys

# === OPTIONAL (Backend) ===
BACKEND_PORT=8000                  # Porta do FastAPI (default: 8000)
LOG_LEVEL=INFO                     # Nível de logging: DEBUG|INFO|WARNING|ERROR
BACKEND_URL=http://localhost:8000  # URL base para frontend chamar backend

# === OPTIONAL (PNCP Client) ===
PNCP_TIMEOUT=30                    # Timeout por request em segundos (default: 30)
PNCP_MAX_RETRIES=5                 # Máximo de tentativas de retry (default: 5)
PNCP_RATE_LIMIT=100                # Delay mínimo entre requests em ms (default: 100)

# === OPTIONAL (LLM) ===
LLM_MODEL=gpt-4o-mini              # Modelo OpenAI (default: gpt-4o-mini)
LLM_TEMPERATURE=0.3                # Temperatura do modelo (0.0-2.0, default: 0.3)
LLM_MAX_TOKENS=500                 # Máximo de tokens na resposta (default: 500)
```

**Detalhes completos:** Ver [.env.example](.env.example) com documentação inline de todas as 15+ variáveis disponíveis.

---

## 🔧 Troubleshooting

### Problemas Comuns e Soluções

#### 1. Docker / Container Issues

**Problema:** `Cannot connect to the Docker daemon`
```bash
# Solução: Inicie o Docker Desktop
# Windows: Procure "Docker Desktop" no menu Iniciar
# macOS: Abra Docker.app da pasta Applications
# Linux: sudo systemctl start docker
```

**Problema:** `Error response from daemon: Conflict. The container name "/descomplicita-backend" is already in use`
```bash
# Solução: Remova containers antigos
docker-compose down
docker-compose up --build
```

**Problema:** `descomplicita-backend exited with code 137` (Out of Memory)
```bash
# Solução: Aumente memória do Docker Desktop
# Settings → Resources → Memory: aumentar para 4GB+
```

**Problema:** Serviços não ficam "healthy" após 2 minutos
```bash
# Diagnóstico: Verifique logs dos containers
docker-compose logs backend
docker-compose logs frontend

# Solução: Health check automático
bash scripts/verify-integration.sh
```

---

#### 2. Backend API Issues

**Problema:** `ImportError: No module named 'httpx'`
```bash
# Solução: Reinstale dependências
cd backend
pip install -r requirements.txt --force-reinstall
```

**Problema:** `401 Unauthorized` ou `invalid_api_key` (OpenAI)
```bash
# Solução 1: Verifique se a chave está correta
cat .env | grep OPENAI_API_KEY
# Deve exibir: OPENAI_API_KEY=sk-...

# Solução 2: Verifique se a chave tem créditos
# Acesse: https://platform.openai.com/usage

# Solução 3: Use o modo fallback (sem LLM)
# O sistema possui fallback automático - não precisa de API key para funcionar
```

**Problema:** `PNCP API timeout` ou `504 Gateway Timeout`
```bash
# Solução: Aumente o timeout (API PNCP é instável)
# No .env:
PNCP_TIMEOUT=60
PNCP_MAX_RETRIES=10
```

**Problema:** `429 Too Many Requests` (PNCP Rate Limit)
```bash
# Solução: O cliente possui rate limiting automático
# Aguarde 1 minuto e tente novamente
# O sistema respeita header Retry-After automaticamente
```

**Problema:** `No matching distributions found for openpyxl`
```bash
# Solução: Use Python 3.11+ (versão mínima suportada)
python --version  # Deve ser 3.11.0 ou superior
# Se necessário, instale Python 3.11: https://www.python.org/downloads/
```

---

#### 3. Frontend Issues

**Problema:** `Error: Cannot find module 'next'`
```bash
# Solução: Reinstale node_modules
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Problema:** `CORS policy: No 'Access-Control-Allow-Origin' header`
```bash
# Solução 1: Verifique se backend está rodando
curl http://localhost:8000/health
# Deve retornar: {"status":"healthy"}

# Solução 2: Verifique CORS no backend (main.py linhas 49-55)
# CORS já está configurado para allow_origins=["*"]
# Se problema persistir, verifique BACKEND_URL no .env
```

**Problema:** Frontend mostra "Nenhum resultado encontrado" mas backend retornou dados
```bash
# Diagnóstico: Verifique console do navegador (F12)
# Procure por erros de parse JSON ou validação de schema

# Solução: Verifique estrutura de resposta da API
curl -X POST http://localhost:8000/buscar \
  -H "Content-Type: application/json" \
  -d '{"ufs":["SC"],"data_inicial":"2026-01-01","data_final":"2026-01-31"}'
```

**Problema:** `Error: ENOENT: no such file or directory, open '.next/...'`
```bash
# Solução: Rebuild Next.js
cd frontend
rm -rf .next
npm run build
npm run dev
```

---

#### 4. Test Failures

**Problema:** `pytest: command not found`
```bash
# Solução: Ative o ambiente virtual
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Problema:** `FAILED test_pncp_integration.py` (testes de integração)
```bash
# Solução: Testes de integração requerem internet e API PNCP funcionando
# Pule estes testes com:
pytest -m "not integration"
```

**Problema:** Coverage abaixo do threshold (70% backend / 60% frontend)
```bash
# Diagnóstico: Veja relatório detalhado
cd backend && pytest --cov --cov-report=html
# Abra: backend/htmlcov/index.html no navegador

cd frontend && npm run test:coverage
# Abra: frontend/coverage/index.html no navegador

# Solução: Adicione testes para módulos não cobertos
```

---

#### 5. Excel Download Issues

**Problema:** Botão "Download Excel" não funciona ou arquivo corrupto
```bash
# Diagnóstico: Verifique cache de downloads
# Frontend usa cache in-memory com TTL de 10min

# Solução 1: Tente novamente (cache pode ter expirado)
# Solução 2: Verifique logs do backend
docker-compose logs backend | grep "download_id"

# Solução 3: Teste endpoint diretamente
curl "http://localhost:3000/api/download?id=DOWNLOAD_ID" -o test.xlsx
```

**Problema:** Excel abre com erro "formato inválido"
```bash
# Solução: Verifique se openpyxl está instalado
cd backend
python -c "import openpyxl; print(openpyxl.__version__)"
# Deve exibir versão 3.1.0+
```

---

#### 6. E2E Test Issues

**Problema:** E2E tests failing with "Timed out waiting for page"
```bash
# Solução: Garanta que ambos serviços estejam rodando
docker-compose up -d
bash scripts/verify-integration.sh  # Health check

# Execute testes E2E
cd frontend
npm run test:e2e
```

**Problema:** `Error: browserType.launch: Executable doesn't exist`
```bash
# Solução: Instale browsers do Playwright
cd frontend
npx playwright install
```

---

### Scripts Úteis de Diagnóstico

```bash
# Health check completo (recomendado)
bash scripts/verify-integration.sh

# Verificar portas ocupadas
# Windows: netstat -ano | findstr :8000
# Linux/Mac: lsof -i :8000

# Rebuild completo (limpa cache)
docker-compose down -v
docker system prune -f
docker-compose build --no-cache
docker-compose up

# Logs em tempo real de todos os serviços
docker-compose logs -f --tail=50

# Ver variáveis de ambiente carregadas
docker-compose exec backend env | grep -E "OPENAI|PNCP|LLM"
```

---

### Onde Buscar Ajuda

1. **Documentação Detalhada:**
   - [Integration Guide](./docs/INTEGRATION.md) - Troubleshooting E2E
   - [PRD.md](./PRD.md) - Especificação técnica completa

2. **Issues do GitHub:**
   - Procure issues existentes: https://github.com/tjsasakifln/PNCP-poc/issues
   - Crie nova issue se não encontrar solução

3. **Logs e Debugging:**
   ```bash
   # Backend logs estruturados
   docker-compose logs backend | grep -E "ERROR|WARNING"

   # Frontend logs (console do navegador)
   # Abra DevTools (F12) → Console
   ```

4. **Testes Automatizados:**
   - Backend: `cd backend && pytest -v`
   - Frontend: `cd frontend && npm test -- --verbose`
   - E2E: `cd frontend && npm run test:e2e`

---

## 🤝 Contribuindo

1. Crie uma branch: `git checkout -b feature/nova-feature`
2. Commit: `git commit -m "feat: adicionar nova feature"`
3. Push: `git push origin feature/nova-feature`
4. Abra um Pull Request

## 📄 Licença

MIT

## 🔗 Links Úteis

- [API PNCP](https://pncp.gov.br/api/consulta/swagger-ui/index.html)
- [AIOS Framework](https://github.com/tjsasakifln/aios-core)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js Docs](https://nextjs.org/docs)
