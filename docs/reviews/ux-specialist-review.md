## UX Specialist Review
**Revisor:** @ux-design-expert (Pixel)
**Data:** 2026-03-11

---

### Debitos Validados

| ID | Debito | Severidade Original | Severidade Ajustada | Horas | Prioridade | Impacto UX |
|----|--------|---------------------|---------------------|-------|------------|------------|
| TD-UX-001 | AuthModal usa tokens CSS inexistentes | Critico | **Critico** (confirmado) | 2h | P0 | **Critical** |
| TD-UX-002 | AuthModal usa classes Tailwind hardcoded | Alto | **Alto** (confirmado) | 1h | P1 | **High** |
| TD-UX-003 | ItemsList usa cores Tailwind hardcoded para badges e texto de erro | Alto | **Alto** (confirmado) | 2h | P1 | **High** |
| TD-UX-004 | Button reutilizavel existe mas nao e usado em nenhum lugar | Medio | **Medio** (confirmado) | 3h | P2 | **Medium** |
| TD-UX-005 | Pagina unica sem rota de resultados / deep-linking | Medio | **Medio** (confirmado) | 8h | P3 | **Medium** |
| TD-UX-006 | Footer duplicado entre page.tsx e termos/page.tsx | Baixo | **Baixo** (confirmado) | 1h | P3 | **Low** |
| TD-UX-007 | Versao hardcoded v2.0 no footer | Baixo | **Baixo** (confirmado) | 0.5h | P4 | **Low** |
| TD-UX-008 | rounded-modal definido no Tailwind config mas nao usado | Baixo | **Rebaixado para Trivial** | 0.5h | P4 | **Low** |
| TD-UX-009 | Sem loading state para pagina inicial (fetch setores) | Baixo | **Baixo** (confirmado) | 2h | P3 | **Low** |
| TD-UX-010 | Paginacao sem acentos nos aria-labels | Baixo | **Baixo** (confirmado) | 0.5h | P1 | **Low** |
| TD-UX-011 | SearchSummary usa inline style para badge tokens | Baixo | **Baixo** (confirmado, com ressalva) | 1h | P4 | **Low** |
| TD-UX-012 | Sem i18n framework | Baixo | **Baixo** (confirmado) | 16h | Fora POC | **Low** |
| TD-UX-013 | dateDiffInDays duplicada em page.tsx e useSearchJob.ts | Baixo | **Baixo** (confirmado) | 0.5h | P2 | **Low** |
| TD-UX-014 | Coverage frontend abaixo do ideal (branches 52.74%) | Medio | **Medio** (confirmado, merge com SYS-009) | 8h | P3 | **Medium** |
| TD-UX-015 | Setores fallback sem indicacao visual | Baixo | **Baixo** (confirmado) | 1h | P4 | **Low** |
| TD-UX-016 | SSE nao implementado (polling com backoff) | Medio | **Rebaixado para Baixo** | 12h | Fora POC | **Low** |
| TD-UX-017 | carouselData.ts nao auditado | Baixo | **Baixo** (confirmado) | 2h | P4 | **Low** |
| TD-UX-018 | Sem PWA / Service Worker | Baixo | **Baixo** (confirmado) | 8h | Fora POC | **Low** |
| TD-UX-019 | SourceBadges usa style para --ink-warning | Baixo | **Baixo** (confirmado, com ressalva) | 0.5h | P4 | **Low** |
| TD-UX-020 | Sem componente Input/Select reutilizavel | Medio | **Medio** (confirmado) | 4h | P2 | **Medium** |

---

### Validacao Detalhada por Item

#### TD-UX-001 (Critico) -- CONFIRMADO COM EVIDENCIA

Inspecionei `AuthModal.tsx` linha por linha. O componente usa **5 tokens CSS inexistentes**:

- `var(--card-bg)` -- linha 88, fundo do dialog
- `var(--text-primary)` -- linhas 88, 98, 127, 144, 161, texto principal
- `var(--text-secondary)` -- linhas 98, 119, 135, 151, 179, texto secundario
- `var(--border-color)` -- linhas 127, 144, 161, bordas dos inputs
- `var(--input-bg)` -- linhas 127, 144, 161, fundo dos inputs
- `var(--accent-color)` -- linhas 127, 144, 161, 170, 183, focus ring e botao submit

