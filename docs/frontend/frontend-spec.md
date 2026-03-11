# Frontend Spec -- DescompLicita

> Auditoria completa do frontend Next.js 14+ App Router.
> Data: 2026-03-11 | Agente: @ux-design-expert (Pixel)

---

## 1. Estrutura do Projeto

### Diretorio raiz (`frontend/`)

```
frontend/
  app/                          # App Router (Next.js 14+)
    api/                        # Route Handlers (BFF)
      buscar/
        route.ts                # POST /api/buscar (inicia job)
        status/route.ts         # GET /api/buscar/status (polling)
        result/route.ts         # GET /api/buscar/result (resultado final)
        items/route.ts          # GET /api/buscar/items (paginacao server-side)
        cancel/route.ts         # DELETE /api/buscar/cancel (cancela job)
      download/route.ts         # GET /api/download (Excel/CSV)
      setores/route.ts          # GET /api/setores (lista setores)
    components/                 # Componentes de UI
    contexts/                   # React Contexts
    hooks/                      # Hooks especificos da app
    constants/                  # Constantes (UFs, setores fallback)
    globals.css                 # Design tokens + temas CSS
    layout.tsx                  # Root layout (fontes, providers)
    page.tsx                    # Pagina principal (busca)
    error.tsx                   # Error boundary global (Sentry)
    not-found.tsx               # Pagina 404
    termos/page.tsx             # Pagina de Termos de Uso
    types.ts                    # Tipos TypeScript compartilhados
  hooks/                        # Hooks compartilhados
    useAnalytics.ts             # Mixpanel tracking
    useSavedSearches.ts         # Buscas salvas (Supabase + localStorage)
  lib/                          # Utilitarios e configs
    backendAuth.ts              # Autenticacao com backend
    savedSearches.ts            # CRUD localStorage buscas salvas
    savedSearchesServer.ts      # CRUD Supabase buscas salvas
    supabase/                   # Clients Supabase
      client.ts                 # Browser client
      server.ts                 # Server client (RSC)
      middleware.ts             # Session refresh middleware
  middleware.ts                 # Next.js middleware (session Supabase)
  public/
    theme-init.js               # FOUC prevention (inline antes do hydrate)
  __tests__/                    # Testes Jest + Playwright
  tailwind.config.ts            # Configuracao Tailwind
  jest.config.js                # Configuracao Jest
  playwright.config.ts          # Configuracao Playwright
  tsconfig.json                 # TypeScript config
  package.json                  # Dependencias
```

### Rotas

| Rota | Arquivo | Tipo | Descricao |
|------|---------|------|-----------|
| `/` | `app/page.tsx` | Client Component | Pagina principal de busca |
| `/termos` | `app/termos/page.tsx` | Server Component | Termos de Uso |
| `/api/buscar` | `app/api/buscar/route.ts` | Route Handler | Inicia job de busca |
| `/api/buscar/status` | `app/api/buscar/status/route.ts` | Route Handler | Polling de progresso |
| `/api/buscar/result` | `app/api/buscar/result/route.ts` | Route Handler | Resultado final |
| `/api/buscar/items` | `app/api/buscar/items/route.ts` | Route Handler | Paginacao de itens |
| `/api/buscar/cancel` | `app/api/buscar/cancel/route.ts` | Route Handler | Cancelamento |
| `/api/download` | `app/api/download/route.ts` | Route Handler | Download Excel/CSV |
| `/api/setores` | `app/api/setores/route.ts` | Route Handler | Lista de setores |

---

## 2. Inventario de Componentes

### 2.1. Componentes de Layout/Estrutura

| Componente | Arquivo | Reutilizavel | Descricao |
|------------|---------|--------------|-----------|
| `RootLayout` | `app/layout.tsx` | Nao | Layout raiz: fontes Google (DM Sans, Fahkwang, DM Mono), providers, skip-link |
| `SearchHeader` | `components/SearchHeader.tsx` | Nao | Header fixo com logo, dropdown buscas salvas, theme toggle |
| `ErrorBoundary` | `components/ErrorBoundary.tsx` | **Sim** | Class component React, fallback customizavel, callback `onError` |

