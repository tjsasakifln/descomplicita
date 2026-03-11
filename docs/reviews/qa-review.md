## QA Review - Technical Debt Assessment
**Revisor:** @qa (Shield)
**Data:** 2026-03-11
**Commit base:** 2a76827b (HEAD de main)
**Documentos analisados:**
- `docs/prd/technical-debt-DRAFT.md` (57 debitos, @architect Atlas)
- `docs/reviews/db-specialist-review.md` (@data-engineer Forge)
- `docs/reviews/ux-specialist-review.md` (@ux-design-expert Pixel)
- `docs/architecture/system-architecture.md` (contexto arquitetural)

---

### Gate Status: APPROVED (com condicoes)

---

### Completude do Assessment

- [x] Todas as areas do sistema foram analisadas?
- [x] Backend coberto adequadamente?
- [x] Frontend coberto adequadamente?
- [x] Database coberto adequadamente?
- [x] Seguranca analisada?
- [x] Performance analisada?
- [x] Acessibilidade analisada?
- [ ] Infraestrutura/DevOps analisada? *(parcial -- ver Gaps)*

**Comentario:** O assessment cobre as camadas criticas do sistema com profundidade adequada para um POC. Cada especialista validou seus respectivos dominios contra o codigo-fonte real (nao apenas documentacao), o que confere alta confiabilidade. A area de infraestrutura/DevOps esta coberta de forma parcial -- docker-compose desatualizado e ausencia de migration runner foram identificados, mas falta analise mais profunda dos 9 workflows de CI/CD.

---

### Gaps Identificados

**1. CI/CD Workflows (cobertura insuficiente)**

O DRAFT menciona TD-SYS-004 (testes de integracao placeholder) mas nao analisa os demais 8 workflows. Questoes nao respondidas:
- O `deploy.yml` tem rollback automatico em caso de falha?
- Os smoke tests pos-deploy verificam funcionalidade real ou apenas health check?
- O `codeql.yml` esta realmente gerando alertas?
- O `dependabot-auto-merge.yml` tem criterios de seguranca antes de auto-merge?

**Impacto para POC:** Baixo. Os workflows existem e funcionam para o fluxo basico.

**2. Observabilidade / Monitoramento**

O Sentry esta configurado em ambos os lados, mas nao ha analise sobre:
- Cobertura real de captura de erros (quais excecoes escapam?)
- Alertas configurados (alguem recebe notificacao de erros?)
- Dashboards ou metricas operacionais

**Impacto para POC:** Medio. Sem alertas, erros durante uma demo podem passar despercebidos.

**3. Variaveis de Ambiente / Seguranca de Secrets**

O system-architecture.md lista 15+ variaveis de ambiente. O assessment nao verifica:
- Se ha `.env.example` atualizado para onboarding
- Se ha risco de vazamento de secrets em logs ou respostas de API
- Se as variaveis obrigatorias sao validadas no startup (alem do safeguard de producao existente)

**Impacto para POC:** Baixo (o safeguard de producao ja cobre o caso critico).

---

### Riscos Cruzados

