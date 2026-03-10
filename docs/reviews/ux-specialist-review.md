# UX Specialist Review
**Reviewer:** @ux-design-expert (Pixel)
**Date:** 2026-03-09

> **Note:** This review supersedes the previous review by @ux-design-expert (Vera) dated 2026-03-09.
> The codebase has changed substantially since that review -- LoadingProgress has been decomposed,
> ThemeProvider refactored to CSS cascade, SavedSearchesDropdown has full ARIA listbox, SaveSearchDialog
> uses native `<dialog>`, and Ctrl+Enter keyboard shortcut is implemented.
> The technical debt IDs have been renumbered from UXD-* to FE-* scheme in the consolidated DRAFT.
> All assessments below are based on the current codebase state as of commit 5e56b38d.

---

## Gate Status: NEEDS REVISION

The DRAFT is substantially well-researched. The FE debt items are accurate, and the deep dives on search quality and large-volume scenarios are strong. However, I identify **5 missing UX debt items**, several severity adjustments, and critical UX gaps in the search results experience that must be addressed before this document is finalized.

---

## Debitos Validados

| ID | Debito | Severidade Original -> Revisada | Horas | Prioridade | Impacto UX |
|----|--------|--------------------------------|-------|------------|------------|
| FE-001 | Cores hardcoded em SearchSummary badges | Alta -> **Alta** (confirmado) | 1h | P2 | Badges `bg-blue-100 text-blue-800` e `bg-purple-100 text-purple-800` nao respondem a temas paperwhite/sepia/dim. Verificado no codigo: linhas 26-34 de `SearchSummary.tsx`. Em sepia (`--canvas: #EDE0CC`), os badges azul/roxo criam contraste visual chocante e perdem legibilidade. |
| FE-002 | Cor hardcoded em SourceBadges warning | Baixa -> **Baixa** (confirmado) | 0.5h | P4 | `text-amber-600 dark:text-amber-400` na linha 111 de `SourceBadges.tsx` nao usa o token `text-warning`. Impacto real e minimo -- amber e proximo de warning em todos os temas, mas viola a consistencia do design system. |
| FE-003 | UUID dependency desnecessaria | Baixa -> **Baixa** (confirmado) | 0.5h | P4 | Sem impacto UX direto. Apenas bundle size. |
| FE-004 | Spinner component ausente | Media -> **Media** (confirmado) | 1h | P3 | SVG spinner duplicado em `SearchForm.tsx` (linhas 67-70) e `SearchActions.tsx`. Risco de drift visual entre as duas instancias. |
| FE-005 | Error swallowing em ItemsList | Alta -> **Critica** (elevada) | 2h | **P1** | Verificado: `catch {}` vazio na linha 44 de `ItemsList.tsx`. O teste `ItemsList.test.tsx` linha 141-150 confirma que o cenario de erro e tratado como "graceful" mas na realidade o usuario fica preso em "Carregando..." ou ve uma lista vazia sem explicacao. Para buscas de grande volume onde paginacao e essencial, isso e **critico**. Sem retry, sem mensagem, sem Sentry logging. |
| FE-006 | Button component ausente | Media -> **Media** (confirmado) | 3h | P3 | Botoes inline com classes longas em `page.tsx` (linha 138-141), `EmptyState.tsx` (linha 131), `SearchActions.tsx`, etc. Drift ja visivel: o botao "Tentar novamente" em `page.tsx` usa `bg-error` enquanto outros usam `bg-brand-navy`. |
| FE-007 | ink-muted contraste < WCAG AA | Media -> **Alta** (elevada) | 1h | **P2** | `#5a6a7a` contra `#ffffff` = 4.1:1 (abaixo de 4.5:1). Usado extensivamente para timestamps, metadata, hints em `ItemsList.tsx`, `Pagination.tsx`, `ProgressBar.tsx`, `EmptyState.tsx`, e footer. Isso afeta leitura de informacao crucial como datas, valores, e contagem de resultados. Nota: paperwhite (`#526272` contra `#F5F0E8` = ~4.6:1) e sepia (`#4a5968` contra `#EDE0CC` = ~5.2:1) ja estao adequados. Apenas o tema light esta abaixo. Recomendacao: alterar `--ink-muted` no `:root` de `#5a6a7a` para `#4f5f6f` (~4.8:1) -- ajuste minimo que atinge AA. |
| FE-008 | Link /termos quebrado | Media -> **Media** (confirmado) | 2h | P3 | Verificado em `page.tsx` linha 202: `<a href="/termos">`. Rota inexistente. Cada usuario ve um link quebrado no footer. |
| FE-009 | Sem fallback para dynamic imports | Baixa -> **Baixa** (confirmado) | 1h | P4 | `EmptyState` e `ItemsList` importados via `next/dynamic` sem `loading` fallback em `page.tsx` linhas 36-42. Chunk load failure = secao em branco. |
| FE-010 | Teste RegionSelector ausente | Baixa -> **Baixa** (confirmado) | 1.5h | P4 | Sem impacto UX direto. |
| FE-011 | Teste SourceBadges ausente | Media -> **Media** (confirmado) | 2h | P3 | Componente com logica condicional complexa (status colors, dedup stats, truncation warning) sem teste. Risco de regressao. |
| FE-012 | Tema Dim incompleto | Baixa -> **Baixa** (confirmado) | 2h | P4 | Verificado em `globals.css` linhas 109-112: dim so sobrescreve `--canvas` e `--surface-0`. Herda tudo de `.dark`. Dim e indistinguivel de dark para a maioria dos elementos. |
| FE-013 | SavedSearchesDropdown null durante loading | Baixa -> **Baixa** (confirmado) | 0.5h | P5 | Layout shift breve. Impacto minimo. |
| FE-014 | page.tsx monolitico | Baixa -> **Baixa** (confirmado) | 4h | P5 | 209 linhas com `"use client"`. Nao causa problemas de performance observaveis ainda, mas limita oportunidades de SSR. |