**Nenhum desses tokens existe em `globals.css`.** O resultado: em qualquer tema, o fundo do dialog, cores de texto, bordas de input, fundo de input e cor de destaque caem para valores default do browser (transparente ou preto). O modal de autenticacao e essencialmente inutilizavel visualmente em temas escuros e degradado em temas claros.

**Severidade: Critico confirmado.** Este e o debito UX mais grave do sistema. Afeta diretamente a conversao de cadastro/login.

**Mapeamento correto deveria ser:**
- `--card-bg` -> `--surface-elevated`
- `--text-primary` -> `--ink`
- `--text-secondary` -> `--ink-secondary`
- `--border-color` -> `--border`
- `--input-bg` -> `--surface-1`
- `--accent-color` -> `--brand-blue`

#### TD-UX-002 (Alto) -- CONFIRMADO

Linhas 106 e 112 do AuthModal usam `bg-red-100 dark:bg-red-900/30` e `bg-green-100 dark:bg-green-900/30`. Esses valores so respeitam light/dark. Os temas paperwhite, sepia e dim ficam com cores inconsistentes.

**Deveria usar:** `bg-error-subtle` / `text-error` e `bg-success-subtle` / `text-success` (tokens semanticos que ja existem no sistema).

#### TD-UX-003 (Alto) -- CONFIRMADO COM NUANCE

ItemsList tem dois problemas distintos:

1. **Erro de texto** (linha 118): `text-red-600 dark:text-red-400` -- deveria usar `text-error`
2. **Badges de tipo** (linhas 136-142): `bg-amber-100 text-amber-800` / `bg-blue-100 text-blue-800` -- hardcoded. O SearchSummary na mesma pagina usa `--badge-licitacao-*` e `--badge-ata-*` via inline styles. A inconsistencia e clara: o resumo mostra badges tematizados, a lista mostra badges com cores fixas.

**Estimativa de 2h e adequada.** A correcao deve espelhar o padrao do SearchSummary.

#### TD-UX-004 (Medio) -- CONFIRMADO COM EVIDENCIA AMPLIADA

O Button component em `Button.tsx` e bem implementado (variantes, tamanhos, loading state, min-height 44px). Porem, uma busca por `import.*Button` nos arquivos `.tsx` da app retornou **zero resultados**. O componente existe mas nao e usado em lugar nenhum.

Na `page.tsx`, o botao "Buscar" (linha 165-168) e os botoes de retry repetem manualmente as mesmas classes que o Button ja encapsula. Sao pelo menos 4 botoes que deveriam usar o componente.

#### TD-UX-011 e TD-UX-019 -- CONFIRMADOS COM RESSALVA

Ambos usam `style={{}}` porque os tokens (`--badge-licitacao-*`, `--badge-ata-*`, `--ink-warning`) existem em `globals.css` mas **NAO estao mapeados no `tailwind.config.ts`**. A solucao correta nao e mudar para classes arbitrarias -- e mapear esses tokens no Tailwind config. Isso e raiz unica para dois debitos.

**Recomendacao:** Resolver TD-UX-011 e TD-UX-019 juntos, mapeando tokens no Tailwind. Esforco combinado: 1h (nao 1.5h separadas).

#### TD-UX-016 -- REBAIXADO PARA BAIXO

O polling com backoff exponencial (1s a 15s) e perfeitamente aceitavel para buscas que levam 30s a 5+ minutos. O overhead de requests extras e insignificante comparado ao tempo total da operacao. SSE adicionaria complexidade de infraestrutura (proxies, load balancers, reconexao) sem beneficio perceptivel para o usuario no contexto POC. **12h de esforco para ganho marginal.**

---

### Debitos Adicionados

| ID | Debito | Severidade | Horas | Impacto UX |
|----|--------|------------|-------|------------|
| TD-UX-021 | **HighlightedText mark sem estilizacao tematica** -- O elemento mark usa estilo default do browser (fundo amarelo). Nao ha CSS para mark em globals.css, o que significa que em temas escuros (dim/dark) o contraste amarelo-sobre-escuro pode ser inadequado e visualmente discrepante. | Medio | 1h | **Medium** |
| TD-UX-022 | **Tokens CSS nao mapeados no Tailwind config** -- `--ink-warning`, `--badge-licitacao-*`, `--badge-ata-*` existem em globals.css mas nao no Tailwind. Isso forca uso de style={{}} em SearchSummary e SourceBadges. Raiz unica de TD-UX-011 e TD-UX-019. | Baixo | 1h | **Low** |
| TD-UX-023 | **Botao Buscar nao usa componente Button** -- O botao principal da app (linha 165-168 de page.tsx) replica manualmente as classes do Button component. Nao tem loading spinner integrado (mostra apenas texto "Buscando..."). O Button component ja tem loading prop com Spinner. | Medio | 0.5h | **Medium** |