| Risco | Areas Afetadas | Probabilidade | Impacto | Mitigacao Sugerida |
|-------|----------------|---------------|---------|---------------------|
| **AuthModal quebrado impede demonstracao de auth** | Frontend (UX-001), Backend (auth flow), Demo | **Alta** | **Critico** | Corrigir TD-UX-001 + TD-UX-002 antes de qualquer demo (~3h) |
| **Schema drift causa falha ao recriar DB** | Database (DB-015), Infra (migrations), Onboarding | **Media** | **Alto** | Criar migracao 003 para `DEFAULT auth.uid()` e auditar schema vivo vs migracoes |
| **python-jose com CVEs + unificacao incompleta** | Backend auth (DB-014), Seguranca | **Media** | **Alto** | Completar migracao para PyJWT em `supabase_auth.py`, remover python-jose |
| **SQLite legado com possiveis dados de usuarios** | Seguranca (SYS-001/DB-016), Compliance | **Baixa** | **Alto** | Verificar conteudo, remover arquivo, adicionar ao .gitignore |
| **verify_aud desabilitado aceita tokens de outros projetos** | Auth (DB-005), Seguranca multi-tenant | **Baixa** | **Alto** | Habilitar `verify_aud=True` com `audience="authenticated"` |
| **main.py monolitico dificulta onboarding** | Manutencao (SYS-002), Velocidade de desenvolvimento | **Alta** | **Medio** | Refatorar apos linter configurado (SYS-003 -> SYS-002) |
| **Cleanup nunca executado acumula dados** | DB (DB-010), Performance futura | **Alta** | **Baixo** (POC) | GitHub Actions schedule semanal |
| **Coverage baixa (branches 52%) mascara regressoes** | Frontend (SYS-009/UX-014), Qualidade | **Media** | **Medio** | Aumentar gradualmente; nao bloqueante para POC |

---

### Consistencia entre Reviews

**Concordancia geral: ALTA.** Os tres relatorios sao consistentes em suas conclusoes principais. Nao ha contradicoes significativas.

**Pontos de concordancia unanime:**
1. TD-UX-001 (AuthModal tokens) e o debito mais critico e urgente -- todos os tres relatorios concordam
2. TD-SYS-001 (SQLite legado) e quick win de alta prioridade
3. SSE (TD-UX-016) e i18n (TD-UX-012) sao fora de escopo POC
4. A ordem de resolucao proposta no DRAFT e consistente com as recomendacoes dos especialistas

**Ajustes de severidade -- todos verificados e justificados:**

| Debito | DRAFT | Especialista | Justificativa verificada |
|--------|-------|-------------|--------------------------|
| TD-DB-001 | Media | **Alta** (@data-engineer) | Status `cancelled` vs `failed` e bug real de integridade; afeta cleanup futuro |
| TD-DB-004 | Baixa | **Removido** -> TD-DB-014 | Verificacao de codigo confirmou unificacao JWT incompleta |
| TD-DB-006 | Media | **Baixa** (@data-engineer) | Volume de POC (<3000 rows) nao justifica batching |
| TD-UX-008 | Baixo | **Trivial** (@ux-expert) | Token orfao sem impacto visual |
| TD-UX-016 | Medio | **Baixo** (@ux-expert) | Polling com backoff e adequado para buscas de 30s-5min |

**Debitos adicionados pelos especialistas (7 novos, todos validos):**

| ID | Origem | Debito | Validacao |
|----|--------|--------|-----------|
| TD-DB-014 | @data-engineer | JWT unificacao incompleta em supabase_auth.py | Verificado: `from jose import jwt` persiste |
| TD-DB-015 | @data-engineer | Schema drift: DEFAULT auth.uid() fora das migracoes | Verificado: INSERT em savedSearchesServer.ts nao envia user_id |
| TD-DB-016 | @data-engineer | SQLite fisico + aiosqlite no requirements | Complementa TD-SYS-001 com detalhes de implementacao |
| TD-DB-017 | @data-engineer | Status `cancelled` nao propagado ao DB | Verificado: API retorna "cancelled" mas DB grava "failed" |
| TD-UX-021 | @ux-expert | mark sem estilizacao tematica | Risco real em temas escuros (amarelo default) |
| TD-UX-022 | @ux-expert | Tokens CSS nao mapeados no Tailwind | Raiz unica de TD-UX-011 e TD-UX-019 |
| TD-UX-023 | @ux-expert | Botao Buscar nao usa componente Button | Verificado: Button component existe mas tem 0 usos |