### 2.2. Componentes de Formulario

| Componente | Arquivo | Reutilizavel | Descricao |
|------------|---------|--------------|-----------|
| `SearchForm` | `components/SearchForm.tsx` | Nao | Toggle setor/termos, select de setores, input de termos com chips |
| `UfSelector` | `components/UfSelector.tsx` | Nao | Grid de botoes UF (27 estados), selecao por regiao |
| `RegionSelector` | `components/RegionSelector.tsx` | Nao | Botoes por regiao (Norte, Nordeste, etc.) com estado parcial |
| `DateRangeSelector` | `components/DateRangeSelector.tsx` | Nao | Inputs date para periodo |
| `LargeVolumeWarning` | `components/LargeVolumeWarning.tsx` | Nao | Banner warning para >10 UFs ou >30 dias |

### 2.3. Componentes de Progresso/Loading

| Componente | Arquivo | Reutilizavel | Descricao |
|------------|---------|--------------|-----------|
| `LoadingProgress` | `components/LoadingProgress.tsx` | Nao | Orquestrador de loading: barra, etapas, UFs, curiosidades, skeleton |
| `ProgressBar` | `components/loading-progress/ProgressBar.tsx` | Parcial | Barra de progresso com %, ETA, tempo decorrido |
| `UfGrid` | `components/loading-progress/UfGrid.tsx` | Nao | Grid visual de UFs completadas |
| `StageList` | `components/loading-progress/StageList.tsx` | Nao | Lista de etapas (busca, filtragem, resumo, Excel) |
| `CuriosityCarousel` | `components/loading-progress/CuriosityCarousel.tsx` | Nao | Carrossel de curiosidades sobre licitacoes |
| `SkeletonCards` | `components/loading-progress/SkeletonCards.tsx` | Parcial | Cards skeleton com shimmer |

### 2.4. Componentes de Resultados

| Componente | Arquivo | Reutilizavel | Descricao |
|------------|---------|--------------|-----------|
| `SearchSummary` | `components/SearchSummary.tsx` | Nao | Resumo executivo, metricas, badges, destaques, fontes |
| `ItemsList` | `components/ItemsList.tsx` | Nao | Lista paginada de licitacoes com fetch por pagina |
| `Pagination` | `components/Pagination.tsx` | **Sim** | Navegacao de paginas com ellipsis, aria labels |
| `HighlightedText` | `components/HighlightedText.tsx` | **Sim** | Highlight de keywords com NFD accent stripping |
| `SourceBadges` | `components/SourceBadges.tsx` | Nao | Badges expandiveis de fontes (PNCP, Compras.gov, etc.) |
| `EmptyState` | `components/EmptyState.tsx` | Nao | Estado vazio com breakdown de rejeicoes e sugestoes |
| `SearchActions` | `components/SearchActions.tsx` | Nao | Botoes de download Excel/CSV e salvar busca |

### 2.5. Componentes Reutilizaveis (Design System)

| Componente | Arquivo | Props | Descricao |
|------------|---------|-------|-----------|
| `Button` | `components/Button.tsx` | `variant: primary/secondary/ghost/danger`, `size: sm/md/lg`, `loading` | Botao reutilizavel com spinner integrado |
| `Spinner` | `components/Spinner.tsx` | `size: sm/md/lg`, `className` | SVG spinner com `role="status"` e sr-only label |
| `ErrorBoundary` | `components/ErrorBoundary.tsx` | `fallback`, `onError` | Boundary com fallback padrao e customizavel |

### 2.6. Componentes de Infraestrutura