---

## Debitos Adicionados

### FE-015: Sem Highlight de Termos de Busca nos Resultados (NOVO)

- **Severidade:** Alta
- **Impacto UX:** Quando o usuario busca por termos customizados (ex: `"jaleco medico"`), os resultados em `ItemsList.tsx` exibem o campo `objeto` como texto puro (`item.objeto` na linha 79) sem nenhum destaque visual dos termos que causaram o match. O usuario nao consegue avaliar rapidamente POR QUE um resultado foi retornado, dificultando a identificacao de falsos positivos e a triagem eficiente de resultados.
- **Esforco:** 4h
- **Prioridade:** P2
- **Recomendacao:** Implementar highlight dos termos de busca no texto do `objeto`. Receber os termos de busca como prop no `ItemsList` e aplicar `<mark>` ou `<span class="bg-warning-subtle font-medium">` nos trechos correspondentes. Considerar normalizacao de acentos no highlight (ex: busca por "licitacao" deve destacar "licitacao" no resultado).

### FE-016: Sem Advertencia Proativa para Buscas de Grande Volume (NOVO)

- **Severidade:** Alta
- **Impacto UX:** Quando o usuario seleciona "Selecionar todos" (27 UFs) e um range de 30+ dias, nao ha nenhum feedback visual indicando que a busca sera demorada. O `UfSelector.tsx` mostra apenas "27 estados selecionados" (linha 70) sem nenhum aviso. O usuario clica "Buscar" sem expectativa do tempo necessario (potencialmente 5-10 minutos). Isso leva a abandono da busca, confusao sobre se o sistema travou, e uso desnecessario de recursos.
- **Esforco:** 3h
- **Prioridade:** P2
- **Recomendacao:** Adicionar um banner de aviso condicional no `UfSelector.tsx` ou entre o seletor e o botao de busca. Trigger: `ufsSelecionadas.size > 10` OU date range > 30 dias. Texto sugerido: "Buscas com muitos estados e/ou periodos longos podem demorar varios minutos. Para resultados mais rapidos, selecione ate 10 estados e um periodo de ate 14 dias." Formato: banner informativo com icone, nao bloqueante.

### FE-017: Mensagem de Timeout Generica sem Orientacao (NOVO)

- **Severidade:** Media
- **Impacto UX:** Quando o polling timeout de 10 minutos e atingido, a mensagem exibida e: `"A consulta excedeu o tempo limite. Tente com menos estados ou um periodo menor."` (linha 163 de `useSearchJob.ts`). Embora inclua uma sugestao basica, nao ha: (a) contexto sobre quantos estados/dias foram selecionados; (b) sugestao especifica de reducao (ex: "Voce selecionou 27 estados -- tente com 5-10"); (c) opcao de re-tentar com parametros reduzidos automaticamente; (d) indicacao se resultados parciais estao disponiveis.
- **Esforco:** 2h
- **Prioridade:** P3
- **Recomendacao:** Enriquecer a mensagem de timeout com contexto do cenario: `"A busca em {N} estados por {M} dias excedeu o limite de 10 minutos. Sugestao: reduza para {N/2} estados ou {M/2} dias para resultados mais rapidos."` Considerar oferecer um botao "Tentar com menos estados" que pre-configura uma selecao reduzida.

### FE-018: ItemsList Heading com Acento Faltando (NOVO)

- **Severidade:** Baixa
- **Impacto UX:** O heading em `ItemsList.tsx` linha 63 exibe `"Licitacoes Encontradas"` sem acentos (cedilha e til) em vez de `"Licita\u00e7\u00f5es Encontradas"`. Verificado no teste `ItemsList.test.tsx` linhas 35-36 que o texto tambem aparece sem acentos. Embora o restante da aplicacao use acentos corretos (ex: `page.tsx` linha 120: `"Busca de Licita\u00e7\u00f5es"`), este componente usa texto sem acento, criando inconsistencia.
- **Esforco:** 0.25h
- **Prioridade:** P4
- **Recomendacao:** Corrigir para `"Licita\u00e7\u00f5es Encontradas"` com acentos e cedilha. Atualizar o teste correspondente.

