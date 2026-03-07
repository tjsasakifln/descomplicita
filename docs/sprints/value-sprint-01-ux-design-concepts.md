# Value Sprint 01 - UX Design Concepts & Recommendations

**UX Designer:** @ux-design-expert (Uma)
**Date:** 2026-01-29
**Sprint:** Value Sprint 01 - Phase 1 (Discovery & Planning)
**Input:** Baseline Analysis (@analyst), MoSCoW Prioritization (@po)

---

## Executive Summary

Completed UX audit of Descomplicita/Descomplicita (frontend/app/page.tsx) and designed wireframe concepts for 3 MUST HAVE deliverables. Current UX score is **52/100** with critical issues in user control, memory load, efficiency, and help/documentation.

**Design Philosophy for Value Sprint:**
- **Minimize cognitive load** - Don't make users remember (fix Heuristic #6)
- **Provide clarity & control** - Users should feel in control, not confused (fix Heuristic #3)
- **Progressive disclosure** - Show help when needed, hide when mastered (fix Heuristic #10)
- **Perceived performance** - Make waiting feel faster through better feedback (fix Heuristic #1)

**Deliverables:**
1. ✅ Saved Searches & History - UI/UX patterns and wireframe
2. ✅ Performance + Visible Feedback - Loading state designs
3. ✅ Interactive Onboarding - 3-step wizard flow

---

## Current UX Audit Summary

### Strengths (Keep These)
- ✅ **Clean visual design** (Heuristic #8: 9/10) - Tailwind implementation is excellent
- ✅ **Clear terminology** (Heuristic #2: 9/10) - Brazilian Portuguese, government context understood
- ✅ **Consistent branding** (Heuristic #4: 8/10) - Descomplicita identity well-established
- ✅ **Form validation** (Heuristic #5: 5/10) - Basic validation exists, can be enhanced

### Critical Weaknesses (Must Fix)
- 🔴 **No persistence** (Heuristic #3: 2/10) - Users lose everything on refresh
- 🔴 **High memory load** (Heuristic #6: 1/10) - Must remember past searches
- 🔴 **No efficiency aids** (Heuristic #7: 2/10) - No shortcuts, no quick actions
- 🔴 **No onboarding** (Heuristic #10: 1/10) - First-time users are confused

### Medium Issues (Address if Time Permits)
- 🟡 **Generic loading feedback** (Heuristic #1: 6/10) - Exists but lacks detail
- 🟡 **Limited error recovery** (Heuristic #9: 6/10) - Errors shown but no suggested fixes

---

## 1. Saved Searches & History - UX Design

### User Need
> "I search for 'uniformes SC/PR/RS' every week. Why do I have to configure this EVERY TIME?"

### Design Goals
1. **Zero-friction recall** - Access past searches with 1 click
2. **Smart defaults** - Pre-fill with last search automatically
3. **Favorites** - Pin frequently used searches
4. **Clarity** - Understand what each saved search was

### UI Pattern: Sidebar Panel (Recommended)

**Why Sidebar:**
- Always visible (persistent UI element)
- Doesn't obscure main content
- Common pattern (Gmail, Slack, etc.)
- Mobile-friendly (collapsible)

**Alternative:** Dropdown (simpler but less discoverable)

---

#### Wireframe Concept A: Sidebar Panel

```
┌─────────────────────────────────────────────────────────────┐
│ [☰] DescompLicita Logo              [🌙] Theme   [👤] User │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────────────────────────────┐ │
│  │ 📁 HISTÓRICO │  │ Busca de Licitações                   │ │
│  │──────────────│  │                                        │ │
│  │              │  │ [Buscar por: Setor ▼]                 │ │
│  │ ⭐ Favoritos │  │                                        │ │
│  │──────────────│  │ Setor: [Vestuário e Uniformes    ▼]  │ │
│  │ 📌 Uniformes │  │                                        │ │
│  │    SC/PR/RS  │  │ Estados (UFs):                        │ │
│  │    Semanal   │  │ [SC] [PR] [RS] ... [Todos] [Limpar]  │ │
│  │    15 result.│  │                                        │ │
│  │    ───────── │  │ Datas:                                │ │
│  │              │  │ [2026-01-22] a [2026-01-29]           │ │
│  │ 🕐 Recentes  │  │                                        │ │
│  │──────────────│  │ [Buscar Licitações]                   │ │
│  │ Vestuário SP │  │                                        │ │
│  │ 28/01 - 12 r.│  └────────────────────────────────────────┘ │
│  │              │                                            │
│  │ Alimentos MG │                                            │
│  │ 27/01 - 8 r. │  [Results would appear below...]          │
│  │              │                                            │
│  │ Informática  │                                            │
│  │ RJ           │                                            │
│  │ 26/01 - 3 r. │                                            │
│  │              │                                            │
│  │ [Ver todos]  │                                            │
│  └──────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
```

**Interaction Flow:**
1. User clicks saved search → Pre-fills form + auto-executes search
2. User clicks ⭐ icon on any search → Pins to "Favoritos"
3. User hovers saved search → Shows tooltip with full criteria
4. User right-clicks (or long-press mobile) → Options: Delete, Edit, Pin

**Key UI Elements:**
- **⭐ Favoritos Section** - Top 3 pinned searches (persistent)
- **🕐 Recentes Section** - Last 10 searches (auto-sorted by date)
- **Compact Card** - Shows: Icon, Name/Setor, Date, Result count
- **[Ver todos] Button** - Expands to full history modal (if >10 searches)

---

#### Wireframe Concept B: Dropdown (Alternative - Simpler)

```
┌─────────────────────────────────────────────────────────────┐
│ DescompLicita                            [🕐 Histórico ▼]    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Busca de Licitações                                         │
│                                                               │
│  Setor: [Vestuário e Uniformes ▼]                           │
│                                                               │
│  Estados (UFs): [SC] [PR] [RS] ...                           │
│  ...                                                          │
└─────────────────────────────────────────────────────────────┘

[User clicks "🕐 Histórico ▼"]

┌─────────────────────────────────────────┐
│ 🕐 Histórico de Buscas                   │
├─────────────────────────────────────────┤
│ ⭐ FAVORITOS                             │
│ ─────────────────────────────────────   │
│ 📌 Uniformes SC/PR/RS - Semanal         │
│    28/01/2026 • 15 resultados           │
│    [Buscar novamente] [⭐ Desfavoritar] │
│                                          │
│ 🕐 RECENTES                              │
│ ─────────────────────────────────────   │
│ Vestuário - SP                           │
│ 28/01/2026 • 12 resultados              │
│ [Buscar novamente] [⭐ Favoritar]       │
│                                          │
│ Alimentos e Merenda - MG                 │
│ 27/01/2026 • 8 resultados               │
│ [Buscar novamente] [⭐ Favoritar]       │
│                                          │
│ ...                                      │
│                                          │
│ [Limpar histórico]                       │
└─────────────────────────────────────────┘
```

**Pros/Cons:**
- ✅ Simpler implementation (no layout changes)
- ✅ Familiar pattern (browser history, etc.)
- ❌ Less discoverable (hidden until clicked)
- ❌ Requires click to access (sidebar is always visible)

**Recommendation:** Start with **Dropdown** for MVP (simpler), upgrade to **Sidebar** in future sprint if users love the feature.

---

### Saved Search Card - Detailed Spec

```
┌──────────────────────────────────────┐
│ 📌 Uniformes SC/PR/RS - Semanal      │  ← Title (editable on click)
│ ────────────────────────────────────  │
│ 🗓️ 28/01/2026 às 14:32              │  ← Timestamp
│ 📍 SC, PR, RS (3 estados)            │  ← UFs selected
│ 📆 22/01 a 29/01 (7 dias)            │  ← Date range
│ 📊 15 licitações encontradas         │  ← Result count
│ 💰 R$ 1.2M valor total               │  ← Total value
│                                       │
│ [🔍 Buscar novamente] [⭐] [🗑️]     │  ← Actions
└──────────────────────────────────────┘
```

**Accessibility:**
- Keyboard navigation (Tab through cards, Enter to execute)
- Screen reader labels ("Busca salva: Uniformes SC PR RS, executada em 28 de janeiro, 15 resultados")
- Focus indicators (outline on keyboard focus)
- ARIA labels for icons

---

### Mobile Responsive Design

**Mobile (<768px):**
- Sidebar collapses to hamburger menu (☰)
- Saved searches accessible via [🕐] icon in header
- Full-screen modal overlay (not dropdown)
- Swipe gestures: Swipe left on card → Delete, Swipe right → Favorite

**Tablet (768-1024px):**
- Sidebar visible but narrower (200px vs 300px desktop)
- Compact card layout

**Desktop (>1024px):**
- Full sidebar (300px)
- Hover effects (preview tooltip with full criteria)

---

### Edge Cases & Empty States

**Empty State (No Saved Searches):**
```
┌──────────────────────────────────────┐
│ 🕐 Histórico de Buscas                │
├──────────────────────────────────────┤
│                                       │
│        🔍                             │
│                                       │
│   Você ainda não fez buscas.          │
│                                       │
│   Suas próximas buscas aparecerão    │
│   aqui automaticamente!               │
│                                       │
│   💡 Dica: Clique em ⭐ para          │
│   favoritar buscas frequentes.       │
│                                       │
└──────────────────────────────────────┘
```

**Max Limit Reached (10 saved searches):**
- Show message: "Limite de 10 buscas atingido. Favorite as importantes (⭐) ou limpe o histórico."
- Oldest non-favorited search is auto-deleted when 11th search happens

**Search Failed (0 results):**
- Still save to history (user may want to retry with different dates)
- Mark with ⚠️ icon: "⚠️ Sem resultados"

---

### Data Schema (localStorage)

```typescript
interface SavedSearch {
  id: string;                    // UUID
  timestamp: string;             // ISO 8601
  name: string;                  // User-editable (default: setor name or termos)
  searchParams: {
    ufs: string[];
    dataInicial: string;
    dataFinal: string;
    setorId: string | null;
    termosBusca: string | null;
  };
  results: {
    totalRaw: number;
    totalFiltered: number;
    valorTotal: number;
  };
  isFavorite: boolean;
}

// localStorage key: "descomplicita_saved_searches"
// Value: SavedSearch[] (max 10 items, sorted by timestamp DESC)
```

---

## 2. Performance + Visible Feedback - Loading State Designs

### User Need
> "I clicked 'Buscar' 30 seconds ago. Is it frozen? Should I refresh? How much longer?"

### Design Goals
1. **Reduce anxiety** - Show that progress is happening
2. **Set expectations** - Accurate time estimates
3. **Educate users** - Explain what's happening behind the scenes
4. **Maintain engagement** - Keep users watching, not leaving

### Current Loading State (Inadequate)

```typescript
// page.tsx:492
{loading ? "Buscando..." : `Buscar ${searchLabel}`}
```

**Problems:**
- ❌ Generic message (no detail)
- ❌ No progress indicator (% complete)
- ❌ No time estimate (users don't know if it's 10s or 10min)
- ❌ No context (what is it doing?)

---

### Design Pattern: Multi-Stage Progress with Context

**Stages:**
1. **Iniciando busca** (0-5%) - Setting up search parameters
2. **Consultando PNCP** (5-80%) - Fetching from API (variable duration based on # of UFs)
3. **Filtrando resultados** (80-90%) - Applying keyword filters
4. **Gerando resumo** (90-95%) - LLM summary creation
5. **Preparando Excel** (95-100%) - File generation

---

#### Wireframe Concept: Enhanced Loading State

```
┌─────────────────────────────────────────────────────────────┐
│                                                               │
│  🔍 Buscando Licitações...                                   │
│                                                               │
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░  65%                  │
│                                                               │
│  📍 Processando São Paulo (5/27 estados)                     │
│                                                               │
│  ⏱️ Tempo estimado: ~45 segundos                             │
│  ✅ Já encontradas 127 licitações brutas                     │
│                                                               │
│  ─────────────────────────────────────────────────────────  │
│                                                               │
│  💡 Enquanto aguarda:                                        │
│     • Quanto mais estados, mais tempo leva                   │
│     • Filtros inteligentes eliminam resultados irrelevantes │
│     • IA gera resumo executivo automaticamente              │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Key Elements:**
1. **Progress Bar** (animated, smooth transitions)
2. **Current State** ("Processando São Paulo...")
3. **Counter** ("5/27 estados" - shows progress)
4. **Time Estimate** (dynamic, updates as states process)
5. **Early Results** ("Já encontradas 127 licitações" - builds anticipation)
6. **Educational Tips** (teaches users why it takes time)

---

#### Stage-by-Stage Breakdown

**Stage 1: Iniciando busca (0-5%)**
```
🔍 Iniciando busca...
▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░  5%

Configurando parâmetros de busca...
```
**Duration:** <1s

---

**Stage 2: Consultando PNCP (5-80%)**
```
📡 Consultando Portal Nacional...
▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░  50%

📍 Processando Paraná (12/27 estados)
⏱️ Tempo estimado: ~1 minuto
✅ Já encontradas 342 licitações brutas
```
**Duration:** 30-90s (depends on # of UFs)

**Technical Implementation:**
- Backend emits progress events: `{ state: "SP", completed: 5, total: 27, rawCount: 127 }`
- Frontend listens via WebSocket/SSE or polls `/api/buscar/progress/{jobId}`
- Progress bar updates smoothly (CSS transitions)

---

**Stage 3: Filtrando resultados (80-90%)**
```
🎯 Filtrando resultados...
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░  85%

Aplicando filtros de valor e keywords...
📊 342 brutas → 87 relevantes
```
**Duration:** 2-5s

---

**Stage 4: Gerando resumo (90-95%)**
```
🤖 Gerando resumo executivo...
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░  92%

IA analisando as melhores oportunidades...
```
**Duration:** 3-8s (LLM call)

---

**Stage 5: Preparando Excel (95-100%)**
```
📄 Preparando planilha Excel...
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░  98%

Formatando dados e gerando arquivo...
```
**Duration:** 1-2s

---

**Stage 6: Concluído (100%)**
```
✅ Busca concluída!
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  100%

87 licitações encontradas em 1m 23s
```
**Duration:** 0.5s (then transition to results)

---

### Loading Skeleton (Alternative for Slow Connections)

If WebSocket/SSE is not feasible, use **Loading Skeleton**:

```
┌─────────────────────────────────────────────────────────────┐
│  🔍 Buscando Licitações...                                   │
│                                                               │
│  ▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░  35%                          │
│  Processando estados selecionados...                         │
│                                                               │
│  ─────────────────────────────────────────────────────────  │
│                                                               │
│  📊 Prévia dos Resultados (carregando...)                   │
│                                                               │
│  ╔══════════════════════════════════════╗                   │
│  ║ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ ║  ← Skeleton card  │
│  ║ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ ║                    │
│  ╚══════════════════════════════════════╝                   │
│                                                               │
│  ╔══════════════════════════════════════╗                   │
│  ║ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ ║  ← Skeleton card  │
│  ║ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ ║                    │
│  ╚══════════════════════════════════════╝                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**When to Use:**
- Fallback if real-time progress not implemented (Phase 1 constraint)
- Mobile users on slow connections (perceived performance boost)

---

### Accessibility Considerations

**Screen Readers:**
- Live region: `<div aria-live="polite">Processando São Paulo, 5 de 27 estados</div>`
- Progress bar: `<progress value="65" max="100" aria-label="Progresso da busca: 65%">`

**Keyboard Users:**
- [Esc] key to cancel search (with confirmation dialog)
- Focus trap: Can't Tab out of loading state (prevent interaction with form)

**Motion Sensitivity:**
- `prefers-reduced-motion` CSS media query: Disable progress bar animation
- Use static dots (...) instead of spinner for motion-sensitive users

---

## 3. Interactive Onboarding - 3-Step Wizard Flow

### User Need
> "I just discovered DescompLicita. What is it? How do I use it? I'm confused."

### Design Goals
1. **Educate quickly** - Explain value in <60s
2. **Show, don't tell** - Interactive demo with real data
3. **Build confidence** - User completes first search successfully
4. **Allow skip** - Don't force experts to sit through tutorial

### Onboarding Trigger Logic

```typescript
// Check if onboarding should show
const shouldShowOnboarding = () => {
  const onboardingCompleted = localStorage.getItem('onboarding_completed');
  const searchCount = localStorage.getItem('search_count') || 0;

  // Show if: Never completed AND (first visit OR <3 searches)
  return !onboardingCompleted && searchCount < 3;
};
```

**Show Onboarding:**
- First-time visitor (no localStorage flag)
- OR: User has <3 searches AND never clicked "Skip"

**Don't Show:**
- User clicked "Skip" (respect choice)
- User completed onboarding
- User has 3+ searches (assumed proficient)

---

### Wizard Flow: 3 Steps

#### Step 1: Welcome & Value Proposition

```
┌─────────────────────────────────────────────────────────────┐
│                   MODAL (centered, full-screen overlay)       │
│                                                               │
│               🎉 Bem-vindo ao DescompLicita!                 │
│                                                               │
│  Encontre oportunidades de licitações públicas de forma      │
│  rápida e descomplicada.                                      │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                                                         │  │
│  │     [Screenshot/Illustration of search results]         │  │
│  │                                                         │  │
│  │  ✅ Busca em 27 estados simultaneamente                │  │
│  │  ✅ Filtros inteligentes eliminam ruído                │  │
│  │  ✅ Resumo executivo gerado por IA                     │  │
│  │  ✅ Export direto para Excel                           │  │
│  │                                                         │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│                                                               │
│  [Pular tutorial]          [Vamos começar! →]                │
│                                                               │
│                          • • ○  (Step 1 of 3)                │
└─────────────────────────────────────────────────────────────┘
```

**Key Elements:**
- **Headline:** Clear value prop ("encontre oportunidades")
- **Visual:** Screenshot or illustration (build trust)
- **Benefits:** Bullet list (scan-friendly)
- **CTA:** Primary button ("Vamos começar!"), secondary link ("Pular")
- **Progress Dots:** Show 3-step flow (set expectations)

**Interaction:**
- Click "Vamos começar!" → Step 2
- Click "Pular tutorial" → Close modal, set `onboarding_skipped: true`

---

#### Step 2: Interactive Demo (Most Important!)

```
┌─────────────────────────────────────────────────────────────┐
│                   MODAL (full-screen overlay)                 │
│                                                               │
│               📚 Vamos fazer uma busca exemplo                │
│                                                               │
│  Vou buscar licitações de Vestuário nos estados do Sul       │
│  nos últimos 7 dias. Observe os resultados!                  │
│                                                               │
│  ─────────────────────────────────────────────────────────  │
│                                                               │
│  🎯 Setor: Vestuário e Uniformes                             │
│  📍 Estados: [SC] [PR] [RS]              ← Highlighted       │
│  📆 Período: 22/01/2026 a 29/01/2026                         │
│                                                               │
│  [🔍 Executar Busca Exemplo]              ← Pulsing button   │
│                                                               │
│  ─────────────────────────────────────────────────────────  │
│                                                               │
│  💡 Dica: Você pode pesquisar em até 27 estados ao mesmo     │
│     tempo! Quanto mais estados, mais oportunidades.          │
│                                                               │
│                                                               │
│  [← Voltar]                            [Próximo passo →]     │
│                                                               │
│                          • ● ○  (Step 2 of 3)                │
└─────────────────────────────────────────────────────────────┘
```

**User Action Required:**
- User MUST click "Executar Busca Exemplo"
- Triggers REAL search (not fake data)
- While loading, show progress bar (teach what to expect)

**After Search Completes:**
```
┌─────────────────────────────────────────────────────────────┐
│               ✅ Busca exemplo concluída!                    │
│                                                               │
│  Veja o que encontramos:                                     │
│                                                               │
│  ╔══════════════════════════════════════════════════════╗   │
│  ║ 📊 Resumo Executivo                     ← Tooltip (1)  ║   │
│  ║                                                        ║   │
│  ║ Foram encontradas 15 licitações de vestuário nos      ║   │
│  ║ estados de SC, PR e RS, totalizando R$ 1.2 milhões.   ║   │
│  ║                                                        ║   │
│  ║ 15 licitações  •  R$ 1.2M valor total                 ║   │
│  ╚══════════════════════════════════════════════════════╝   │
│                                                               │
│  [📥 Baixar Excel (15 licitações)]        ← Tooltip (2)     │
│                                                               │
│  ─────────────────────────────────────────────────────────  │
│                                                               │
│  💡 Tooltips aparecem sobre elementos destacados:            │
│     (1) Resumo gerado por IA                                │
│     (2) Clique aqui para baixar planilha completa           │
│                                                               │
│                                                               │
│  [← Voltar]                            [Entendi! →]          │
│                                                               │
│                          • ● ○  (Step 2 of 3)                │
└─────────────────────────────────────────────────────────────┘
```

**Tooltips (Spotlight Pattern):**
- Use `Shepherd.js` or `Intro.js` for tooltip overlays
- Highlight: Summary card, Download button
- Arrows point to key UI elements
- Users can click through tooltips or skip

---

#### Step 3: Your Turn

```
┌─────────────────────────────────────────────────────────────┐
│                   MODAL (faded background, form visible)      │
│                                                               │
│               🎯 Agora é sua vez!                            │
│                                                               │
│  Faça sua primeira busca personalizada.                      │
│  Escolha os estados e setor que te interessam.               │
│                                                               │
│  ─────────────────────────────────────────────────────────  │
│                                                               │
│  [Form is now interactive - user can fill it out]            │
│                                                               │
│  Setor: [Selecione um setor ▼]           ← Arrow points here│
│                                                               │
│  Estados: [Clique nos estados desejados]  ← Arrow points here│
│                                                               │
│  ─────────────────────────────────────────────────────────  │
│                                                               │
│  💡 Dica: Comece com 3-5 estados para resultados rápidos.   │
│     Você pode adicionar mais depois!                         │
│                                                               │
│                                                               │
│  [← Voltar]         [Pular]         [Fazer minha busca!]    │
│                                                               │
│                          • • ●  (Step 3 of 3)                │
└─────────────────────────────────────────────────────────────┘
```

**User Action:**
- User fills form (setor + UFs + dates)
- Clicks "Fazer minha busca!"
- Modal closes, search executes
- **Onboarding complete!** Set `onboarding_completed: true`

**Validation:**
- If user clicks "Fazer minha busca!" without selecting UFs → Show tooltip: "Selecione pelo menos 1 estado"
- Don't allow empty search (same validation as main form)

---

### Alternative: Tooltip-Only Onboarding (Lighter Version)

If 3-step wizard is too heavy, use **Tooltip Tour** (Intro.js):

```
Step 1: Tooltip over "Setor" dropdown
┌────────────────────────────────────┐
│ 👋 Bem-vindo! Comece escolhendo    │
│    o setor que te interessa.       │
│                                     │
│    [Próximo →]                     │
└────────────────────────────────────┘
        ↓
    [Setor: Vestuário ▼]

Step 2: Tooltip over UF buttons
┌────────────────────────────────────┐
│ Selecione os estados onde você     │
│ quer buscar licitações.            │
│                                     │
│ [← Voltar]  [Próximo →]            │
└────────────────────────────────────┘
        ↓
    [SC] [PR] [RS] ...

Step 3: Tooltip over "Buscar" button
┌────────────────────────────────────┐
│ Pronto! Clique aqui para executar  │
│ sua busca. Fácil assim! 🎉         │
│                                     │
│ [← Voltar]  [Entendi!]             │
└────────────────────────────────────┘
        ↓
    [Buscar Licitações]
```

**Pros/Cons:**
- ✅ Faster to implement (library handles everything)
- ✅ Less intrusive (user sees real UI, not modal)
- ❌ Less engaging (no demo, no "aha!" moment)
- ❌ Easier to skip/ignore

**Recommendation:** Start with **3-Step Wizard** (higher impact), use Tooltip Tour if users find wizard too long.

---

### Onboarding Completion Celebration

After first successful search (from Step 3):

```
┌──────────────────────────────────────┐
│   🎉 Parabéns!                        │
│                                       │
│   Você completou sua primeira busca! │
│                                       │
│   [Ver resultados]                    │
└──────────────────────────────────────┘
```

**Toast notification** (bottom-right corner, auto-dismiss after 3s)

**First-time user badge** (optional gamification):
- Show 🏅 icon in header for 24h
- Tooltip: "Você é um novo usuário! Explore as funcionalidades."

---

### A/B Testing Recommendations (Post-Sprint)

**Test Variations:**
1. **Wizard Length:** 3 steps vs. 2 steps (combine Step 1+2)
2. **Demo Data:** Real search vs. pre-loaded fake results (faster but less authentic)
3. **Skip Placement:** Top-left vs. bottom-center (reduce skip rate?)
4. **Tone:** Formal vs. casual ("Vamos lá!" vs. "Vamos começar")

**Success Metrics:**
- Completion rate (% who finish all 3 steps)
- Time to first search (after onboarding)
- Bounce rate (do onboarding users return?)
- Feature adoption (do they use Saved Searches later?)

---

## 4. Additional UX Recommendations (Post-Sprint Enhancements)

### Quick Wins (Consider for SHOULD HAVE)

#### 4.1. Keyboard Shortcuts
**Heuristic #7 Fix: Flexibility & Efficiency**

```
[Ctrl/Cmd + K] → Open search history
[Ctrl/Cmd + Enter] → Execute search
[Ctrl/Cmd + S] → Save current search
[Esc] → Close modals/cancel loading
```

**Implementation:**
- Use `react-hotkeys-hook` library
- Show shortcut hints in tooltips ("Buscar Licitações (Ctrl+Enter)")

---

#### 4.2. Smart Auto-Complete for Custom Search Terms
**Heuristic #6 Fix: Recognition vs. Recall**

```
User types: "fard"
Dropdown suggests:
  - fardamento (common term)
  - farda (variant)
  - uniforme fardamento (combo)
```

**Implementation:**
- Build dictionary from `KEYWORDS_UNIFORMES` (backend/filter.py)
- Frontend autocomplete component
- Fuzzy matching for typos

---

#### 4.3. Empty State for Zero Results (Already Exists, Enhance It)

Current: `EmptyState` component (page.tsx:520-529)

**Enhancement:**
```
┌──────────────────────────────────────────────────────────┐
│  😔 Nenhuma licitação encontrada                          │
│                                                            │
│  Encontramos 127 licitações brutas, mas nenhuma passou   │
│  nos filtros de valor e keywords.                        │
│                                                            │
│  💡 Sugestões:                                            │
│     • Amplie o período de busca (últimos 15 dias)        │
│     • Adicione mais estados                              │
│     • Experimente termos de busca customizados           │
│     • Ajuste setor (talvez "Alimentos" tem mais results) │
│                                                            │
│  [Ajustar busca ↑]    [Limpar filtros]                   │
└──────────────────────────────────────────────────────────┘
```

---

## 5. Design System Notes

### Color Palette (From Tailwind Config)

**Primary (Brand Navy/Blue):**
- `brand-navy`: Main CTA buttons, selected states
- `brand-blue`: Links, hover states
- `brand-blue-subtle`: Backgrounds, highlights

**Semantic Colors:**
- `success`: Green for completed actions
- `warning`: Yellow for alerts (e.g., "Alerta de urgência")
- `error`: Red for errors, validation failures

**Neutrals:**
- `ink`: Primary text
- `ink-secondary`: Secondary text
- `ink-muted`: Tertiary text, placeholders
- `surface-0`: Main background
- `surface-1`: Card backgrounds
- `surface-2`: Elevated elements

### Typography

**Font Families:**
- `font-display`: Headings (likely Inter or similar)
- `font-data`: Tabular numbers (monospace for alignment)

**Sizes:**
- Headings: `text-2xl` (24px), `text-3xl` (30px)
- Body: `text-base` (16px), `text-sm` (14px)
- Small: `text-xs` (12px)

### Spacing & Layout

**Container:**
- Max width: `max-w-4xl` (896px)
- Padding: `px-4` mobile, `px-6` desktop

**Animations:**
- `animate-fade-in-up`: Staggered entry animations
- `transition-all duration-200`: Smooth state changes

---

## 6. Implementation Priorities

### Must Do (Week 1)

1. **Saved Searches - Dropdown Version** (simpler than sidebar)
   - Component: `<SearchHistoryDropdown />`
   - localStorage integration
   - "Buscar novamente" button

2. **Enhanced Loading State** (at minimum: progress bar + stage labels)
   - Component: `<EnhancedLoadingProgress />`
   - Basic stages: "Consultando PNCP... Filtrando... Concluído"
   - No WebSocket needed (use estimated progress)

3. **Onboarding Wizard - 3 Steps** (use Intro.js library)
   - Modal-based (overlay on first visit)
   - Real demo search (not fake data)
   - Skip option

### Nice to Have (Week 2 if Time Permits)

4. **Saved Searches - Sidebar Version** (upgrade from dropdown)
5. **Real-time Progress** (WebSocket/SSE for accurate state-by-state updates)
6. **Keyboard Shortcuts** (power user efficiency)

### Future Sprints

7. **Smart Auto-Complete** (for custom search terms)
8. **Tooltip Tour Alternative** (lighter onboarding)
9. **A/B Testing Framework** (measure onboarding effectiveness)

---

## 7. Accessibility Checklist (WCAG 2.1 AA Compliance)

### Perceivable
- ✅ Color contrast ≥4.5:1 for text, ≥3:1 for UI components
- ✅ Text alternatives for icons (aria-label)
- ✅ Keyboard-accessible progress indicators (aria-live regions)

### Operable
- ✅ All interactive elements keyboard-accessible (Tab, Enter, Esc)
- ✅ Focus indicators visible (outline on focus)
- ✅ No keyboard traps (can Tab out of all components)

### Understandable
- ✅ Clear labels for form inputs
- ✅ Error messages descriptive ("Selecione pelo menos 1 estado", not "Invalid")
- ✅ Consistent navigation (header always visible)

### Robust
- ✅ Semantic HTML (button, nav, main, etc.)
- ✅ ARIA roles where needed (role="progressbar", aria-live="polite")
- ✅ Screen reader tested (NVDA/JAWS for Windows, VoiceOver for Mac)

---

## 8. Handoff to @dev

### Design Assets Needed (from @ux-design-expert)

1. **High-fidelity mockups** (Figma or similar):
   - Saved Searches dropdown (desktop + mobile)
   - Loading state (all 5 stages)
   - Onboarding wizard (3 steps)

2. **Component specs** (this document serves as spec)

3. **Accessibility annotations** (ARIA labels, keyboard interactions)

4. **Interaction prototypes** (Figma prototype or video walkthrough)

### Dev Implementation Notes

**Libraries Recommended:**
- **Onboarding:** `intro.js` or `shepherd.js` (lightweight, well-documented)
- **Progress Bar:** `react-circular-progressbar` OR custom CSS
- **Tooltips:** `@radix-ui/react-tooltip` (accessible, customizable)
- **Keyboard Shortcuts:** `react-hotkeys-hook`

**Testing:**
- Unit tests: Component renders with correct props
- Integration tests: localStorage persists searches
- E2E tests: Onboarding flow completes successfully
- Accessibility tests: axe-core or Pa11y

---

## Conclusion

**UX Audit Complete:** Current score 52/100 → Target 75+ after Value Sprint

**Deliverables Ready:**
1. ✅ Saved Searches & History - UI/UX patterns defined (dropdown MVP, sidebar v2)
2. ✅ Performance + Visible Feedback - 5-stage loading design with progress bar
3. ✅ Interactive Onboarding - 3-step wizard flow (welcome, demo, your turn)

**Next Steps:**
1. **@dev:** Implement designs using specs above
2. **@qa:** Validate accessibility (WCAG 2.1 AA)
3. **@pm:** Allocate work, estimate effort
4. **@sm:** Create stories with these specs as acceptance criteria

**Success Metrics (UX-specific):**
- Time on Task (First Search): 120s → 60s (50% reduction via onboarding)
- Bounce Rate: 40% → 30% (25% reduction via onboarding + saved searches)
- User Satisfaction: NPS +15 points (better UX = happier users)

---

**Report Status:** ✅ COMPLETE
**Signed:** @ux-design-expert (Uma)
**Date:** 2026-01-29