| Componente | Arquivo | Descricao |
|------------|---------|-----------|
| `ThemeProvider` | `components/ThemeProvider.tsx` | Context de tema com `data-theme` + classe `dark` |
| `ThemeToggle` | `components/ThemeToggle.tsx` | Dropdown de selecao de tema com menu ARIA |
| `AnalyticsProvider` | `components/AnalyticsProvider.tsx` | Init Mixpanel lazy, track page_load/page_exit |
| `NetworkIndicator` | `components/NetworkIndicator.tsx` | Banner offline/online com dismiss |
| `AuthModal` | `components/AuthModal.tsx` | Modal login/signup com `<dialog>` nativo |
| `SaveSearchDialog` | `components/SaveSearchDialog.tsx` | Dialog salvar busca com `<dialog>` nativo |
| `SavedSearchesDropdown` | `components/SavedSearchesDropdown.tsx` | Dropdown ARIA listbox com keyboard nav |

---

## 3. Design System

### 3.1. Sistema de Temas (5 temas)

O sistema de temas opera via CSS custom properties definidas em `globals.css`, selecionadas pelo atributo `data-theme` no `<html>`.

| Tema | `data-theme` | Classe | Canvas | Ink | Tipo |
|------|-------------|--------|--------|-----|------|
| Light | `light` (default) | -- | `#ffffff` | `#1e2d3b` | Claro |
| Paperwhite | `paperwhite` | -- | `#F5F0E8` | `#1e2d3b` | Claro (quente) |
| Sepia | `sepia` | -- | `#EDE0CC` | `#2c1810` | Claro (pergaminho) |
| Dim | `dim` | `dark` | `#2A2A2E` | `#e0e0e0` | Escuro (suave) |
| Dark | `dark` | `dark` | `#121212` | `#e0e0e0` | Escuro (profundo) |

**Implementacao:**
- `theme-init.js` (inline `beforeInteractive`): previne FOUC lendo localStorage
- `ThemeProvider`: context React com `setTheme()` que aplica `data-theme` + classe `dark`
- `globals.css`: tokens CSS via seletores `html[data-theme="..."]` e classe `.dark`
- `tailwind.config.ts`: `darkMode: "class"` para suporte ao Tailwind dark mode

### 3.2. Tokens de Cor

**Canvas & Ink (base)**
- `--canvas`: fundo principal
- `--ink`: texto principal
- `--ink-secondary`: texto secundario
- `--ink-muted`: texto desenfatizado (>= 4.5:1 WCAG AA em todos os temas)
- `--ink-faint`: texto muito sutil / placeholders

**Brand**
- `--brand-navy`: `#0a1e3f` (primaria)
- `--brand-blue`: `#116dff` (accent)
- `--brand-blue-hover`: `#0d5ad4`
- `--brand-blue-subtle`: fundo sutil azul

**Superficies**
- `--surface-0`: superficie base (= canvas)
- `--surface-1`: superficie elevada 1
- `--surface-2`: superficie elevada 2
- `--surface-elevated`: cards/modais

**Semanticos**
- `--success`, `--error`, `--warning` + variantes `*-subtle`
- `--status-{success|warning|error}-{bg|text|border|dot}`: badges e indicadores
- `--badge-licitacao-*`, `--badge-ata-*`: badges de tipo no SearchSummary
- `--ink-warning`: texto de aviso tematico
- `--cat-{legislacao|estrategia|insight|dica}-*`: categorias do carrossel

**Bordas**
- `--border`: borda sutil (`rgba(0,0,0,0.08)` light / `rgba(255,255,255,0.08)` dark)
- `--border-strong`: borda enfatizada
- `--border-accent`: borda azul accent

**Focus**
- `--ring`: cor do focus ring (`#116dff` light / `#3b8bff` dark)

### 3.3. Tipografia

| Variavel | Fonte | Uso |
|----------|-------|-----|
| `--font-body` | DM Sans | Corpo de texto, UI geral |
| `--font-display` | Fahkwang | Titulos, headings |
| `--font-data` | DM Mono | Numeros, dados tabulares, versao |

**Tamanho base:** `clamp(14px, 1vw + 10px, 16px)` com `line-height: 1.6`

Classes Tailwind: `font-body`, `font-display`, `font-data`

