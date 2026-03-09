# UX Specialist Review
## Reviewer: @ux-design-expert (Vera)
## Data: 2026-03-09

> **Note:** This review supersedes the previous review by @ux-design-expert (Pixel) dated 2026-03-07.
> The codebase has changed substantially since that review -- the god component has been decomposed,
> accessibility improvements have been implemented, and the debt IDs have been renumbered (UXD-* scheme).
> All assessments below are based on the current codebase state as of commit 9c47d4ce.

---

## Summary

I reviewed all 20 UXD-* debts and 12 cross-cutting (XD-*) debts from the technical debt DRAFT against the actual codebase. The assessment is largely accurate. I validated 19 of 20 UXD debts, adjusted severity on 4 items, and found 3 new debts that were missed. The most impactful finding remains UXD-001 (multi-word terms impossible) -- this is a genuine user-facing bug that blocks legitimate search workflows. From a pure UX perspective, the hardcoded Tailwind colors in SearchSummary (UXD-018) should be elevated because they cause visible breakage in Sepia/Paperwhite themes, directly degrading the experience for users who chose those themes.

The previous review (Pixel, 2026-03-07) referenced debts (TD-004 god component, TD-008 focus trap, TD-009 Escape key, etc.) that have since been resolved. The current codebase is in substantially better shape: page.tsx is 185 lines, focus traps and ARIA roles are implemented, Escape handlers are present, and test coverage is at ~68%. The remaining debts are real but less severe than the previous assessment.

---

## Debitos Validados

