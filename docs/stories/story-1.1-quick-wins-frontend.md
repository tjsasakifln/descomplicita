# Story 1.1 -- Quick Wins: Frontend e Design System

## Contexto

Com os tokens visuais corrigidos na Story 0.1, esta story aproveita o momentum para adotar componentes reutilizaveis ja existentes (Button), mapear tokens CSS restantes no Tailwind config, estilizar o elemento `<mark>` por tema, e realizar limpezas de codigo no frontend. O componente Button existe no codebase com variantes (primary/secondary/ghost/danger), tamanhos e loading state com Spinner integrado, mas tem zero usos na aplicacao.

Referencia: `docs/prd/technical-debt-assessment.md` -- Secao "Sprint 1: Quick Wins"

## Objetivo

Consolidar o design system basico do frontend: adotar Button em todos os pontos relevantes, eliminar inline styles via mapeamento de tokens no Tailwind, garantir contraste adequado do highlight em temas escuros, e realizar deduplicacoes triviais.

## Tasks

- [ ] **Task 1** (TD-UX-023) -- Migrar botao "Buscar" (page.tsx linhas ~165-168) para componente Button com loading prop (ganha Spinner integrado) -- 0.5h
- [ ] **Task 2** (TD-UX-004) -- Adotar componente Button nos demais 3-4 botoes da aplicacao (page.tsx e outras paginas). Verificar que variantes, disabled e onClick sao preservados -- 2.5h
- [ ] **Task 3** (TD-UX-022) -- Mapear tokens CSS faltantes no tailwind.config.ts: `--ink-warning`, `--badge-licitacao-bg`, `--badge-licitacao-text`, `--badge-ata-bg`, `--badge-ata-text`. Elimina necessidade de `style={{}}` em SearchSummary e SourceBadges -- 1h
- [ ] **Task 4** (TD-UX-021) -- Estilizar elemento `<mark>` por tema em globals.css usando `var(--brand-blue-subtle)` para fundo e cores apropriadas por tema. Validar contraste WCAG AA nos 5 temas -- 1h
- [ ] **Task 5** (TD-UX-008) -- Remover classe `rounded-modal` orfao do tailwind.config.ts (nenhum componente a usa) -- 0.5h
- [ ] **Task 6** (TD-UX-013) -- Extrair funcao `dateDiffInDays` duplicada em dois arquivos para `frontend/lib/utils.ts` ou equivalente -- 0.5h
- [ ] **Task 7** (TD-UX-006) -- Extrair componente Footer reutilizavel (duplicado em page.tsx e termos/page.tsx) -- 1h
- [ ] **Task 8** (TD-UX-011 / TD-UX-019) -- Remover inline styles residuais de SearchSummary e SourceBadges (resolvido automaticamente pela Task 3 se tokens mapeados) -- 1h

## Criterios de Aceite

- [ ] Botao "Buscar" usa componente Button com loading state e Spinner
- [ ] Pelo menos 4 instancias do componente Button na aplicacao
- [ ] Zero `style={{}}` para tokens de badges em SearchSummary e SourceBadges
- [ ] Tokens `ink-warning`, `badge-licitacao-*`, `badge-ata-*` disponiveis como classes Tailwind
- [ ] Elemento `<mark>` estilizado corretamente em todos os 5 temas com contraste >= 4.5:1
- [ ] `rounded-modal` removido do tailwind.config.ts
- [ ] `dateDiffInDays` existe em um unico local, importada onde necessario
- [ ] Footer e componente reutilizado, sem duplicacao

## Testes Requeridos

- [ ] Testes unitarios dos botoes migrados: click, disabled, loading state (unit)
- [ ] Snapshot tests do SearchSummary e SourceBadges nos 5 temas (unit)
- [ ] Teste axe-core de contraste do `<mark>` nos 5 temas (e2e accessibility)
- [ ] Testes existentes de page.tsx continuam passando (unit)
- [ ] Testes existentes de SearchSummary continuam passando (unit)
- [ ] Verificar que `dateDiffInDays` importada corretamente nos dois consumidores (unit)

## Estimativa

- **Horas:** 8h
- **Complexidade:** Simples (adocao de componentes existentes, mapeamento de tokens, deduplicacoes)

## Dependencias

- **Depende de:** Story 0.1 (tokens CSS do AuthModal corrigidos; design tokens estaveis)
- **Bloqueia:** Nenhuma diretamente (Story 3.1 pode usar Input/Select como extensao)

## Definition of Done

- [ ] Codigo implementado e revisado
- [ ] Todos os testes passando (existentes + novos)
- [ ] Nenhuma regressao nos 576+ testes frontend
- [ ] Review aprovado
- [ ] Sem regressoes visuais nos 5 temas

---

*Story criada em 2026-03-11 por @pm (Sage)*
*Debitos: TD-UX-023 (Medio), TD-UX-004 (Medio), TD-UX-022 (Baixo), TD-UX-021 (Medio), TD-UX-008 (Trivial), TD-UX-013 (Baixo), TD-UX-006 (Baixo), TD-UX-011 (Baixo), TD-UX-019 (Baixo)*