**Estimativas de horas -- razoaveis e consistentes:**
- DRAFT: ~145h deduplicado -- conservador mas realista
- @data-engineer: ajustou total DB de ~14.5h para ~16h (novos debitos) -- coerente
- @ux-expert: reduziu total UX priorizavel de ~73.5h para ~36h para o POC -- pragmatico e correto
- Nenhuma estimativa individual parece grosseiramente errada (variacao maxima de ~1h)

---

### Dependencias Validadas

**Ordem de resolucao proposta: CORRETA.**

O grafo de dependencias de 4 niveis do DRAFT esta logicamente consistente. Dependencias criticas validadas:

1. **SYS-003 (linter) -> SYS-008 (hooks) -> SYS-002 (refactor main.py):** Correto. Refatorar sem linter e arriscado.
2. **UX-001 (tokens) -> UX-002 (classes):** Correto. Primeiro criar tokens, depois migrar classes.
3. **DB-014 (PyJWT) -> DB-005 (verify_aud):** Correto. Verificar audience requer lib unificada.
4. **SYS-013 (migration runner) -> DB-001 a DB-012:** Correto, com ressalva -- migracoes triviais (CHECK constraint) podem ser aplicadas via `supabase db push` sem runner formal.

**Dependencias circulares:** Nenhuma identificada.

**Itens bloqueantes nao sinalizados:** Nenhum. O DRAFT e os especialistas identificaram todos os pre-requisitos corretamente.

**Ressalva sobre TD-DB-015 (schema drift):**
O @data-engineer identificou corretamente que `DEFAULT auth.uid()` nao esta nas migracoes. Isso cria uma dependencia oculta: TD-DB-015 deve ser resolvido ANTES de qualquer recriacao do banco (inclusive para testes de integracao). Sugiro elevar TD-DB-015 para o Nivel 0 do grafo de dependencias (pode ser feito agora, sem pre-requisitos).

---

### Testes Requeridos Pos-Resolucao

| Debito | Teste Requerido | Tipo (Unit/Integration/E2E) |
|--------|-----------------|----------------------------|
| TD-UX-001 + TD-UX-002 | Snapshot tests do AuthModal nos 5 temas; verificar que nenhum token CSS `var(--*)` usado no componente e indefinido em globals.css | Unit + Visual |
| TD-UX-003 | Snapshot tests do ItemsList nos 5 temas; comparar visualmente badges com SearchSummary | Unit + Visual |
| TD-UX-004 + TD-UX-023 | Verificar que botoes migrados mantem comportamento (click handlers, disabled, loading) | Unit |
| TD-UX-021 | Verificar contraste da tag `<mark>` nos 5 temas via axe-core | E2E (Accessibility) |
| TD-DB-001 | INSERT com status invalido (ex: `status='banana'`) deve falhar com constraint violation | Integration (SQL) |
| TD-DB-005 | Autenticacao com token JWT de `aud` diferente de `"authenticated"` deve ser rejeitado | Integration |
| TD-DB-014 | Testes existentes de `supabase_auth.py` devem passar apos migracao para PyJWT; teste com token Supabase real | Integration |
| TD-DB-015 | Recriar banco a partir das migracoes e testar INSERT em `saved_searches` sem `user_id` explicito | Integration |
| TD-DB-016 / TD-SYS-001 | Verificar que nenhum import referencia `aiosqlite` ou `descomplicita.db` no codebase (grep automatizado) | Unit (CI script) |
| TD-SYS-002 | Testes existentes devem continuar passando apos refatoracao de main.py; cobertura nao deve cair | Unit + Integration |
| TD-SYS-003 | `ruff check .` deve rodar sem erros no CI apos configuracao | CI |
| TD-SYS-005 | Verificar que Supabase client nao e recriado em cada request auth (mock + assertion de chamadas) | Unit |
| TD-SYS-006 | Requests com payload invalido nos endpoints auth devem retornar 422 (Pydantic) em vez de 500 | Integration |
| TD-SYS-015 | Burst de 20 requests em `/auth/login` deve retornar 429 apos o limite | Integration |

---

### Metricas de Qualidade