### FE-019: Sem Protecao contra Race Conditions na Paginacao (NOVO)

- **Severidade:** Media
- **Impacto UX:** O `ItemsList.tsx` `fetchPage` callback (linhas 30-51) nao usa AbortController. Quando o usuario navega rapidamente entre paginas, cada mudanca dispara um fetch independente. Se a resposta da pagina 3 chegar depois da resposta da pagina 5, o usuario vera itens da pagina 3 enquanto a UI indica pagina 5. Nao ha debounce no `onPageChange` do `Pagination` component. Em conexoes lentas ou com grande volume de dados (85K items desserializados por request, conforme DB-009), essa race condition e provavel.
- **Esforco:** 2h
- **Prioridade:** P3
- **Recomendacao:** (1) Adicionar `AbortController` em `fetchPage` para cancelar requests anteriores quando uma nova pagina e solicitada. (2) Opcionalmente adicionar debounce de 150ms no `onPageChange`. O pattern de AbortController ja existe implicitamente na estrutura do `useCallback` -- basta adicionar um `abortControllerRef`.

---

## Deep Dive: Search UX

### Fluxo de Busca por Termos Customizados

**Mecanismo de entrada de termos** (`SearchForm.tsx` linhas 119-155): O usuario digita um termo e pressiona `espaco` ou `Enter` para confirmar. Termos sao transformados em chips visuais com botao de remocao. Multi-word terms sao suportados via aspas no backend (`parse_multi_word_terms`), mas a UI do frontend nao oferece affordance para multi-word -- o espaco cria um token novo. O hint text (linha 157-158) diz "Digite cada termo e pressione espaco para confirmar" mas nao menciona aspas ou virgulas.

**Achados:**

1. **Termos com acentos sao aceitos e exibidos corretamente** no input e nos chips. O `onChange` handler (linha 127) aplica `.toLowerCase()` mas preserva acentos. A normalizacao de acentos acontece no backend (`normalize_text()`), nao no frontend. Isso e correto -- o frontend preserva o que o usuario digitou.

2. **Sem preview/feedback de matching**: O usuario nao sabe quais termos farao match ate ver os resultados. Nao ha auto-suggest, auto-complete, ou indicacao de que acentos serao normalizados.

3. **Resultados nao indicam relevancia**: `ItemsList.tsx` exibe os items como lista flat sem score, ranking, ou indicacao de por que o item apareceu. O usuario nao consegue distinguir um match forte (termo no titulo) de um match fraco (termo em contexto ambiguo).

4. **Sem filtro/refinamento pos-busca**: Uma vez que os resultados aparecem, o usuario nao pode filtrar por UF, valor, data, ou tipo. A unica acao e uma nova busca do zero.

### Fluxo "No Results Found"

O `EmptyState.tsx` e **bem implementado**:
- Exibe contagem de items brutos encontrados vs rejeitados
- Breakdown por motivo de rejeicao (keyword, valor, UF) com contagens individuais
- Tips actionaveis para cada motivo de rejeicao
- Sugestoes genericas (ampliar periodo, selecionar mais estados, trocar setor)
- Botao "Ajustar criterios de busca" que faz scroll to top
- Estatisticas contextuais (numero de estados pesquisados, modalidades usadas)

**Lacuna encontrada:** O EmptyState usa `sectorName` como default `"uniformes"` (linha 18) quando nao informado. Para buscas por termos customizados, o `sectorName` e passado como `"Licita\u00e7\u00f5es"` (`useSearchForm.ts` linhas 147-149), o que gera a mensagem "Nenhuma licita\u00e7\u00e3o de licita\u00e7\u00f5es encontrada" -- redundante e confusa. O EmptyState deveria exibir os termos de busca em vez do nome do setor quando em modo `termos`.

### Qualidade Visual dos Resultados

O `SearchSummary.tsx` apresenta um **resumo executivo AI forte** com:
- Total de oportunidades (numero grande, fonte data)
- Valor total em R$ (numero grande, fonte data)
- Badges de tipo (licitacao/ata) -- mas com cores hardcoded (FE-001)
- Alerta de urgencia (condicional, role="alert")
- Lista de destaques com animacao staggered
- SourceBadges com detalhamento expansivel

A estrutura e boa, mas os **items individuais** em `ItemsList.tsx` sao significativamente mais pobres em informacao. Cada card mostra:
- `objeto` (descricao) -- truncado em 2 linhas (`line-clamp-2`)
- `orgao` (nome do orgao)
- `uf` (estado, como badge)
- `valorTotalEstimado` (valor em R$)
- `dataPublicacao` (data formatada pt-BR)
- Link "Ver" para o PNCP