| ID | Debito | Severidade Original | Severidade Ajustada | Horas | Prioridade | Impacto UX | Notas |
|----|--------|---------------------|---------------------|-------|------------|------------|-------|
| UXD-001 | Termos multi-palavras impossiveis | **Alta** | **Alta** | 3h | **P1** | Critico | Confirmado: SearchForm.tsx linha 113, espaco (`val.endsWith(" ")`) dispara criacao de token. Usuarios de licitacoes frequentemente buscam termos compostos ("camisa polo", "material de limpeza"). Bloqueador funcional real. |
| UXD-002 | Sem loading state para fetch de setores | Media | Media | 1h | P3 | Medio | Confirmado: useSearchForm.ts usa FALLBACK_SETORES hardcoded (7 setores) enquanto busca. Dropdown nunca fica completamente vazio, mas setores podem estar desatualizados momentaneamente. Impacto menor que o previsto devido ao fallback. |
| UXD-003 | Sem pagina 404 | Baixa | Baixa | 1h | P4 | Baixo | Confirmado: nenhum `not-found.tsx` encontrado. Impacto baixo pois app tem rota unica. |
| UXD-004 | Sem atalho de teclado para busca | Baixa | Baixa | 1h | P4 | Baixo | Confirmado: Enter no input de termos cria token, nao submete busca. Campos de data nao tem handler de Enter. |
| UXD-005 | SavedSearchesDropdown sem ARIA listbox | Media | Media | 3h | P3 | Medio | Confirmado: usa `div` com backdrop fixo inset-0. Funcional mas semanticamente incorreto. `aria-expanded` e `aria-haspopup` presentes, porem falta `role="listbox"` e `role="option"` nos itens. |
| UXD-006 | SaveSearchDialog sem `<dialog>` nativo | Media | **Baixa** | 2h | P4 | Baixo | Confirmado: usa `div` com `role="dialog"` e `aria-modal="true"`. Focus trap manual funciona corretamente (Tab cycling, Escape). A implementacao atual atende ARIA spec. Migrar para `<dialog>` nativo e melhoria de codigo, nao de UX. Severidade reduzida. |
| UXD-007 | Sem elemento `<form>` envolvendo formulario | Media | Media | 2h | P3 | Medio | Confirmado: page.tsx nao envolve o formulario em `<form>`. Impede autofill do browser e submissao nativa. Afeta usabilidade em mobile (teclado nao mostra "Go"/"Enviar"). |
| UXD-008 | Mixpanel importado incondicionalmente | Baixa | Baixa | 1h | P4 | Baixo | Confirmado: AnalyticsProvider importa mixpanel-browser no topo. ~40KB de bundle desnecessario quando analytics desabilitado. Impacto em performance, nao em UX diretamente. |
| UXD-009 | Sem confirmacao page unload durante busca | Baixa | Baixa | 0.5h | P4 | Baixo | Parcialmente abordado: LoadingProgress.tsx ja tem listener `beforeunload` mas apenas para analytics tracking (trackEvent), nao para exibir confirmacao ao usuario. Falta adicionar `e.preventDefault(); e.returnValue = ""` para mostrar dialogo nativo do browser. Esforco reduzido pois o listener ja existe. |
| UXD-010 | ThemeProvider imperativo (30+ props CSS) | Baixa | Baixa | 8h | P4 | Baixo | Confirmado: `applyTheme()` em ThemeProvider.tsx faz 30+ chamadas `root.style.setProperty()`. Funcional mas dificil de manter. Refatorar para data-attribute + CSS rules melhoraria DX mas nao afeta UX diretamente. |
| UXD-011 | Script FOUC duplica logica do ThemeProvider | Media | Media | 3h | P3 | Medio | Confirmado: layout.tsx linhas 41-61 duplicam parcialmente a logica do ThemeProvider (canvas/ink apenas, dark class). Script inline aplica apenas 2-4 propriedades vs 30+ do ThemeProvider completo. Flash parcial possivel em Sepia/Paperwhite (surfaces e borders nao aplicadas no script inline). |
| UXD-012 | Sem indicador offline/rede | Media | Media | 4h | P3 | Medio | Confirmado: nenhum uso de `navigator.onLine` ou Network Information API encontrado. Erros de rede durante polling mostram mensagem generica. |
| UXD-013 | Footer sem conteudo significativo | Baixa | Baixa | 1h | P4 | Baixo | Confirmado: page.tsx linha 180-182, footer contem apenas "DescompLicita -- Licitacoes e Contratos de Forma Descomplicada". Sem links de utilidade. |
| UXD-014 | SourceBadges sem acentos portugues | Baixa | Baixa | 0.25h | P4 (Quick Win) | Baixo | Confirmado: SourceBadges.tsx linha 112, `combinac{...}oes` / `combinac{...}ao` sem acentuacao correta. |
| UXD-015 | Sem auditoria de contraste (5 temas) | Media | **Alta** | 4h | **P2** | Alto | Confirmado e severidade elevada. ThemeProvider.tsx mostra que Sepia e Paperwhite tem tratamento especial para surfaces, mas cores semanticas como `--ink-secondary: #3d5975` sobre `--canvas: #EDE0CC` (Sepia) precisam verificacao. Acessibilidade e obrigacao legal (LBI 13.146/2015, WCAG AA), nao opcional. |
| UXD-016 | LoadingProgress 450+ linhas | Media | Media | 6h | P3 | Baixo | Confirmado: 452 linhas. Componente funcional e complexo por natureza. Decomposicao melhora manutenibilidade mas nao afeta UX do usuario final. |
| UXD-017 | Setores fallback hardcoded | Baixa | Baixa | 1h | P4 | Baixo | Confirmado: useSearchForm.ts linhas 45-51, 7 setores hardcoded como FALLBACK_SETORES. Risco de drift se backend adicionar ou remover setores. |
| UXD-018 | Cores hardcoded em SearchSummary | Baixa | **Media** | 1h | **P2** (Quick Win) | Medio | Confirmado e severidade elevada: SearchSummary.tsx linhas 26-33 usam `bg-blue-100 text-blue-800` e `bg-purple-100 text-purple-800` com fallback `dark:`. Essas cores ignoram completamente os temas Sepia e Paperwhite, criando badges visualmente inconsistentes. Usuarios desses temas veem cores que nao combinam com o restante da interface. |
| UXD-019 | carouselData com cores hardcoded | Baixa | **Media** | 2h | P3 | Medio | Confirmado e severidade elevada: carouselData.ts usa `bg-blue-50 dark:bg-blue-950/30`, `bg-green-50`, etc. Mesma questao do UXD-018 -- ignora Sepia/Paperwhite. Porem impacto menor pois carrossel so aparece durante loading (transiente). |
| UXD-020 | Sem noValidate no form | Baixa | Baixa | 0.1h | P4 (Quick Win) | Trivial | Confirmado: nenhum uso de `noValidate` encontrado. Porem, sem elemento `<form>` (UXD-007), `noValidate` nao se aplica atualmente. Este debito depende de UXD-007 ser resolvido primeiro. |