---

### Debitos Removidos/Rebaixados

| ID | Acao | Justificativa |
|----|------|---------------|
| TD-UX-008 | **Rebaixado para Trivial** | `rounded-modal: 12px` esta definido no Tailwind config mas nao e usado. Ambos os modals usam `rounded-xl` (AuthModal) e `rounded-card` (SaveSearchDialog). Isso nao causa problema visual perceptivel -- ambos os modals tem border-radius consistente entre si. E um token orfao, nao um bug. Resolver junto com qualquer refatoracao de design system. |
| TD-UX-016 | **Rebaixado de Medio para Baixo** | Polling com backoff e adequado para o caso de uso (buscas longas). O ganho perceptivel de SSE e proximo de zero para o usuario. Complexidade de implementacao (12h) nao se justifica no POC. Manter como melhoria futura pos-escala. |
| TD-UX-012 | **Mantido Baixo, Fora de Escopo POC** | Sem plano de internacionalizacao no roadmap. App serve exclusivamente mercado brasileiro. Investir 16h nisto agora e desperdicio. |
| TD-UX-018 | **Mantido Baixo, Fora de Escopo POC** | PWA/offline nao faz sentido para busca de licitacoes que depende 100% de APIs online. O NetworkIndicator ja avisa quando esta offline. |

---

### Respostas ao Architect

#### 1. TD-UX-001 (AuthModal tokens) -- "Confirma que o AuthModal esta renderizando com cores default do browser?"

**Confirmado.** Inspecionei o codigo fonte do `AuthModal.tsx`. O componente usa `var(--card-bg)`, `var(--text-primary)`, `var(--text-secondary)`, `var(--border-color)`, `var(--input-bg)` e `var(--accent-color)` -- nenhum desses tokens existe em `globals.css` ou no Tailwind config. O resultado e:

- **Fundo do dialog:** transparente ou branco default do browser (dependendo do user agent)
- **Texto:** preto default (funciona em temas claros, invisivel em temas escuros)
- **Inputs:** sem fundo, sem borda visivel, sem focus ring visivel
- **Botao submit:** sem cor de fundo (transparente)

O modal e visualmente quebrado em temas escuros (dim/dark) e degradado em temas claros. Nao tenho screenshots dos 5 temas, mas a analise do codigo e conclusiva. **Prioridade maxima para correcao.**

#### 2. TD-UX-005 (Pagina unica) -- "Qual a prioridade real de deep-linking?"

**Prioridade media para o POC.** O publico-alvo (analistas de licitacoes, empresas de consultoria) tipicamente faz buscas ad-hoc e consome resultados na sessao. O compartilhamento de links de busca tem valor, mas nao e bloqueante. A busca em si demora 30s-5min, entao um link direto para resultados teria vida curta (resultados expiram no Redis).

**Recomendacao:** Postergar para pos-POC. Se implementar, considerar uma rota `/resultado/:job_id` com TTL visivel. Nao justifica 8h agora.

#### 3. TD-UX-004 + TD-UX-020 (Design System) -- "Sprint dedicado ou incremental?"

**Recomendacao: abordagem hibrida.** Um mini-sprint de 4-5h para:
1. Adotar Button nos 4-5 botoes existentes da page.tsx (0.5-1h)
2. Criar Input e Select simples, baseados no padrao do Button (2-3h)
3. Migrar os inputs do AuthModal para usar Input (1h, pode ser feito junto com TD-UX-001)

Isso evita um sprint completo mas garante que novos componentes usem o design system. Nao recomendo fazer incrementalmente porque a cada feature nova se acumula mais divida.

#### 4. TD-UX-016 (SSE vs polling) -- "O polling causa reclamacoes?"

