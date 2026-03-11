# Story 0.1 -- Pre-Demo: Correcoes Visuais

## Contexto

O assessment tecnico identificou que o AuthModal (modal de login/cadastro) esta visualmente quebrado em temas escuros devido a 6 tokens CSS inexistentes. Alem disso, o ItemsList usa cores Tailwind hardcoded para badges e erros, criando inconsistencia visual na mesma pagina onde o SearchSummary exibe badges tematizados corretamente. A paginacao tambem apresenta aria-labels sem acentos, e o elemento `<mark>` do HighlightedText usa amarelo padrao do browser, inadequado em temas escuros.

Estes itens sao **BLOQUEANTES** para qualquer demonstracao do produto. Um apresentador que trocar o tema durante a demo encontrara texto invisivel, botoes sem cor e campos de entrada sem borda no modal de autenticacao.

Referencia: `docs/prd/technical-debt-assessment.md` -- Secao "Pre-Demo Visual/UX"

## Objetivo

Corrigir todas as inconsistencias visuais que causariam constrangimento em uma demonstracao, garantindo que AuthModal, ItemsList e HighlightedText funcionem corretamente em todos os 5 temas.

## Tasks

- [x] **Task 1** (TD-UX-001) -- Corrigir 6 tokens CSS inexistentes no AuthModal: `--card-bg` -> `--surface-elevated`, `--text-primary` -> `--ink`, `--text-secondary` -> `--ink-secondary`, `--border-color` -> `--border`, `--input-bg` -> `--surface-1`, `--accent-color` -> `--brand-blue` -- 2h
- [x] **Task 2** (TD-UX-002) -- Migrar feedback de erro/sucesso do AuthModal de classes Tailwind hardcoded (`bg-red-100`, `bg-green-100`) para tokens semanticos (`bg-error-subtle`/`text-error`, `bg-success-subtle`/`text-success`) -- 1h
- [x] **Task 3** (TD-UX-003) -- Migrar badges do ItemsList de cores Tailwind hardcoded (`bg-amber-100`, `bg-blue-100`) para tokens `--badge-licitacao-*`/`--badge-ata-*` ja definidos; migrar texto de erro de `text-red-600` para `text-error` -- 2h
- [x] **Task 4** (TD-UX-010) -- Adicionar acentos nos aria-labels da paginacao: "Navegacao de paginas", "Pagina anterior", "Proxima pagina" -- 0.5h

## Criterios de Aceite

- [x] AuthModal renderiza corretamente em todos os 5 temas (light, paperwhite, sepia, dim, dark)
- [x] Texto, inputs, botoes e mensagens de erro/sucesso do AuthModal sao visiveis e legiveis em todos os temas
- [x] Nenhum token CSS inexistente (`var(--*)` sem definicao em globals.css) referenciado no AuthModal
- [x] Badges de tipo de licitacao no ItemsList sao consistentes com badges do SearchSummary na mesma pagina
- [x] Texto de erro no ItemsList usa tokens semanticos, nao cores Tailwind hardcoded
- [x] Aria-labels da paginacao contem acentos corretos em portugues
- [ ] Zero violacoes WCAG AA de contraste nos componentes corrigidos (validar via axe-core)

## Testes Requeridos

- [x] Snapshot tests do AuthModal nos 5 temas (unit)
- [x] Verificar que nenhum `var(--card-bg)`, `var(--text-primary)`, `var(--text-secondary)`, `var(--border-color)`, `var(--input-bg)`, `var(--accent-color)` permanece no codigo (CI grep)
- [x] Snapshot tests do ItemsList nos 5 temas (unit)
- [ ] Teste de acessibilidade axe-core incluindo AuthModal aberto (e2e)
- [x] Testes existentes do AuthModal continuam passando (unit)
- [x] Testes existentes do ItemsList continuam passando (unit)

## Estimativa

- **Horas:** 5.5h
- **Complexidade:** Simples (mapeamento de tokens 1:1, sem mudanca de logica)

## Dependencias

- **Depende de:** Nenhuma (Nivel 0 no grafo de dependencias)
- **Bloqueia:** Story 1.1 (Quick Wins Frontend -- adocao do Button depende de tokens corretos)

## Definition of Done

- [x] Codigo implementado e revisado
- [x] Todos os testes passando (existentes + novos snapshots)
- [x] Nenhuma regressao nos 576+ testes frontend (576 passed)
- [ ] Review aprovado
- [ ] Verificacao visual em pelo menos 3 temas (light, dim, dark)

---

*Story criada em 2026-03-11 por @pm (Sage)*
*Debitos: TD-UX-001 (Critico), TD-UX-002 (Alto), TD-UX-003 (Alto), TD-UX-010 (Baixo)*
