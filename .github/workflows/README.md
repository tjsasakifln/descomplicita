# CI/CD Workflows - Descomplicita POC

## 📋 Visão Geral

Este diretório contém todos os workflows de CI/CD do projeto, implementando automação completa para:

- ✅ Validação de PRs
- 🧪 Testes automatizados
- 🔒 Análise de segurança
- 📦 Deploy automático
- 🧹 Manutenção e limpeza

---

## 🔄 Workflows Ativos

### 1. **PR Validation** (`pr-validation.yml`)

**Trigger:** Quando PR é aberto/atualizado
**Objetivo:** Garantir qualidade e conformidade do PR

**Checks executados:**

- ✅ **Metadata**: Valida formato do título (Conventional Commits) e corpo do PR
- ✅ **File Changes**: Detecta arquivos sensíveis (.env) e grandes (>5MB)
- ✅ **Backend Quality**: Linting (Ruff), formatação, type checking (mypy), syntax
- ✅ **Frontend Quality**: Linting, type checking (TypeScript), build
- ✅ **Security**: Trivy vulnerability scan, TruffleHog secret detection
- ✅ **Documentation**: Verifica se README foi atualizado quando necessário

**Status Required:** ✅ Obrigatório para merge

**Como resolver falhas:**

```bash
# Backend formatting
cd backend
ruff format .

# Backend linting
ruff check . --fix

# Frontend linting
cd frontend
npm run lint -- --fix

# Type checking
npx tsc --noEmit
```

---

### 2. **Tests** (`tests.yml`)

**Trigger:** PR + push para master
**Objetivo:** Executar testes automatizados

**Suites de teste:**