**Nao.** O polling com backoff exponencial (1-15s) e transparente para o usuario. O LoadingProgress mostra barra de progresso, etapas completadas, grid de UFs e curiosidades educativas. O usuario esta engajado e nao percebe a latencia de atualizacao. Para buscas de 30s-5min, uma latencia de atualizacao de 1-15s e imperceptivel.

**SSE so se justificaria se houvesse reclamacoes reais ou se migrassemos para buscas sub-segundo**, o que nao e o caso. Rebaixo para Baixo / Fora de Escopo POC.

#### 5. TD-UX-012 (i18n) -- "Ha plano de internacionalizacao?"

**Nao ha no roadmap atual.** A plataforma e 100% voltada ao mercado brasileiro (licitacoes publicas brasileiras, legislacao brasileira, portais brasileiros como PNCP e Compras.gov). Nao ha caso de uso para ingles ou espanhol no horizonte previsivel.

**Decisao: Fora de escopo POC.** Se surgir demanda, o esforco sera de ~16h para extrair strings. Por ora, o custo de oportunidade nao justifica.

#### 6. TD-UX-009 (loading inicial) -- "O tempo de carga e perceptivel?"

**Marginalmente.** O fetch de setores e rapido (<500ms tipico), e o select mostra "Carregando setores..." enquanto busca. O restante do formulario (UFs, datas, termos) ja renderiza imediatamente. O impacto e um flash breve no select, nao no formulario inteiro.

**Manter como Baixo.** Se quisermos melhorar, um skeleton simples no select seria suficiente (0.5h, nao 2h). Reduzo a estimativa para 1h.

---

### Estimativa de Custos Detalhada

| Item | Horas | Impacto Visual vs Funcional | Necessita Design Review? |
|------|-------|-----------------------------|--------------------------|
| TD-UX-001 (AuthModal tokens) | 2h | **Visual critico** -- modal inutilizavel em temas escuros | Nao -- mapeamento direto para tokens existentes |
| TD-UX-002 (AuthModal hardcoded) | 1h | **Visual alto** -- feedback erro/sucesso inconsistente | Nao -- usar tokens semanticos existentes |
| TD-UX-003 (ItemsList hardcoded) | 2h | **Visual alto** -- badges e texto de erro inconsistentes | Nao -- espelhar padrao do SearchSummary |
| TD-UX-004 (Adotar Button) | 3h | **Funcional medio** -- consistencia de interacao | Nao -- componente ja existe e esta pronto |
| TD-UX-005 (Rotas de resultado) | 8h | **Funcional medio** -- deep-linking | Sim -- definir URL structure, TTL, UX de link expirado |
| TD-UX-006 (Footer component) | 1h | **Funcional baixo** -- manutencao | Nao |
| TD-UX-007 (Versao dinamica) | 0.5h | **Visual baixo** -- info desatualizada | Nao |
| TD-UX-008 (rounded-modal orfao) | 0.5h | **Nenhum** -- limpeza de config | Nao |
| TD-UX-009 (Loading inicial) | 1h (ajustado de 2h) | **Visual baixo** -- flash breve | Nao |
| TD-UX-010 (Acentos aria-labels) | 0.5h | **Acessibilidade** -- pronuncia screen reader | Nao |
| TD-UX-011 + TD-UX-019 (Inline styles) | 1h (combinados) | **Funcional baixo** -- mapear tokens no Tailwind | Nao |
| TD-UX-013 (dateDiffInDays dedup) | 0.5h | **Funcional baixo** -- risco de divergencia | Nao |
| TD-UX-014 (Coverage) | 8h | **Qualidade** -- regressoes | Nao -- merge com SYS-009 |
| TD-UX-015 (Setores fallback) | 1h | **UX baixo** -- transparencia | Nao |
| TD-UX-016 (SSE) | 12h | **Performance marginal** | Sim -- definir protocolo de reconexao |
| TD-UX-017 (carouselData audit) | 2h | **Conteudo** -- precisao informativa | Sim -- validar com especialista juridico |
| TD-UX-018 (PWA) | 8h | **Funcional** -- offline | Sim -- definir escopo offline |
| TD-UX-020 (Input/Select) | 4h | **Funcional medio** -- consistencia | Nao -- seguir padrao do Button |
| TD-UX-021 (mark estilizacao) | 1h | **Visual medio** -- contraste em temas escuros | Nao -- CSS para mark por tema |
| TD-UX-022 (Tokens no Tailwind) | 1h | **Funcional baixo** -- elimina inline styles | Nao |
| TD-UX-023 (Botao Buscar -> Button) | 0.5h | **Visual/funcional** -- spinner integrado | Nao |
| **Total ajustado** | **~48h** | | |