### 3.4. Spacing

Base 4px (Tailwind default). Escala: 1=4px, 2=8px, 3=12px, 4=16px, 6=24px, 8=32px, 16=64px.

### 3.5. Border Radius

| Token | Valor | Uso |
|-------|-------|-----|
| `rounded-input` | 4px | Inputs, selects |
| `rounded-button` | 6px | Botoes |
| `rounded-card` | 8px | Cards, containers |
| `rounded-modal` | 12px | Modais (definido mas nao usado -- dialogs usam `rounded-xl`/`rounded-card`) |

### 3.6. Animacoes

| Classe | Descricao | Duracao |
|--------|-----------|---------|
| `animate-fade-in-up` | Entrada com slide up | 0.4s ease-out |
| `animate-fade-in` | Fade simples | 0.3s ease-out |
| `animate-shimmer` | Shimmer gradient para skeletons | 1.5s infinite |
| `stagger-1` a `stagger-5` | Delays escalonados (50ms cada) | -- |

`@media (prefers-reduced-motion: reduce)` reduz todas as animacoes a 0.01ms.

---

## 4. Gerenciamento de Estado

### 4.1. Contexts

| Context | Provider | Arquivo | Descricao |
|---------|----------|---------|-----------|
| `AuthContext` | `AuthProvider` | `app/contexts/AuthContext.tsx` | User, session, loading, signUp, signIn, signOut via Supabase |
| `ThemeContext` | `ThemeProvider` | `app/components/ThemeProvider.tsx` | Tema atual, setTheme, config |

### 4.2. Hooks

| Hook | Arquivo | Escopo | Descricao |
|------|---------|--------|-----------|
| `useSearchForm` | `app/hooks/useSearchForm.ts` | App | Estado do formulario: setores, UFs, datas, modo busca, validacao |
| `useSearchJob` | `app/hooks/useSearchJob.ts` | App | Lifecycle do job: submit, polling, progresso, resultado, download |
| `useSaveDialog` | `app/hooks/useSaveDialog.ts` | App | Estado do dialog de salvar busca |
| `useSavedSearches` | `hooks/useSavedSearches.ts` | Shared | CRUD buscas salvas (Supabase server-mode + localStorage fallback) |
| `useAnalytics` | `hooks/useAnalytics.ts` | Shared | Mixpanel trackEvent, identifyUser, trackPageView |
| `useAuth` | `app/contexts/AuthContext.tsx` | App | Acesso ao AuthContext |
| `useTheme` | `app/components/ThemeProvider.tsx` | App | Acesso ao ThemeContext |

### 4.3. Fluxo de Dados

```
HomePage (page.tsx)
  |-- useSearchForm() ........ estado do formulario
  |-- useSearchJob() ......... job lifecycle + polling
  |-- useSaveDialog() ........ dialog de salvar
  |-- useSavedSearches() ..... buscas salvas
  |-- useAnalytics() ......... tracking
  |
  |-> SearchHeader (onLoadSearch, onAnalyticsEvent)
  |     |-> SavedSearchesDropdown
  |     |-> ThemeToggle
  |
  |-> SearchForm (modo, setores, termos)
  |-> UfSelector (UFs selecionadas)
  |-> DateRangeSelector (periodo)
  |-> LargeVolumeWarning (contagem UFs/dias)
  |-> Botao Buscar
  |
  |-> LoadingProgress (fase, progresso, UFs, cancel)
  |-> Error alert (retry)
  |-> SearchSummary (resultado)
  |-> ItemsList (paginacao server-side via /api/buscar/items)
  |-> SearchActions (download, salvar)
  |-> SaveSearchDialog (modal)
```

**Padrao de polling:** Exponential backoff (1s -> 1.5x -> max 15s) com timeout dinamico baseado em UFs selecionadas.

**Padrao auth:** Supabase JWT via cookies (SSR) + `@supabase/ssr`. Middleware Next.js refresh session em cada request.

---