**Cobertura de codigo:**

| Metrica | Atual | Meta pos-Quick Wins | Meta pos-Fase 2 |
|---------|-------|---------------------|-----------------|
| Backend coverage (total) | 70%+ | 70%+ (manter) | 75%+ |
| Frontend branches | 52.74% | 55% | 65% |
| Frontend lines | 65%+ | 65%+ (manter) | 72% |

**Seguranca:**

| Metrica | Atual | Meta |
|---------|-------|------|
| Dependencias com CVE conhecida | python-jose (CVEs ativos) | 0 apos TD-DB-014 |
| Endpoints auth sem rate limit | 3 (`/auth/*`) | 0 apos TD-SYS-015 |
| Tokens JWT sem validacao de audience | 1 (supabase_auth.py) | 0 apos TD-DB-005 |
| Arquivos legados com dados potenciais | 1 (descomplicita.db) | 0 apos TD-DB-016 |

**Acessibilidade:**

| Metrica | Atual | Meta |
|---------|-------|------|
| Violacoes WCAG AA criticas (axe-core) | AuthModal: 2 (contraste + focus) | 0 |
| Componentes com tokens CSS inexistentes | 1 (AuthModal: 6 tokens) | 0 |
| Componentes com cores Tailwind hardcoded | 2 (AuthModal + ItemsList) | 0 |

**Design system:**

| Metrica | Atual | Meta pos-Fase 2 |
|---------|-------|-----------------|
| Uso do componente Button | 0 instancias | 4-5 instancias |
| Tokens CSS orfaos (definidos mas nao usados) | 1 (rounded-modal) | 0 |
| Tokens CSS referenciados mas inexistentes | 6 (AuthModal) | 0 |

**Performance (baseline a medir):**

| Metrica | Acao |
|---------|------|
| Tempo de resposta `/auth/login` p95 | Medir, meta < 500ms |
| Tamanho do bundle JS | Monitorar via bundle-size workflow, nao regredir |
| Tempo de criacao Supabase client | Medir antes/depois de TD-SYS-005 |

---

### Riscos do POC

#### O que DEVE ser corrigido antes de qualquer demo/apresentacao

| # | Debito | Horas | Razao |
|---|--------|-------|-------|
| 1 | **TD-UX-001 + TD-UX-002** (AuthModal tokens + classes) | 3h | Modal de login/registro visualmente quebrado. Texto invisivel em temas escuros, inputs sem borda, botao submit sem cor. **Constrangimento garantido em qualquer demo que envolva autenticacao.** |
| 2 | **TD-DB-016 / TD-SYS-001** (remover SQLite legado) | 0.5h | Arquivo `.db` com dados potenciais de usuarios no repositorio. Risco reputacional se alguem inspecionar o codigo. Quick win de 30 minutos. |
| 3 | **TD-UX-003** (ItemsList cores hardcoded) | 2h | Badges de resultados com cores inconsistentes entre componentes da mesma pagina. Visivel em qualquer demo que mostre resultados. |

**Total pre-demo: ~5.5h**

#### O que pode ser deferido para pos-POC

| Debito | Razao para deferir |
|--------|-------------------|
| TD-UX-012 (i18n, 16h) | App 100% brasileiro, sem plano de internacionalizacao |
| TD-UX-018 (PWA, 8h) | Licitacoes dependem de APIs online; offline nao faz sentido |
| TD-UX-016 (SSE, 12h) | Polling funciona bem para buscas de 30s-5min; ganho imperceptivel |
| TD-UX-005 (deep-linking, 8h) | Resultados expiram no Redis; links teriam vida curta |
| TD-SYS-014 (ThreadPool monitoring, 3h) | So relevante com carga real |
| TD-SYS-024 (CHANGELOG, 2h) | Commits sao suficientes para equipe pequena |
| TD-SYS-011 (/health frontend, 2h) | Depende de politica de monitoramento |
| TD-DB-006 (cleanup em batches, 1h) | Volume de POC nao justifica |
| TD-DB-007, DB-009, DB-011 (indices/schema cosmetico) | Otimizacoes para escala futura |