**Nota:** O total original era ~73.5h. Com ajustes (TD-UX-009 reduzido, TD-UX-011+019 combinados, TD-UX-016 fora de escopo POC), o esforco priorizavel para o POC cai para **~36h** (excluindo i18n, PWA, SSE).

---

### Recomendacoes de Design

#### Correcoes Visuais Imediatas (Quick Fixes -- 5h)

**1. AuthModal: migrar para tokens do design system (3h, TD-UX-001 + TD-UX-002)**

Substituicoes diretas, sem redesign necessario:

| Token atual (inexistente) | Token correto (existente) |
|---------------------------|---------------------------|
| `var(--card-bg)` | `var(--surface-elevated)` |
| `var(--text-primary)` | `var(--ink)` |
| `var(--text-secondary)` | `var(--ink-secondary)` |
| `var(--border-color)` | `var(--border)` |
| `var(--input-bg)` | `var(--surface-1)` |
| `var(--accent-color)` | `var(--brand-blue)` |
| `bg-red-100 dark:bg-red-900/30` | `bg-error-subtle text-error` |
| `bg-green-100 dark:bg-green-900/30` | `bg-success-subtle text-success` |

**2. ItemsList: alinhar com SearchSummary (2h, TD-UX-003)**

- Badges de tipo: usar `style={{}}` com `--badge-licitacao-*` e `--badge-ata-*` (mesmo padrao do SearchSummary) OU mapear no Tailwind e usar classes
- Texto de erro: `text-red-600 dark:text-red-400` -> `text-error`

#### Prioridades de Componentizacao (4-5h)

**3. Adotar Button (TD-UX-004 + TD-UX-023)**

Botoes a migrar:
- Botao "Buscar" em page.tsx (linhas 165-168) -- ganha loading spinner automatico
- Botao "Tentar novamente" em page.tsx (linhas 182-185) -- danger variant
- Botao "Tentar novamente" em ItemsList.tsx (linhas 119-124) -- secondary variant
- Botoes em SearchActions.tsx (se houver)

**4. Criar Input reutilizavel (TD-UX-020 parcial)**

Encapsular o padrao repetido nos inputs do AuthModal e SearchForm:
- Props: type, label, placeholder, error, required
- Classes base: w-full px-3 py-2 rounded-input border bg-surface-1 text-ink focus:ring-2 focus:ring-brand-blue

#### Melhorias do Design System (2h)

**5. Mapear tokens restantes no Tailwind (TD-UX-022)**

Adicionar ao tailwind.config.ts:
- `ink-warning: "var(--ink-warning)"`
- `badge-licitacao-bg/text/border`
- `badge-ata-bg/text/border`

Isso elimina a necessidade de style={{}} em SearchSummary e SourceBadges.

**6. Estilizar mark por tema (TD-UX-021)**

Adicionar em globals.css regras para mark por tema, usando `var(--brand-blue-subtle)` como fundo e `var(--ink)` como cor de texto, com padding e border-radius minimos.

---

### Analise de Acessibilidade

Ordenada por severidade de impacto:

| # | Issue | WCAG | Severidade | Status |
|---|-------|------|------------|--------|
| 1 | **AuthModal: contraste quebrado em temas escuros** (TD-UX-001) -- tokens inexistentes resultam em texto preto sobre fundo escuro | 1.4.3 (AA) | **Critico** | ABERTO |
| 2 | **AuthModal: inputs sem borda/focus visivel em temas escuros** (TD-UX-001) -- var(--border-color) e var(--accent-color) nao resolvem | 2.4.7 (AA), 1.4.11 (AA) | **Critico** | ABERTO |
| 3 | **Pagination: aria-labels sem acentos** (TD-UX-010) -- "Navegacao de paginas", "Pagina anterior", "Proxima pagina" | Boas praticas | **Baixo** | ABERTO |
| 4 | **HighlightedText: mark sem contexto para screen readers** -- A tag mark e anunciada como "highlighted text" por screen readers, sem explicar o motivo do destaque | 1.3.1 (A) | **Baixo** | ABERTO |
| 5 | **mark sem estilizacao tematica** (TD-UX-021) -- Fundo amarelo default pode ter contraste insuficiente em temas escuros | 1.4.3 (AA) | **Medio** | ABERTO |