## 5. Estilizacao

### 5.1. Tailwind Config

- **`darkMode: "class"`** -- ativado pela classe `.dark` no `<html>`
- **Cores** mapeadas para CSS custom properties (ex: `canvas: "var(--canvas)"`)
- **Fontes** via CSS variables (`--font-body`, `--font-display`, `--font-data`)
- **Border radius** semanticos: `input`, `button`, `card`, `modal`
- **Plugins:** nenhum

### 5.2. CSS Custom Properties

Definidas em `globals.css` com cascata por `data-theme`. Totalizando ~70+ tokens cobrindo:
- Canvas/Ink (5), Brand (4), Surfaces (4), Semantic (6)
- Status badges (12), Source badges (6), Warning ink (1)
- Borders (3), Focus (1), Category carousel (16)

### 5.3. Abordagem Responsiva

- **Mobile-first** com breakpoints Tailwind: `sm:` (640px), `md:` (768px)
- Layout max-width: `max-w-4xl` (896px) centrado com `mx-auto`
- Grid UFs: `grid-cols-5 sm:grid-cols-7 md:grid-cols-9`
- Tamanhos de texto adaptativos: `text-sm sm:text-base`, `text-2xl sm:text-3xl`
- Touch targets: `min-height: 44px` em botoes e inputs (global CSS)
- Padding responsivo: `px-4 sm:px-6`, `py-6 sm:py-8`

---

## 6. Acessibilidade

### 6.1. Conformidade WCAG

| Criterio | Status | Implementacao |
|----------|--------|---------------|
| Skip link | OK | "Pular para o conteudo principal" no layout |
| `lang="pt-BR"` | OK | Definido no `<html>` |
| Focus visible | OK | `--ring` com `outline: 2px solid` e `outline-offset: 2px` |
| Touch targets | OK | `min-height: 44px` global para botoes e inputs |
| Contraste `--ink-muted` | OK | >= 4.5:1 em todos os 5 temas |
| Reduced motion | OK | `@media (prefers-reduced-motion)` zera animacoes |
| `aria-live` regions | OK | Anuncio de resultados, progresso, warnings |
| `role="alert"` | OK | Erros de validacao, download, timeout |
| `aria-pressed` | OK | Botoes UF toggle |
| `aria-expanded` | OK | Dropdowns (ThemeToggle, SavedSearches, SourceBadges) |
| `aria-label` | OK | Botoes de icone, nav, regioes |
| `aria-current="page"` | OK | Paginacao, link ativo |
| `aria-busy` | OK | Botao de busca durante loading |
| `aria-labelledby` | OK | SaveSearchDialog via `id="save-search-dialog-title"` |
| `aria-describedby` | OK | Input termos via hint text |
| Keyboard navigation | OK | ThemeToggle (Arrow, Home, End, Escape), SavedSearches (listbox pattern) |
| Screen reader headings | OK | `<h2 class="sr-only">` para secoes invisiveis |

### 6.2. Testes de Acessibilidade

- `accessibility.test.tsx`: testes de estrutura ARIA
- `contrast-validation.test.ts`: validacao de contraste por tema
- `SavedSearchesDropdown.aria.test.tsx`: keyboard navigation
- `05-accessibility.spec.ts`: Playwright E2E com axe-core

### 6.3. Lacunas Identificadas

- `AuthModal.tsx` usa `var(--card-bg)`, `var(--text-primary)`, `var(--border-color)`, `var(--input-bg)`, `var(--accent-color)` -- tokens que **nao existem** no design system. O modal provavelmente renderiza com fallbacks do browser.
- Pagination: labels sem acentos (`"Navegacao de paginas"`, `"Pagina anterior"`, `"Proxima pagina"`) -- nao e um bug funcional mas e inconsistente com o restante em portugues.
- `HighlightedText`: `<mark>` nao tem `aria-label` ou contexto adicional para screen readers.

---

## 7. Performance

### 7.1. Bundle Optimization