**O que falta nos cards de resultado:**
- Tipo (licitacao vs ata) -- o campo `tipo` e recebido (linha 13 do `ProcurementItem` interface) mas nunca renderizado
- Score/relevancia
- Highlight dos termos de busca
- Modalidade (pregao eletronico, concorrencia, etc.)
- Status (ativo, encerrado)

---

## Deep Dive: Large Volume Search UX

### O Que o Usuario Ve Durante Busca de 27 UFs x 30 Dias

**Cenario analisado via codigo:**

1. **Botao "Buscar"** muda para "Buscando..." com `aria-busy="true"` -- imediato, bom feedback.

2. **LoadingProgress aparece** (`page.tsx` linhas 143-149) dentro de `aria-live="polite"`:
   - **ProgressBar**: Barra de progresso com porcentagem, ETA estimado, tempo decorrido, mensagem de status contextual ("Buscando em X/Y estados... (Z licita\u00e7\u00f5es encontradas)")
   - **UfGrid**: Grid visual de 27 UFs mostrando estados completados (azul escuro), em processamento (azul com pulse animation), e pendentes (cinza) -- **excelente feedback granular**
   - **StageList**: 5 stages com dots de progresso (queued, fetching, filtering, summarizing, generating_excel) + mobile detail card
   - **CuriosityCarousel**: Dicas educacionais rotativas a cada 6s, filtradas por setor selecionado -- **muito bom para manter engajamento durante esperas longas**
   - **SkeletonCards**: Placeholder cards com shimmer animation
   - **Cancel button**: Sempre visivel, com hover state vermelho

3. **ETA accuracy** (`LoadingProgress.tsx` `getETA()` linhas 41-50):
   - Para fase `fetching`: calcula ETA baseado em `(ufsTotal - ufsCompleted) * (elapsedSeconds / ufsCompleted) + 20s buffer`. Funciona razoavelmente para 3-10 UFs, mas para 27 UFs o ETA inicial sera impreciso (baseado em poucas amostras) e vai flutuar significativamente nos primeiros estados.
   - Para fases pos-fetching: ETAs fixos hardcoded (`~15s restantes`, `~10s restantes`, `~5s restantes`). Para 85K items, a fase de filtering pode levar 30-60s, nao 15s. **O ETA hardcoded sera enganoso para grandes volumes.**

4. **Progress bar accuracy**: A funcao `calculateProgress()` (linhas 29-34) usa valores fixos para fases pos-fetching: filtering=60%, summarizing=75%, generating_excel=90%. Para grandes volumes, o usuario pode ficar preso em 60% por minutos enquanto a mensagem diz "~15s restantes".

5. **Timeout scenario**: Apos 10 minutos, o usuario ve: "A consulta excedeu o tempo limite. Tente com menos estados ou um periodo menor." + botao "Tentar novamente". Mensagem generica sem contexto especifico (analisada em FE-017).

### Analise Critica do Feedback para Grande Volume

| Aspecto | Avaliacao | Detalhe |
|---------|-----------|---------|
| Progress bar accuracy (fetching) | **Adequada** | Baseia-se em UFs completados / total -- metrica real |
| Progress bar accuracy (pos-fetching) | **Inadequada** | Valores fixos (60%, 75%, 90%) nao refletem tempo real de filtering/summarizing para 85K items |
| ETA para fetching | **Imprecisa no inicio** | Com 1 de 27 UFs completo, o ETA extrapola linearmente, mas UFs variam muito em volume (SP vs AC) |
| ETA pos-fetching | **Enganosa** | Hardcoded `~15s restantes` para filtering quando pode levar 60s+ com 85K items |
| UF Grid | **Excelente** | Feedback visual granular por estado, pulse animation no estado ativo |
| Cancel button | **Adequado** | Sempre visivel, acao imediata, tracking de analytics |
| Tab notification | **Bom** | Titulo muda + browser notification quando backgrounded |
| Polling overhead | **Adequado** | Exponential backoff de 1s a 15s reduz requests em 60-80% |
| Curiosity carousel | **Excelente** | Mantém engajamento, filtrado por setor, rotacao a cada 6s com fade |

### Race Condition: Frontend Timeout vs Backend Timeout

Confirmada pelo DRAFT: para 27 UFs, o backend calcula timeout de `300 + (27-5)*15 = 630s` (10.5 min), enquanto o frontend timeout e fixo em `10 * 60 * 1000 = 600000ms` (10 min exatos). O frontend desistira 30 segundos antes do backend completar. O usuario vera erro de timeout mesmo que o backend estivesse prestes a retornar resultados.

### Perguntas Respondidas sobre Grande Volume

**Deve haver hard cap no frontend para UFs ou date range?**