- 🐍 **Backend Tests**: pytest com coverage (threshold: 70%)
- ⚛️ **Frontend Tests**: Jest/Vitest com coverage
- 🔗 **Integration Tests**: Testes com PostgreSQL (issue #27)
- 🌐 **E2E Tests**: Playwright (issue #27)

**Matrix:**

- Python: 3.11, 3.12
- Node.js: 20

**Coverage:** Enviado automaticamente para Codecov

**Status:** ⚠️ Parcialmente implementado (aguardando issues de teste)

---

### 3. **CodeQL Security Scan** (`codeql.yml`)

**Trigger:**

- Push para master
- PRs
- Agendado: Segunda-feira 00:00 UTC

**Análises:**

- 🐍 Python (segurança + qualidade)
- 🟨 JavaScript/TypeScript (segurança + qualidade)
- 🔍 Secret scanning (TruffleHog)
- 📦 Dependency review (em PRs)

**Alertas:** Visíveis na aba Security > Code scanning

**Status Required:** ⚠️ Recomendado (não bloqueia merge)

---

### 4. **Deploy** (`deploy.yml`)

**Trigger:**

- Push para master
- Manual (workflow_dispatch)

**Ambientes:**

- 🖥️ **Backend**: Railway (aguardando issue #31)
- 🌐 **Frontend**: Vercel (aguardando issue #31)
- 💨 **Smoke Tests**: Validação pós-deploy (issue #27)

**Secrets necessários:**

```bash
RAILWAY_TOKEN=...
VERCEL_TOKEN=...
VERCEL_ORG_ID=...
VERCEL_PROJECT_ID=...
```

**Status:** 📝 Preparado (aguardando configuração de produção)

---

### 5. **Dependabot** (`dependabot.yml`)

**Configuração:**

- 📅 Schedule: Segunda-feira 09:00
- 🔢 Limite: 5 PRs por ecosistema
- 🎯 Ecosistemas: pip, npm, github-actions

**Comportamento:**

- ✅ **Patch/Minor**: Auto-merge após checks passarem
- ⚠️ **Major**: Requer revisão manual

**Ignore list:**

- Major updates (durante POC)

---

### 6. **Dependabot Auto-merge** (`dependabot-auto-merge.yml`)

**Trigger:** PRs do Dependabot
**Ação:**

- Patch/Minor → Auto-merge com squash
- Major → Adiciona comentário de aviso

**Requisitos:** Todos os checks devem passar

---

### 7. **Cleanup** (`cleanup.yml`)

**Trigger:**

- Agendado: Domingo 00:00 UTC
- Manual (workflow_dispatch)

**Ações:**

- 🗑️ Deleta branches merged há +30 dias
- 🗑️ Deleta workflow runs antigos (+90 dias, mantém 10)

---

## 🚦 Status Badges

Adicione ao README.md principal:

```markdown
![PR Validation](https://github.com/tjsasakifln/PNCP-poc/actions/workflows/pr-validation.yml/badge.svg)
![Tests](https://github.com/tjsasakifln/PNCP-poc/actions/workflows/tests.yml/badge.svg)
![CodeQL](https://github.com/tjsasakifln/PNCP-poc/actions/workflows/codeql.yml/badge.svg)
```

---

## 🔧 Configuração Local

### Backend Development

```bash
# Install dev dependencies
cd backend
pip install ruff mypy pytest pytest-cov

# Format code
ruff format .

# Lint
ruff check . --fix

# Type check
mypy . --ignore-missing-imports

# Run tests
pytest tests/ --cov
```

### Frontend Development

```bash
# Install dependencies
cd frontend
npm install

# Lint
npm run lint -- --fix

# Type check
npx tsc --noEmit

# Run tests
npm test

# Build
npm run build
```

---

## 🎯 Workflow para Contribuidores

### 1️⃣ Criar Feature Branch

```bash
git checkout -b feature/issue-N-description
```

### 2️⃣ Implementar e Testar Localmente

```bash
# Backend
cd backend
ruff format . && ruff check .
pytest tests/

# Frontend
cd frontend
npm run lint
npm test
npm run build
```

### 3️⃣ Commit com Conventional Commits

```bash
git commit -m "feat(backend): add PNCP client"
git commit -m "fix(frontend): resolve state update issue"
git commit -m "docs: update API documentation"
```

### 4️⃣ Push e Criar PR

```bash
git push -u origin feature/issue-N-description
gh pr create --title "feat: description" --body "..."
```

### 5️⃣ Aguardar Checks

- ✅ PR Validation passa
- ✅ Tests passam
- ✅ CodeQL sem alertas críticos
- 👀 Aguardar code review

### 6️⃣ Merge Automático

Após aprovação, o merge é feito automaticamente (squash).

---

## 🚨 Troubleshooting

### ❌ PR Validation Falhou

**Erro:** "PR title must follow Conventional Commits"

```bash
# Renomear PR no GitHub UI
feat: add user authentication
fix(api): resolve rate limiting
docs: update README
```

**Erro:** "PR body must include '## Context'"

- Edite o corpo do PR no GitHub
- Adicione as seções obrigatórias (veja template)

### ❌ Tests Falhando

**Erro:** Coverage below threshold

```bash
# Adicione mais testes
pytest tests/ --cov --cov-report=term-missing

# Identifique arquivos sem cobertura
```

**Erro:** Type checking errors

```bash
# Backend
mypy . --show-error-codes

# Frontend
npx tsc --noEmit
```

### ❌ Security Scan Falhou

**Erro:** Secret detected

- Remova o secret do código
- Use .env e variáveis de ambiente
- Force push para limpar histórico (cuidado!)

```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/file" \
  --prune-empty --tag-name-filter cat -- --all
```

---

## 📊 Métricas e Monitoramento

### GitHub Actions Usage

- Verificar em: Settings > Billing > GitHub Actions
- Limite free tier: 2000 minutos/mês
- Workflow mais pesado: CodeQL (~10min)

### Otimizações Implementadas

- ✅ Caching de dependências (pip, npm)
- ✅ Matrix strategy para testes
- ✅ Conditional execution (apenas arquivos alterados)
- ✅ Continue-on-error para checks não-críticos

---

## 🔮 Próximas Melhorias

### Issue #27 (Testes E2E)

- [ ] Implementar suite completa de testes
- [ ] Configurar Playwright
- [ ] Integration tests com banco real

### Issue #31 (Deploy)

- [ ] Configurar Railway (backend)
- [ ] Configurar Vercel (frontend)
- [ ] Smoke tests pós-deploy
- [ ] Rollback automático em falha

### Futuras

- [ ] Performance testing (Lighthouse CI)
- [ ] Visual regression testing
- [ ] Terraform para IaC
- [ ] Preview deployments para PRs

---

## 📚 Referências

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Ruff Linter](https://docs.astral.sh/ruff/)
- [CodeQL](https://codeql.github.com/docs/)
- [Dependabot](https://docs.github.com/en/code-security/dependabot)

---

**Última atualização:** 2026-01-24
**Mantido por:** AIOS Master (@aios-master)