---

## Debitos Removidos

Nenhum debito completamente removido. Todos os 20 UXD debts sao reais e verificados no codigo.

**UXD-020 merece nota:** embora valido, e inoperante ate que UXD-007 (adicionar `<form>`) seja resolvido. Nao e um falso positivo, mas e uma dependencia que deve ser documentada.

---

## Debitos Adicionados

| ID | Debito | Severidade | Horas | Prioridade | Impacto UX |
|----|--------|------------|-------|------------|------------|
| UXD-021 | **Cores amber hardcoded em SourceBadges e carouselData.** SourceBadges.tsx linha 111 usa `text-amber-600 dark:text-amber-400` para mensagem de truncamento, e carouselData.ts linha 46 usa `text-amber-600 dark:text-amber-400` para categoria "dica". Mesma classe de problema que UXD-018/019 -- nao responsivo aos temas Sepia/Paperwhite. Deveria usar token `text-warning`. | Baixa | 0.5h | P4 (Quick Win) | Baixo |
| UXD-022 | **Sem `aria-required` em campos obrigatorios.** Nenhum campo do formulario marca campos obrigatorios com `aria-required="true"`. Verificado: zero resultados para `aria-required` no frontend. Screen readers nao anunciam quais campos sao mandatorios (UF, datas). Afeta acessibilidade. | Media | 0.5h | P2 (Quick Win) | Medio |
| UXD-023 | **Delete confirmation timeout (3s) inacessivel para screen readers.** SavedSearchesDropdown.tsx linha 93 usa `setTimeout(() => setDeleteConfirmId(null), 3000)` e linha 199 faz o mesmo para "Limpar todas". Usuarios de screen reader ou com deficiencias motoras podem nao conseguir confirmar a acao em 3 segundos. WCAG 2.2.1 (Timing Adjustable) recomenda no minimo 20 segundos ou remocao do timeout. | Media | 1h | P2 | Medio |

---

## Cross-cutting Debts Review

### XD-SEC-01 (Headers de seguranca ausentes) - Media
**Impacto UX:** Indireto. CSP poderia bloquear o inline script de FOUC (layout.tsx linhas 41-63) se implementado sem `nonce` ou hash. Ao implementar CSP, sera necessario alinhar com UXD-010/011 para evitar retrabalho.

### XD-SEC-02 (Autenticacao fragil end-to-end) - Critica
**Impacto UX:** Nenhum impacto UX direto na versao atual (POC sem login). Quando auth for implementado, sera necessario adicionar fluxo de login, registro, e tratamento de sessao expirada no frontend. Planejar UX de auth antecipadamente evitara retrabalho significativo.

### XD-SEC-03 (dangerouslySetInnerHTML + sem CSP) - Media
**Impacto UX:** Confirmado em layout.tsx linhas 41-63. O script inline e seguro hoje (sem input de usuario), mas quando CSP for adicionado, este script precisara ser refatorado. Alinhar com UXD-010/011.

### XD-API-01 (Sem versionamento de API) - Media
**Impacto UX:** Mudancas no backend podem quebrar o frontend silenciosamente. Usuarios veriam erros genericos. Impacto mitigado pelo BFF pattern (API routes em Next.js atuam como adaptadores).

### XD-API-02 (Sem testes de contrato) - Media
**Impacto UX:** Drift entre tipos TypeScript e schemas Pydantic pode causar dados undefined no frontend, resultando em UI quebrada (texto faltando, contadores incorretos, downloads silenciosamente falhando).

### XD-API-03 (Codigos de erro nao estruturados) - Baixa
**Impacto UX:** Frontend depende de parsing de texto livre para exibir erros. Mensagens de erro podem ser confusas se backend mudar wording. Severidade adequada.