#### O que poderia causar constrangimento em demo

1. **AuthModal quebrado (TD-UX-001):** Se o apresentador tentar fazer login em tema escuro, o modal sera praticamente invisivel. **Risco critico de demo.**

2. **Versao "v2.0" no footer (TD-UX-007):** Se o sistema e apresentado como v3.x, mostrar "v2.0" no rodape contradiz a narrativa. Fix trivial (0.5h).

3. **Diretorio com nome invalido na raiz (TD-SYS-018):** Se alguem abrir o repositorio, sugere descuido. Fix de 30 segundos.

4. **Badges inconsistentes em resultados (TD-UX-003):** Cores fixas de Tailwind ao lado de badges tematizados na mesma pagina. Falta de polimento visivel.

5. **Highlight amarelo default em tema escuro (TD-UX-021):** `<mark>` com fundo amarelo do browser em temas dim/dark pode parecer um bug visual.

---

### Parecer Final

**Gate Status: APPROVED (com condicoes)**

**Justificativa:**

O Technical Debt Assessment esta abrangente, bem estruturado e validado por evidencia de codigo-fonte. Os tres relatorios (DRAFT + 2 revisoes de especialistas) sao consistentes entre si, sem contradicoes materiais. Os ajustes propostos pelos especialistas sao todos justificados e melhoram a precisao do documento.

**Pontos fortes do assessment:**
- Deduplicacao cuidadosa (7 sobreposicoes identificadas, reducao de ~171h para ~145h)
- Grafo de dependencias correto e sem circularidades
- Priorizacao pragmatica para contexto POC
- Ambos os especialistas validaram contra codigo-fonte real, nao apenas documentacao
- 7 novos debitos adicionados sao todos validos e bem fundamentados
- Clusters cross-cutting (auth, qualidade, design tokens, infra) facilitam resolucao coordenada

**Condicoes para prosseguir (5 itens):**

1. **Incorporar os 7 novos debitos** (TD-DB-014 a TD-DB-017, TD-UX-021 a TD-UX-023) na versao final do documento. Representam descobertas reais feitas durante a validacao.

2. **Atualizar o grafo de dependencias** para incluir TD-DB-015 no Nivel 0 (sem pre-requisitos) e TD-DB-014 como pre-requisito de TD-DB-005.

3. **Atualizar totais:** O total efetivo deduplicado deve refletir os novos debitos e ajustes. Recalculo sugerido: ~152h (145h base + ~7h novos debitos).

4. **Marcar itens pre-demo como bloqueantes:** TD-UX-001, TD-UX-002, TD-UX-003 e TD-SYS-001/TD-DB-016 devem ser explicitamente marcados como bloqueantes para demonstracao na versao final.

5. **Remover TD-DB-004:** Substituido por TD-DB-014. Manter ambos causa confusao na contagem.

**Nota sobre o estado do projeto:**

O sistema esta em estado surpreendentemente bom para um POC. Com 1349+ testes backend, 576+ testes frontend, 5 specs E2E com axe-core, Sentry configurado em ambos os lados, CI/CD com 9 workflows, RLS habilitado em todas as tabelas, e WCAG AA validado para ink-muted em 5 temas -- a base tecnica e solida. Os debitos identificados sao gerenciaveis.

**Esforco critico resumido:**
- Pre-demo (visual/UX): ~5.5h
- Seguranca (recomendacoes @data-engineer): ~6.5h
- **Total critico: ~12h de trabalho** -- altamente viavel e deve ser priorizado.

O assessment pode prosseguir para finalizacao com as condicoes acima atendidas.

---

**Review Status:** COMPLETO
**Revisor:** @qa (Shield)
**Assinado:** 2026-03-11