Recomendacao: **NAO** implementar hard cap, mas sim **soft warning** (FE-016). Razoes:
- Usuarios B2B podem legitimamente precisar de buscas nacionais para analise de mercado
- Um hard cap seria arbitrario e frustrante -- o usuario sabe melhor o que precisa
- O backend ja tem protecoes automaticas (reducao de modalidades para >10 UFs, MAX_PAGES_PER_COMBO adaptativo)
- Melhor UX: informar o usuario sobre o tempo esperado e deixar a decisao com ele

**Formato do aviso:** Banner inline amarelo (usando tokens `bg-warning-subtle text-warning border border-warning/20`) entre o seletor de UFs e o botao de busca. Nao usar modal confirmacao -- seria interruptivo demais para uma acao frequente. Nao usar tooltip -- muito sutil, nao funciona em mobile.

---

## Deep Dive: Search Results Quality UX

### Como o Usuario Avalia Relevancia dos Resultados

**Problema central:** O usuario nao tem ferramentas para avaliar a qualidade dos resultados.

1. **Sem indicacao de score/relevancia**: O tier scoring do backend (A/B/C com pesos 1.0/0.7/0.3) nao e exposto ao frontend. Um item que fez match por Tier A ("uniforme") aparece identico a um que fez match por Tier C ("camisa"). O tipo `ProcurementItem` em `ItemsList.tsx` (linhas 6-15) nao inclui campo de score ou termos matched.

2. **Sem highlight de termos**: Analisado em FE-015. O `objeto` e exibido como texto puro sem destaque dos termos que causaram o match.

3. **Sem filtro pos-busca**: O `ItemsList` recebe apenas `jobId` e `totalFiltered`. Nao ha filtros de UF, valor, data, tipo (licitacao/ata), ou relevancia. O usuario so pode fazer nova busca do zero.

4. **Ordenacao opaca**: Os resultados vem na ordem retornada pelo backend (que ordena por data de publicacao descendente). O usuario nao sabe disso e nao pode re-ordenar. Nao ha indicacao visual da ordenacao.

5. **Tipo (licitacao/ata) oculto nos items**: Os badges de tipo aparecem apenas no `SearchSummary.tsx` como contagem agregada (ex: "150 Licita\u00e7\u00f5es", "30 Atas RP"). Nos items individuais, o campo `tipo` e recebido na interface `ProcurementItem` (linha 13) mas **nunca renderizado**. O usuario nao consegue distinguir licitacoes de atas na lista.

6. **Informacao de truncamento escondida**: O `SourceBadges` mostra warning sobre combos truncados (linhas 110-113), mas essa informacao esta escondida atras do toggle "fontes consultadas" (`expanded` state, default false). O usuario pode nao perceber que esta vendo resultados parciais e tomar decisoes com base em dados incompletos.

### Falsos Positivos -- Perspectiva do Usuario

O DRAFT documenta corretamente que termos customizados desabilitam exclusoes (main.py linha 543). Do ponto de vista UX:

- O usuario que busca "camisa" vera items como "confeccao de camisa de forca" sem nenhuma indicacao visual de que isso pode ser um falso positivo
- Sem highlight de termos, o usuario precisa ler cada `objeto` inteiro para avaliar relevancia
- Para 1000+ resultados, isso e impraticavel -- 50+ paginas de 20 items cada
- O truncamento de `line-clamp-2` em `ItemsList.tsx` agrava o problema: o contexto do match pode estar truncado

**Recomendacoes imediatas:**
1. Expor o campo `tipo` nos cards de resultado (1h)
2. Implementar highlight de termos (FE-015, 4h)
3. Considerar re-ordenacao e filtragem client-side para futuro proximo

---

## Deep Dive: Acentuacao UX

### Input de Busca

**Status: Funcional.** Verificado no codigo:

1. `SearchForm.tsx` linha 124-135: O `onChange` handler faz `.trim().toLowerCase()` mas **preserva acentos**. "Licita\u00e7\u00e3o" se torna "licita\u00e7\u00e3o" (com cedilha preservada, apenas lowercase).

2. Os chips de termos (linhas 96-117) exibem o texto exatamente como digitado (apos lowercase): "licita\u00e7\u00e3o" com acentos intactos.

3. Nao ha normalizacao visual de acentos no frontend -- o usuario ve exatamente o que digitou. Isso e **correto** e nao deve mudar.

### Historico de Busca (Saved Searches)

**Status: Funcional com ressalva.** Os termos sao salvos em localStorage via `savedSearches.ts` com os termos originais (incluindo acentos). `useSearchForm.ts` `loadSearchParams` (linhas 157-182) restaura termos preservando acentos.

**Ressalva:** A funcao `loadSearchParams` (linha 174) faz split por virgula e depois `trim().replace(/^"|"$/g, "")`. Para termos com acentos e aspas como `"licita\u00e7\u00e3o"`, o parsing funciona corretamente. Porem, para termos com virgula interna (improvavel mas possivel em frases longas), o split quebraria o termo.

### Display de Resultados