**Pontos positivos (ja implementados):**
- Skip link funcional
- `lang="pt-BR"` correto
- Focus ring com --ring configurado
- Touch targets 44px minimo
- --ink-muted com >= 4.5:1 em todos os 5 temas
- prefers-reduced-motion respeitado
- aria-live, aria-pressed, aria-expanded, aria-current em uso adequado
- Keyboard navigation completa em ThemeToggle e SavedSearchesDropdown

---

### Recomendacoes de Ordem de Resolucao

#### Sprint 1 -- O que o usuario ve/sente imediatamente (5.5h)

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 1 | TD-UX-001 | AuthModal: corrigir tokens CSS | 2h | **Bloqueante.** Modal de auth visualmente quebrado impede cadastro/login. |
| 2 | TD-UX-002 | AuthModal: migrar feedback para tokens | 1h | Dependencia direta do anterior. Completar a correcao do AuthModal. |
| 3 | TD-UX-003 | ItemsList: migrar badges e erro para tokens | 2h | Inconsistencia visivel na pagina de resultados. |
| 4 | TD-UX-010 | Acentos nos aria-labels | 0.5h | Fix trivial, melhora acessibilidade. |

#### Sprint 2 -- O que afeta consistencia e manutencao (5.5h)

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 5 | TD-UX-023 | Botao Buscar -> componente Button | 0.5h | Quick win, ganha spinner integrado. |
| 6 | TD-UX-004 | Adotar Button nos demais botoes | 2.5h | Consistencia visual + reduce duplicacao. |
| 7 | TD-UX-021 | Estilizar mark por tema | 1h | Contraste de highlight em temas escuros. |
| 8 | TD-UX-022 | Mapear tokens restantes no Tailwind | 1h | Elimina inline styles em 2 componentes. |
| 9 | TD-UX-013 | Extrair dateDiffInDays | 0.5h | Deduplicacao trivial. |

#### Sprint 3 -- Design system e qualidade (8h)

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 10 | TD-UX-020 | Criar Input/Select reutilizavel | 4h | Completar o design system basico. |
| 11 | TD-UX-006 | Extrair Footer como componente | 1h | Deduplicacao simples. |
| 12 | TD-UX-007 | Versao dinamica no footer | 0.5h | Junto com footer refactor. |
| 13 | TD-UX-009 | Loading state pagina inicial | 1h | Polish. |
| 14 | TD-UX-015 | Indicacao de setores fallback | 1h | Transparencia para o usuario. |
| 15 | TD-UX-008 | Remover ou usar rounded-modal | 0.5h | Limpeza de config. |

#### Pos-POC (36h+)

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| -- | TD-UX-005 | Rotas de resultado | 8h | Requer design de URL, TTL, UX de expirado. |
| -- | TD-UX-014 | Coverage frontend | 8h | Melhoria continua, merge com SYS-009. |
| -- | TD-UX-016 | SSE | 12h | So se houver reclamacoes de latencia. |
| -- | TD-UX-018 | PWA | 8h | So se houver demanda offline. |
| -- | TD-UX-012 | i18n | 16h | So se houver plano de internacionalizacao. |
| -- | TD-UX-017 | Audit carouselData | 2h | Validacao de conteudo juridico. |

---

### Resumo Final

| Metrica | Valor |
|---------|-------|
| Debitos validados sem alteracao | 15/20 |
| Debitos com severidade ajustada | 2 (TD-UX-008 rebaixado, TD-UX-016 rebaixado) |
| Debitos adicionados | 3 (TD-UX-021, TD-UX-022, TD-UX-023) |
| Estimativas ajustadas | 2 (TD-UX-009 de 2h para 1h, TD-UX-011+019 combinados) |
| Esforco total para POC (Sprints 1-3) | **~19h** |
| Esforco pos-POC | **~54h** |
| Item mais critico | TD-UX-001 -- AuthModal com tokens inexistentes |
| Maior quick win | TD-UX-001 + TD-UX-002 juntos (3h, corrige auth UI completamente) |