| Tecnica | Implementacao |
|---------|---------------|
| Dynamic imports | `LoadingProgress`, `EmptyState`, `ItemsList`, `SaveSearchDialog` via `next/dynamic` |
| Mixpanel lazy load | `import('mixpanel-browser')` dinamico (~40KB savings) |
| Font display swap | `display: "swap"` em todas as 3 fontes Google |
| FOUC prevention | `theme-init.js` inline via `strategy="beforeInteractive"` |
| Image optimization | Logo via `next/image` com `priority` |

### 7.2. Polling Optimization

- Exponential backoff: 1s -> 1.5s -> 2.25s -> ... -> max 15s
- Reduz requests em ~60-80% vs polling fixo de 2s
- AbortController em ItemsList para cancelar requests duplicados
- Timeout dinamico baseado em UFs selecionadas

### 7.3. Caching

- Buscas salvas: Supabase primary + localStorage write-through cache
- Setores: fetch on mount com fallback para constantes locais
- Sem estrategia de cache HTTP explicita para API routes

### 7.4. Dependencias (runtime)

| Pacote | Tamanho aprox. | Uso |
|--------|----------------|-----|
| `next` | ~150KB (core) | Framework |
| `react` + `react-dom` | ~130KB | UI |
| `@supabase/ssr` + `@supabase/supabase-js` | ~50KB | Auth + DB |
| `mixpanel-browser` | ~40KB | Analytics (lazy) |
| `@sentry/nextjs` | ~60KB | Error tracking |
| `uuid` | ~5KB | IDs |

---

## 8. Padroes UX

### 8.1. Fluxo de Busca

1. Usuario seleciona modo (setor ou termos)
2. Configura UFs (grid + regioes) e periodo
3. LargeVolumeWarning aparece se >10 UFs ou >30 dias
4. Clique "Buscar" (ou Ctrl+Enter)
5. POST `/api/buscar` retorna `job_id`
6. Polling com backoff exponencial mostra progresso em tempo real
7. LoadingProgress: barra, etapas, grid UFs, curiosidades, skeleton
8. Cancelamento disponivel durante polling
9. Resultado: resumo executivo, metricas, lista paginada
10. Acoes: download Excel/CSV, salvar busca

### 8.2. Buscas Salvas

- Maximo 10 buscas
- Dual-mode: Supabase (autenticado) + localStorage (anonimo)
- Migracao automatica no primeiro login
- Dropdown com listbox ARIA, keyboard navigation
- Delete com confirmacao dupla

### 8.3. Auth Modal

- `<dialog>` nativo com `showModal()` (focus trap built-in)
- Toggle login/signup
- Supabase email/password auth
- Feedback visual para erro e sucesso

### 8.4. Error Handling

| Nivel | Componente | Estrategia |
|-------|------------|------------|
| Global | `app/error.tsx` | Sentry + botao retry |
| Secao | `ErrorBoundary` | Fallback local + retry |
| Network | `NetworkIndicator` | Banner offline dismissivel |
| Busca | `useSearchJob` | Timeout com contexto (UFs/dias), retry |
| Download | `SearchActions` | Mensagem de erro + retry |
| Paginacao | `ItemsList` | Retry por pagina, abort em flight |
| Analytics | Todo lugar | `try/catch` silencioso -- analytics nunca quebra o app |

### 8.5. Notificacoes

- Notification API: pede permissao, notifica quando busca completa em background
- `document.title` muda para "X licitacoes encontradas" quando tab inativa
- Restaura titulo ao voltar para a tab

---

## 9. Inventario de Debitos Tecnicos

### Frontend / UX