### XD-PERF-01 (Download bufferizado em cadeia) - Alta
**Impacto UX:** Alto. Usuarios experimentam delay significativo entre clicar "Download" e receber o arquivo. Sem indicador de progresso real para o download (apenas spinner). Para arquivos grandes, pode causar timeout (TD-H06) sem feedback claro ao usuario.

### XD-PERF-02 (Sem paginacao end-to-end) - Media
**Impacto UX:** Medio. O componente SearchSummary mostra resumo AI e o download Excel e o CTA principal, entao a maioria dos usuarios nao precisa percorrer resultados individualmente. Impacto aumentara quando lista detalhada de licitacoes for implementada.

### XD-PERF-03 (Polling intervalo fixo) - Baixa
**Impacto UX:** Baixo. Polling a cada 2s e imperceptivel para o usuario. Backoff exponencial economizaria requests mas nao melhoraria UX perceptivelmente. Severidade adequada.

### XD-TEST-01 (Sem testes integracao frontend-backend) - Media
**Impacto UX:** Indireto. Bugs de integracao so sao detectados em producao, afetando usuarios reais.

### XD-TEST-02 (Sem smoke tests pos-deploy) - Media
**Impacto UX:** Indireto. Deploy quebrado afeta todos os usuarios sem deteccao automatica.

### XD-TEST-03 (Sem testes regressao visual) - Baixa
**Impacto UX:** Com 5 temas, mudancas visuais involuntarias sao provaveis. Regressao visual nos temas Sepia/Paperwhite e particularmente arriscada dado os tokens hardcoded (UXD-018/019/021). Severidade adequada mas importancia cresce com cada correcao de tema.

---

## Respostas ao Architect

### 1. UXD-001 (termos multi-palavras): abordagem preferida

**Recomendacao: combinacao de aspas + virgula como delimitadores.**

- Aspas duplas para termos compostos: `"camisa polo"` resulta em token unico "camisa polo"
- Virgula como delimitador alternativo: `camisa polo, material limpeza` cria dois tokens compostos
- Manter espaco como delimitador para termos simples (retrocompativel)
- Placeholder deve atualizar para: `"Separe termos por virgula ou use aspas para termos compostos"`
- Impacto na curva de aprendizado: minimo. Aspas sao convencao universal (Google, Amazon). Hint text no placeholder e no `aria-describedby` orientam usuarios novos.
- Alternativa descartada: modal de adicao de termo (overengineering para POC).

### 2. UXD-015 (contraste dos temas): ferramenta e decisao sobre temas

**Ferramenta recomendada:** axe DevTools browser extension para auditoria manual dos 5 temas, complementado por `@axe-core/playwright` (ja instalado no projeto) para auditoria automatizada no E2E.

**Processo:**
1. Para cada tema, executar axe no browser com todos os estados visiveis (form vazio, loading, resultados, empty state, erro)
2. Documentar todos os pares foreground/background e seus ratios de contraste
3. Ajustar tokens no ThemeProvider onde necessario
4. Adicionar teste E2E com axe para cada tema prevenindo regressoes

**Sobre manter Sepia e Paperwhite:** Manter ambos. Eles atendem casos de uso reais:
- **Paperwhite:** reduz fadiga visual para uso prolongado (e-ink aesthetic)
- **Sepia:** preferido por usuarios com sensibilidade a luz azul
- Remover temas seria uma regressao de acessibilidade e preferencia do usuario
- O custo de manter 5 temas e baixo se os tokens forem corrigidos (UXD-018/019/021)

### 3. UXD-016 (LoadingProgress): decomposicao recomendada

**Sim, a decomposicao sugerida esta correta.** Recomendo:

```
LoadingProgress.tsx (orquestrador, ~80 linhas)
  |-- ProgressBar.tsx (~40 linhas: barra visual, ETA, porcentagem)
  |-- StageList.tsx (~60 linhas: lista de estagios com icones e status)
  |-- UfProgressGrid.tsx (~50 linhas: grid de UFs com status individual)
  |-- CuriosityCarousel.tsx (~80 linhas: carrossel de dicas/curiosidades)
  |-- LoadingSkeleton.tsx (~30 linhas: skeleton para fallback do dynamic import)
```