**Status: Correto.** Os textos de `objeto`, `orgao`, `uf` vem diretamente da API PNCP sem transformacao. O PNCP retorna textos com acentuacao nativa do portugues brasileiro. Verificado que `ItemsList.tsx` renderiza `item.objeto` diretamente (linha 79) sem transformacao.

### Inconsistencia Textual Encontrada

O heading `"Licitacoes Encontradas"` em `ItemsList.tsx` linha 63 esta **sem acentos** (falta cedilha e til), enquanto `page.tsx` linha 120 usa `"Busca de Licita\u00e7\u00f5es"` com acentos corretos. Documentado como FE-018.

### Avaliacao Geral

| Aspecto | Status | Acao Necessaria |
|---------|--------|-----------------|
| Digitacao de acentos no input | Funcional | Nenhuma |
| Chips com acentos | Funcional | Nenhuma |
| Normalizacao para matching | Funcional (backend normalize_text em ambos os lados) | Nenhuma |
| Display de resultados (PNCP) | Correto (acentos preservados) | Nenhuma |
| Historico com acentos | Funcional | Nenhuma |
| Heading "Licitacoes Encontradas" | **Bug** -- falta acentos | Corrigir (FE-018) |
| Indicacao ao usuario sobre acentos opcionais | Ausente | Considerar adicionar hint |

**Recomendacao adicional:** Adicionar uma nota sutil no hint do campo de termos: "Acentos sao opcionais -- 'licitacao' e 'licita\u00e7\u00e3o' retornam os mesmos resultados." Isso reduziria incerteza do usuario e e especialmente util para quem usa teclados internacionais sem acentos.

---

## Respostas ao Architect

### Pergunta 1: LoadingProgress suficiente para buscas de 5+ minutos? ETA preciso?

O LoadingProgress e **uma das melhores implementacoes de loading state** para este tipo de aplicacao. O UfGrid visual, curiosity carousel contextual, e progress bar criam uma experiencia engajante que mantém o usuario informado. Porem, para buscas de 5+ minutos, dois problemas:

1. **ETA pos-fetching e impreciso** (hardcoded em `~15s/~10s/~5s` independente do volume de dados). Para 85K items, filtering pode levar 30-60s. O usuario vera "~15s restantes" por muito mais que 15s, gerando desconfianca e percepcao de que o sistema travou.

2. **Sem indicacao de progresso dentro da fase de filtering**. O backend envia `items_filtered` via progress updates, e o frontend recebe esse valor (`useSearchJob.ts` linha 187), e o `ProgressBar` ate exibe "X licita\u00e7\u00f5es filtradas" (linhas 50-51). Porem, a barra de progresso permanece fixa em 60% durante toda a fase de filtering, nao acompanhando o aumento de `items_filtered`. A barra deveria interpolar entre 60-75% baseada na proporcao `itemsFiltered / itemsFetched`.

**Recomendacao:** Tornar ETAs das fases pos-fetching dinamicos baseados no volume de items. Se `itemsFetched > 10000`, multiplicar as estimativas base por `Math.ceil(itemsFetched / 5000)`. Para a barra de progresso, usar `itemsFiltered / itemsFetched` como proxy de progresso real na fase de filtering.

### Pergunta 2: Limites proativos -- abordagem UX (banner, tooltip, modal?)

**Formato recomendado: Banner inline.**

| Formato | Preos | Contras | Recomendacao |
|---------|-------|---------|--------------|
| Tooltip | Nao-intrusivo | Muito sutil, facil de perder. Nao funciona em mobile/touch. | NAO |
| Modal de confirmacao | Impossivel ignorar | Cria "confirmation fatigue" apos 2-3 usos. Interruptivo para usuarios frequentes. | NAO |
| Banner inline | Visivel sem bloquear. Estilo consistente com o design system. Funciona em mobile. | Pode ser ignorado pelo usuario. | SIM |

**Especificacao do banner:**
- Posicao: entre o `UfSelector` e o botao de busca
- Trigger: `ufsSelecionadas.size > 10` OU `dateDiffInDays(dataInicial, dataFinal) > 30`
- Estilo: `bg-warning-subtle text-warning border border-warning/20 rounded-card p-3`
- Conteudo: icone + texto informativo com estimativa de tempo
- Comportamento: nao bloqueante, desaparece quando criterios ficam abaixo do threshold

### Pergunta 3: Badges de tipo confusos? EmptyState compreensivel?

**Badges de tipo (licitacao/ata):** Os badges no `SearchSummary` sao claros em contexto ("150 Licita\u00e7\u00f5es", "30 Atas RP"). O problema nao e confusao -- e **ausencia de tipo nos items individuais**. O campo `tipo` e recebido pela interface `ProcurementItem` (linha 13 de `ItemsList.tsx`) mas nunca renderizado nos cards. Um usuario B2B precisa saber se um item e licitacao ou ata para priorizar corretamente. Recomendacao: adicionar badge de tipo em cada card (1h de esforco).