| ID | Descricao | Severidade | Esforco (h) | Impacto UX |
|----|-----------|------------|-------------|------------|
| TD-UX-001 | **AuthModal usa tokens CSS inexistentes** (`--card-bg`, `--text-primary`, `--border-color`, `--input-bg`, `--accent-color`). Esses tokens nao existem em `globals.css` nem no Tailwind config. O modal provavelmente renderiza com cores do browser default, quebrando a consistencia visual em todos os temas. | **Critico** | 2 | Modal de auth com aparencia incorreta em todos os temas nao-default. Experiencia de cadastro/login degradada. |
| TD-UX-002 | **AuthModal nao usa design tokens do sistema** -- usa classes hardcoded como `bg-red-100 dark:bg-red-900/30`, `bg-green-100 dark:bg-green-900/30` ao inves de `bg-error-subtle`, `bg-success-subtle`. Inconsistente com padrao do restante da app. | **Alto** | 1 | Cores de feedback (erro/sucesso) nao acompanham temas paperwhite/sepia/dim. |
| TD-UX-003 | **ItemsList usa cores Tailwind hardcoded** -- `text-red-600 dark:text-red-400` e badges `bg-amber-100/text-amber-800`, `bg-blue-100/text-blue-800` ao inves de tokens semanticos. | **Alto** | 2 | Cores de erro e badges de tipo nao seguem temas personalizados. Inconsistencia visual com SearchSummary que usa `--badge-licitacao-*` e `--badge-ata-*`. |
| TD-UX-004 | **Componente `Button` reutilizavel existe mas nao e usado** -- A pagina principal usa botoes inline com classes repetidas. `Button.tsx` define variantes (primary/secondary/ghost/danger) mas o botao "Buscar", botao de retry, e botoes de download nao o utilizam. | **Medio** | 3 | Duplicacao de estilos, risco de inconsistencia entre botoes. Manutencao mais dificil. |
| TD-UX-005 | **Pagina unica (SPA-like)** -- Toda a aplicacao vive em `page.tsx` como client component. O formulario, progresso, e resultados sao secoes do mesmo componente. Nao ha rota separada para resultados. | **Medio** | 8 | Nao e possivel compartilhar link de resultado. Historico do browser nao funciona. Scroll position perdida ao navegar. |
| TD-UX-006 | **Footer duplicado** -- O footer identico aparece em `page.tsx` e `termos/page.tsx` como JSX inline. Deveria ser um componente reutilizavel no layout. | **Baixo** | 1 | Manutencao duplicada. Risco de divergencia. |
| TD-UX-007 | **Versao hardcoded "v2.0"** no footer. Deveria vir de `package.json` ou env var. | **Baixo** | 0.5 | Informacao desatualizada para usuarios. |
| TD-UX-008 | **`rounded-modal: "12px"` definido mas nao usado** -- SaveSearchDialog usa `rounded-card`, AuthModal usa `rounded-xl`. O token de design para modais existe mas nenhum modal o utiliza. | **Baixo** | 0.5 | Inconsistencia de border-radius entre modais. |
| TD-UX-009 | **Sem loading state para pagina inicial** -- O fetch de setores (`/api/setores`) acontece no mount mas nao ha skeleton/placeholder para o formulario inteiro durante o carregamento. O spinner aparece apenas no select. | **Baixo** | 2 | Flash de conteudo parcial no primeiro render. |
| TD-UX-010 | **Paginacao sem acentos nos aria-labels** -- `"Navegacao de paginas"`, `"Pagina anterior"`, `"Proxima pagina"` faltam acentos. Inconsistente com o restante do app que usa acentos corretamente. | **Baixo** | 0.5 | Screen readers pronunciam incorretamente. |
| TD-UX-011 | **`SearchSummary` usa inline `style={{}}` para badge tokens** ao inves de classes Tailwind. Mistura de abordagens de estilizacao. | **Baixo** | 1 | Manutencao inconsistente. Inline styles nao beneficiam de purge/tree-shaking. |
| TD-UX-012 | **Sem i18n framework** -- Todos os textos estao hardcoded em portugues nos componentes. Nao ha separacao de strings. | **Baixo** | 16 | Caso futuro de internacionalizacao sera custoso. Para POC e aceitavel. |
| TD-UX-013 | **`dateDiffInDays` duplicada** -- Funcao identica existe em `page.tsx` e `useSearchJob.ts`. Deveria estar em um util compartilhado. | **Baixo** | 0.5 | Risco de divergencia se alterada em apenas um local. |
| TD-UX-014 | **Coverage abaixo do ideal** -- branches em 52.74%, funcoes em 59.89%. Threshold global e 50/57/65/65. Ha margem apertada. | **Medio** | 8 | Regressoes podem passar despercebidas. |
| TD-UX-015 | **Sem tratamento de erro no `/api/setores`** -- Se o fetch falha, cai em FALLBACK_SETORES silenciosamente. Nao ha indicacao visual de que os setores sao fallback. | **Baixo** | 1 | Usuario pode ver lista incompleta de setores sem saber. |
| TD-UX-016 | **SSE nao implementado** -- Comentario no codigo menciona substituir polling por Server-Sent Events. Polling com backoff funciona mas consome mais recursos. | **Medio** | 12 | Latencia de atualizacao de progresso entre 1-15s. Custo de requests desnecessarios. |
| TD-UX-017 | **`carouselData.ts` nao auditado neste spec** -- Dados de curiosidades podem conter informacoes desatualizadas sobre legislacao de licitacoes. | **Baixo** | 2 | Conteudo educacional potencialmente incorreto. |
| TD-UX-018 | **Sem PWA / Service Worker** -- App nao funciona offline. NetworkIndicator avisa mas nao ha cache de conteudo. | **Baixo** | 8 | Nenhuma funcionalidade offline. Busca impossivel sem internet. |
| TD-UX-019 | **`SourceBadges` usa `style={{}}` para `--ink-warning`** ao inves de classe Tailwind. Necessidade de prop `style` para acessar token CSS nao mapeado no Tailwind. | **Baixo** | 0.5 | Padroes mistos de estilizacao. |
| TD-UX-020 | **Nenhum componente de input reutilizavel** -- Inputs de texto, date, e select repetem classes CSS longas. Nao ha `<Input>` ou `<Select>` padronizado como existe `<Button>`. | **Medio** | 4 | ~10 inputs com classes duplicadas. Mudanca de estilo requer alteracao em multiplos locais. |