Beneficios: cada sub-componente e testavel isoladamente, o carrossel pode ser lazy-loaded separadamente, e futuros ajustes de UX em um estagio nao arriscam quebrar outros. O carouselData.ts (369 linhas, 52 items) deve ser dynamically imported dentro de CuriosityCarousel para reduzir bundle inicial (~15KB economia).

### 4. Design System: prioridade entre opcoes

**Ordem recomendada:**

1. **(a) Extrair `<TextInput>` e `<Button>` primeiro.** Impacto imediato: elimina 4x duplicacao de estilos de input (verificada em SearchForm setor select, SearchForm terms wrapper, DateRangeSelector 2x, SaveSearchDialog) e padroniza botoes. Retorno de investimento mais rapido. Estimativa: 4h para TextInput + Button + migracao dos 4+ locais.
2. **(c) Documentacao de design system.** Um `DESIGN_SYSTEM.md` simples com tokens existentes, tipografia, e componentes. Nao precisa ser exaustivo -- documenta o que ja existe. 2h.
3. **(b) Setup Storybook.** Ultimo, pois Storybook e mais util quando ha componentes reutilizaveis para documentar. Sem (a) e (c), Storybook seria um shell vazio. Estimativa: 3h para setup + stories iniciais dos componentes extraidos.

### 5. UXD-005/UXD-006: prioridade de migracao para `<dialog>`

**Nao e prioritaria.** As implementacoes atuais funcionam corretamente:

- **SaveSearchDialog** tem focus trap funcional, `role="dialog"`, `aria-modal="true"`, Escape handler -- atende ARIA spec completamente
- **SavedSearchesDropdown** tem `aria-expanded`, `aria-haspopup`, Escape handler via document keydown listener -- funcional

Migracao para `<dialog>` nativo traz beneficios de manutenibilidade (eliminacao de codigo de focus trap) mas nao melhora UX ou acessibilidade perceptivelmente. Por esse motivo rebaixei UXD-006 para Baixa.

**UXD-005 permanece Media** porque o dropdown nao e semanticamente um dialog -- e um listbox/menu. A correcao deveria adicionar `role="listbox"` e `role="option"` nos itens da lista, nao migrar para `<dialog>`.

### 6. Acessibilidade geral: B+ adequado para POC?

**B+ e adequado para estagio POC, mas existem itens que deveriam ser P2 antes de lancamento publico:**

- **UXD-022 (aria-required):** Quick win de 30 minutos, melhora experiencia de screen reader significativamente. Campos obrigatorios nao sao anunciados como tal.
- **UXD-015 (contraste):** Obrigacao legal em muitas jurisdicoes (incluindo Brasil, LBI 13.146/2015). Deveria ser P2 no minimo.
- **UXD-023 (timeout 3s em confirmacao de delete):** Viola WCAG 2.2.1 (Timing Adjustable) tecnicamente. Fix simples: aumentar timeout para 10s ou remover completamente.

Nenhum desses e P0 bloqueador pois a app funciona para a maioria dos usuarios. Mas esses 3 itens devem ser resolvidos antes de qualquer lancamento publico ou apresentacao para clientes.

A nota B+ e justificada pelo trabalho ja realizado: skip navigation, focus traps, ARIA roles, keyboard navigation em menus, aria-live regions, prefers-reduced-motion, 44px touch targets. A fundacao de acessibilidade e solida.

---

## Recomendacoes de Design

### 1. Resolver inconsistencia de cores por tema (UXD-018/019/021)
Criar tokens semanticos para badges de tipo no design token system:
- `--badge-primary-bg`, `--badge-primary-text`, `--badge-primary-border`
- `--badge-secondary-bg`, `--badge-secondary-text`, `--badge-secondary-border`
- `--badge-info-text` (para mensagens warning/informativas, substituindo amber hardcoded)

Esses tokens devem ser definidos por tema no ThemeProvider `applyTheme()`, eliminando todas as cores Tailwind hardcoded em SearchSummary, carouselData, e SourceBadges.

### 2. Input de termos multi-palavras (UXD-001)
A implementacao deve:
- Detectar aspas no input e nao quebrar em espacos quando dentro de aspas
- Aceitar virgula como delimitador alternativo ao espaco
- Mostrar hint text claro com exemplos no `aria-describedby`
- Suportar paste de termos separados por virgula (parse no onChange)
- Atualizar placeholder contextualmente