**EmptyState:** O filter breakdown com contagens e tips e excelente e compreensivel. A unica falha e o default `sectorName = "uniformes"` (linha 18 de `EmptyState.tsx`) que, quando recebe `"Licita\u00e7\u00f5es"` da busca por termos customizados, gera texto redundante "Nenhuma licita\u00e7\u00e3o de licita\u00e7\u00f5es encontrada". Recomendacao: aceitar `searchTerms: string[]` como prop alternativa e exibir "Nenhum resultado para 'termo1, termo2'" quando em modo termos.

### Pergunta 4: Design para erro de paginacao (FE-005)

**Recomendacao: Inline error com retry button** dentro do container da lista.

| Opcao | Avaliacao |
|-------|-----------|
| Toast notification | Desaparece rapido demais (3-5s), usuario pode perder. Nao permite retry direto. |
| Banner no topo da pagina | Desconexo da acao que falhou. Confuso quando multiplos erros. |
| Inline retry (recomendado) | Aparece exatamente onde os resultados deveriam estar. Contexto claro. |

**Design proposto:**
```
+-----------------------------------------------+
|  [icone erro]  Nao foi possivel carregar os    |
|  itens desta pagina.                           |
|  [Tentar novamente]                            |
+-----------------------------------------------+
```

Implementacao: adicionar estado `error: string | null` ao `ItemsList`, capturar a mensagem no catch, exibir com `role="alert"`, e oferecer botao que chama `fetchPage(page)`. Adicionar `Sentry.captureException(e)` no catch. Total: 2h conforme estimado.

### Pergunta 5: ink-muted contraste -- aceitavel para metadados?

**WCAG AA deve ser atendido estritamente (4.5:1).** Razoes:

1. Os "metadados" em questao incluem **valores monetarios** (R$ X.XXX) e **datas de publicacao** que sao informacao de decisao para o usuario B2B. Nao sao decorativos.
2. `ink-muted` e usado em `Pagination.tsx` para "Mostrando X-Y de Z itens" -- informacao de contexto que o usuario precisa para navegar.
3. Telas em ambientes corporativos com luz forte reduzem contraste perceptivel.
4. Legislacao brasileira (LBI 13.146/2015) referencia WCAG como padrao de acessibilidade.

**Acao:** Alterar `--ink-muted` no `:root` de `#5a6a7a` para `#4f5f6f` (atinge ~4.8:1 contra branco). Impacto visual: imperceptivel para usuarios com visao normal. Os outros temas ja estao adequados (paperwhite 4.6:1, sepia 5.2:1, dark usa `#8a99a9` contra `#1a1d22` que precisa verificacao separada).

### Pergunta 6: Normalizar acentos visualmente no input?

**NAO.** Normalizar visualmente o input criaria confusao ("eu digitei 'licita\u00e7\u00e3o' mas aparece 'licitacao'?"). O correto e o approach atual: preservar o que o usuario digitou e normalizar silenciosamente no backend. Adicionar apenas um **hint textual** informando que acentos sao opcionais.

### Pergunta 7: Tema Dim -- identidade visual distinta do Dark?

O tema Dim **deveria** ter identidade visual distinta do Dark. Atualmente, com apenas `--canvas` e `--surface-0` diferentes (`#2A2A2E` vs `#121212`), o usuario que alterna entre Dim e Dark percebe diferenca minima -- apenas o fundo muda ligeiramente. Todos os textos, borders, badges, e cards ficam identicos.

**Recomendacao minima (2h):**
```css
html[data-theme="dim"] {
  --canvas: #2A2A2E;
  --surface-0: #2A2A2E;
  --surface-1: #32323a;      /* mais claro que dark #1a1d22 */
  --surface-2: #3a3a42;      /* mais claro que dark #242830 */
  --surface-elevated: #2e2e34;
  --border: rgba(255, 255, 255, 0.12);  /* mais sutil que dark */
  --ink-secondary: #b0bcc8;  /* mais claro que dark #a8b4c0 */
}
```

Isso criaria uma experiencia "twilight" distinta: superficies mais claras com maior contraste entre camadas, dando ao Dim uma personalidade propria de "conforto noturno sem escuridao total".

---

## Recomendacoes de Design (Priorizadas)

### P1 -- Critico (resolver antes de producao)

| # | Item | Esforco | Justificativa |
|---|------|---------|---------------|
| 1 | FE-005: Corrigir error swallowing em ItemsList | 2h | Usuario preso em loading infinito ou lista vazia sem feedback. Nenhum log para debug. |
| 2 | FE-016: Advertencia para buscas de grande volume | 3h | Previne abandono, frustacao, e uso desnecessario de recursos do servidor |
| 3 | Alinhar frontend timeout com backend timeout (DRAFT rec. 1) | 4h | Race condition confirmada: frontend 10min vs backend 10.5min para 27 UFs |

### P2 -- Alto impacto (resolver no proximo sprint)