### Resumo de Severidade

| Severidade | Quantidade | Esforco total estimado |
|------------|-----------|----------------------|
| Critico | 1 | 2h |
| Alto | 2 | 3h |
| Medio | 5 | 35h |
| Baixo | 12 | 33.5h |
| **Total** | **20** | **~73.5h** |

### Prioridade sugerida (quick wins)

1. **TD-UX-001** (Critico, 2h) -- Corrigir tokens do AuthModal
2. **TD-UX-002** (Alto, 1h) -- Migrar AuthModal para tokens semanticos
3. **TD-UX-003** (Alto, 2h) -- Migrar ItemsList para tokens semanticos
4. **TD-UX-010** (Baixo, 0.5h) -- Adicionar acentos nos aria-labels
5. **TD-UX-013** (Baixo, 0.5h) -- Extrair `dateDiffInDays` para util
6. **TD-UX-006** (Baixo, 1h) -- Extrair Footer reutilizavel

---

## Apendice: Stack Tecnica

| Tecnologia | Versao | Uso |
|------------|--------|-----|
| Next.js | ^16.1.6 | Framework App Router |
| React | ^18.3.1 | UI Library |
| TypeScript | ^5.9.3 | Type safety |
| Tailwind CSS | ^3.4.19 | Utility-first CSS |
| Supabase (`@supabase/ssr` + `supabase-js`) | ^0.9.0 / ^2.99.0 | Auth + DB |
| Mixpanel | ^2.75.0 | Product analytics |
| Sentry | ^10.42.0 | Error monitoring |
| Jest + Testing Library | ^29.7.0 / ^14.1.2 | Unit/integration tests |
| Playwright + axe-core | ^1.58.2 / ^4.11.1 | E2E + accessibility |
| MSW | ^2.12.10 | API mocking |
| SWC | ^0.2.29 | Fast transpilation |