### 3. Componentes de formulario extraidos
Priorizar `<TextInput>` com as seguintes props:
```
id, label, value, onChange, placeholder, error?, required?, maxLength?, hint?
```
Isso eliminaria a duplicacao de classes CSS em 4+ locais e garantiria consistencia visual automaticamente, alem de fornecer ponto unico para adicionar `aria-required` (resolvendo UXD-022).

### 4. Script FOUC alinhado com ThemeProvider (UXD-011)
O script inline em layout.tsx aplica apenas `--canvas` e `--ink` (+ dark class). Quando o ThemeProvider monta, ele aplica 30+ propriedades. O gap temporal causa micro-flash em superficies, borders, e badges. Opcoes:
- **Curto prazo (recomendado):** Expandir script inline para cobrir `--surface-0`, `--surface-1`, `--border`, `--border-strong` (4 propriedades extras com maior impacto visual)
- **Longo prazo:** Migrar para data-attribute approach (UXD-010) que eliminaria o script inline completamente

---

## Ordem de Resolucao Recomendada (UX)

1. **UXD-001** - Termos multi-palavras (3h) -- bloqueador funcional, usuarios nao conseguem buscar termos compostos
2. **UXD-022** - Adicionar aria-required (0.5h) -- quick win de acessibilidade
3. **UXD-018** - Cores hardcoded SearchSummary (1h) -- quebra visual em temas, quick win
4. **UXD-015** - Auditoria de contraste dos 5 temas (4h) -- obrigacao de acessibilidade
5. **UXD-023** - Timeout de confirmacao de delete (1h) -- violacao WCAG 2.2.1
6. **UXD-007** - Adicionar elemento `<form>` (2h) -- melhora autofill e mobile UX
7. **UXD-021** - Cores amber hardcoded (0.5h) -- quick win junto com UXD-018
8. **UXD-019** - Cores hardcoded carouselData (2h) -- consistencia visual em temas
9. **UXD-011** - Alinhar script FOUC com ThemeProvider (3h) -- elimina micro-flash de tema
10. **UXD-005** - SavedSearchesDropdown ARIA listbox (3h) -- semantica correta para screen readers
11. **UXD-012** - Indicador offline/rede (4h) -- melhora feedback de erros de conectividade
12. **UXD-016** - Decomposicao LoadingProgress (6h) -- manutenibilidade e testabilidade

---

## Quick Wins UX

Correcoes com alto retorno de investimento, executaveis em menos de 1 hora cada:

| ID | Debito | Tempo | Impacto | Descricao da Correcao |
|----|--------|-------|---------|----------------------|
| UXD-014 | SourceBadges sem acentos | 15min | Percepcao de qualidade | Corrigir `combinacoes`/`combinacao` para formas com acentuacao correta em SourceBadges.tsx linha 112 |
| UXD-020 | Sem noValidate no form | 5min | Prevencao de conflito | Adicionar `noValidate` ao `<form>` (implementar junto com UXD-007) |
| UXD-022 | Sem aria-required | 30min | Acessibilidade | Adicionar `aria-required="true"` nos campos de UF, data, e setor/termos |
| UXD-021 | Cores amber hardcoded | 30min | Consistencia visual | Substituir `text-amber-600 dark:text-amber-400` por `text-warning` em SourceBadges.tsx e carouselData.ts |
| UXD-018 | Cores hardcoded SearchSummary | 1h | Corrigir quebra em temas | Criar tokens de badge e substituir `bg-blue-100` etc. por tokens que respeitem todos os 5 temas |
| UXD-009 | Sem confirmacao page unload | 30min | Prevencao de perda | Adicionar `e.preventDefault(); e.returnValue = ""` no listener existente de beforeunload em LoadingProgress.tsx |

**Total quick wins: ~3 horas para 6 correcoes com impacto imediato.**

---

**Review Status: COMPLETE**
**Reviewer:** @ux-design-expert (Vera)
**Signed:** 2026-03-09
**Next step:** Consolidation by @architect into final technical-debt.md