| # | Item | Esforco | Justificativa |
|---|------|---------|---------------|
| 4 | FE-001: Corrigir cores hardcoded em SearchSummary | 1h | Ilegibilidade em 3 de 5 temas (paperwhite, sepia, dim) |
| 5 | FE-007: Corrigir ink-muted para WCAG AA | 1h | Acessibilidade -- afeta leitura de valores monetarios e datas |
| 6 | FE-015: Highlight de termos de busca nos resultados | 4h | Permite avaliacao rapida de relevancia, reduz impacto de falsos positivos |
| 7 | Expor campo `tipo` (licitacao/ata) nos cards de resultado | 1h | Informacao de decisao B2B atualmente oculta |
| 8 | FE-017: Enriquecer mensagem de timeout com contexto | 2h | Orientacao especifica vs generica |

### P3 -- Qualidade (backlog priorizado)

| # | Item | Esforco | Justificativa |
|---|------|---------|---------------|
| 9 | ETA dinamico baseado em volume de items | 2h | Evita ETAs enganosos ("~15s" quando faltam 60s) |
| 10 | FE-006: Button component | 3h | Previne drift de estilos entre variantes de botao |
| 11 | FE-019: AbortController para pagination race conditions | 2h | Previne exibicao de dados stale em navegacao rapida |
| 12 | FE-004: Spinner component | 1h | Consistencia visual, eliminacao de duplicacao |
| 13 | FE-008: Link /termos quebrado | 2h | Link quebrado visivel em todas as paginas |
| 14 | FE-011: Teste SourceBadges | 2h | Componente complexo sem teste dedicado |
| 15 | Corrigir EmptyState para modo termos customizados | 1h | Texto redundante "nenhuma licitacao de licitacoes" |

### P4 -- Refinamento

| # | Item | Esforco | Justificativa |
|---|------|---------|---------------|
| 16 | FE-012: Dim theme com identidade propria | 2h | Diferenciacao de Dark |
| 17 | FE-018: Acento no heading ItemsList | 0.25h | Inconsistencia textual |
| 18 | Hint sobre acentos opcionais no campo de termos | 0.5h | Reduz incerteza do usuario |
| 19 | FE-002: Cor hardcoded SourceBadges | 0.5h | Quick win de consistencia |
| 20 | FE-009: Fallback para dynamic imports | 1h | Protecao contra chunk load failure |

**Esforco total novas recomendacoes (FE-015 a FE-019 + items nao-FE): ~23h**
**Esforco total estimado incluindo FE existentes: ~50h**

---

## Nota sobre Itens Resolvidos desde a Review Anterior (Vera)

Os seguintes itens da review anterior (UXD-*) foram **resolvidos** no codebase atual e nao precisam mais constar como debitos:

| UXD antigo | Status | Evidencia |
|------------|--------|-----------|
| UXD-002: Sem loading state para setores | **RESOLVIDO** | `SearchForm.tsx` linhas 64-72: spinner + "Carregando setores..." + aria-busy |
| UXD-003: Sem pagina 404 | **RESOLVIDO** | `not-found.tsx` existe |
| UXD-004: Sem atalho de teclado | **RESOLVIDO** | `page.tsx` linhas 79-88: Ctrl+Enter |
| UXD-005: SavedSearchesDropdown sem ARIA listbox | **RESOLVIDO** | Full listbox pattern com role="listbox", role="option", aria-activedescendant |
| UXD-006: SaveSearchDialog sem `<dialog>` | **RESOLVIDO** | Usa `<dialog>` nativo com showModal() |
| UXD-008: Mixpanel importado incondicionalmente | **RESOLVIDO** | Lazy loaded via dynamic import |
| UXD-010: ThemeProvider imperativo | **RESOLVIDO** | CSS cascade via data-theme attribute |
| UXD-011: Script FOUC duplica logica | **RESOLVIDO** | Ambos usam mesmo mecanismo (data-theme + .dark class) |
| UXD-012: Sem indicador offline | **RESOLVIDO** | NetworkIndicator component |
| UXD-016: LoadingProgress 450+ linhas | **RESOLVIDO** | Decomposto em 5 sub-components, orquestrador com 141 linhas |
| UXD-017: Setores fallback hardcoded | **RESOLVIDO** | Centralizado em constants/fallback-setores.ts |
| UXD-019: carouselData cores hardcoded | **RESOLVIDO** | Migrado para CSS custom properties (--cat-* tokens) |

**UXD-001 (termos multi-palavras impossivel)** permanece aberto e e um problema UX real. O SearchForm.tsx (linha 126) ainda usa espaco como delimitador de tokens. Porem, este item nao esta listado no DRAFT FE-* consolidado. **Recomendo que o architect avalie se deve ser adicionado como FE-020.**

---

**Review Status: COMPLETE**
**Reviewer:** @ux-design-expert (Pixel)
**Signed:** 2026-03-09
**Next step:** Consolidation by @architect into final technical-debt.md
