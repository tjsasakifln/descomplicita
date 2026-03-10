# Relatorio de Debito Tecnico

**Projeto:** Descomplicita
**Data:** 2026-03-09
**Versao:** 1.0
**Preparado por:** @analyst (Athena) -- Business Analyst
**Baseado em:** Technical Debt Assessment FINAL v1.0 (validado por @architect Atlas, @data-engineer Delphi, @ux-design-expert Pixel, @qa Quartz)
**Commit de referencia:** 5e56b38d

---

## Executive Summary

### Situacao Atual

O Descomplicita e uma plataforma SaaS de busca de licitacoes publicas brasileiras que permite empresas encontrarem oportunidades de fornecimento ao governo via o Portal Nacional de Compras Publicas (PNCP). A plataforma possui uma base tecnica madura -- 404 testes automatizados, 5 temas visuais, excelente acessibilidade (ARIA, axe-core), e uma experiencia de loading state acima da media do mercado com grid visual por estado, carrossel de curiosidades e barra de progresso com ETA. A qualidade da fundacao e real e demonstra competencia tecnica significativa.

Entretanto, uma auditoria completa conduzida por quatro especialistas independentes identificou **60 debitos tecnicos** que afetam diretamente as tres funcionalidades que definem a proposta de valor do produto: **qualidade de busca** (resultados relevantes vs. irrelevantes), **buscas de grande volume** (27 estados, 30+ dias), e **experiencia do usuario** (retencao e conversao). O banco de dados atual perde todos os dados a cada deploy, tornando impossivel qualquer modelo de assinatura. A implementacao de seguranca possui vulnerabilidades que impedem a ida para producao. E o motor de busca -- razao de existencia do produto -- apresenta taxa de falsos positivos entre 20-40% para buscas personalizadas e descarta silenciosamente ate 95,6% dos resultados disponiveis em estados de alto volume como Sao Paulo.

A descoberta mais importante da auditoria e tambem a mais promissora: o parametro `palavraChave` da API do PNCP nunca foi utilizado pelo sistema. Se funcionar, o volume de dados processados cai entre 10 e 20 vezes, eliminando ou reduzindo drasticamente varios dos problemas mais caros do inventario. Testar este parametro leva 2 horas e custa R$ 300. E potencialmente a acao de maior retorno sobre investimento de todo o projeto.

### Numeros Chave

| Metrica | Valor |
|---------|-------|
| Total de debitos identificados | **60** (24 Sistema + 16 Banco de Dados + 20 Frontend) |
| Debitos criticos (bloqueiam producao) | **4** |
| Debitos de alta prioridade (degradam valor) | **12** |
| Debitos de media prioridade | **24** |
| Debitos de baixa prioridade | **20** |
| Horas totais estimadas | **~255 horas** |
| Horas para criticos + altos | **~100 horas** |
| Custo total (R$150/h) | **R$ 38.250** |
| Custo criticos + altos | **R$ 15.000** |
| Custo Sprints 1-3 (resolucao planejada) | **R$ 20.550** |
| Timeline de execucao | **3 sprints em 6-8 semanas** |

### Recomendacao

Recomendamos a aprovacao imediata do orcamento para os **Sprints 1 e 2** (R$ 15.150, 6 semanas), que resolvem todos os 16 itens criticos e altos, habilitam persistencia de dados via Supabase PostgreSQL, e melhoram significativamente a qualidade de busca e a experiencia de grande volume. A execucao deve comecar pelo teste do parametro `palavraChave` (2 horas, R$ 300), cujo resultado pode alterar todas as prioridades subsequentes. Adiar esta resolucao custa entre R$ 100.000 e R$ 350.000 ao longo de 12 meses em receita perdida, riscos de seguranca e perda competitiva -- 5 a 17 vezes o investimento necessario para resolver.

---

## Impacto nas Funcionalidades Core

Estes tres pilares sao a razao pela qual o usuario paga pelo produto. Os debitos identificados afetam exatamente o que o Descomplicita promete entregar.

### Qualidade de Busca

A proposta de valor central do Descomplicita e simples: ajudar empresas a encontrar licitacoes relevantes. Quando a busca retorna resultados errados ou esconde oportunidades reais, o produto falha na sua missao fundamental.

**Resultados irrelevantes (falsos positivos) -- 20-40% para buscas personalizadas:**

O sistema utiliza conjuntos de palavras-chave com niveis de confianca (termos inequivocos, termos fortes e termos ambiguos) e listas de exclusao por setor para filtrar resultados. O mecanismo e sofisticado e funciona bem para buscas pre-configuradas. Entretanto, quando o usuario digita termos personalizados, **o sistema desativa completamente os filtros de exclusao por setor**. Isso significa que uma busca por "confeccao" retorna "confeccao de placas de sinalizacao" misturada com resultados de vestuario.

Alem disso, o calculo de relevancia para termos ambiguos possui uma falha conceitual: quando um resultado contem tres termos fracos (ex: "bota + meia + avental"), o sistema calcula a relevancia com base apenas no melhor termo individual (0.3 de 1.0), em vez de somar os tres. O resultado e sistematicamente rejeitado (0.3 < limiar de 0.6), mesmo sendo claramente relevante.

**Para o usuario, isto significa:** a cada 10 resultados de uma busca personalizada, 2 a 4 sao irrelevantes. O usuario perde tempo avaliando licitacoes que nao interessam. A confianca no produto erode gradualmente. E licitacoes genuinamente relevantes que combinam termos ambiguos nunca aparecem.

**Resultados relevantes perdidos (falsos negativos) -- ate 95,6% em estados de alto volume:**

Tres fatores causam perda silenciosa de oportunidades:

1. **Truncamento de volume:** O sistema busca no maximo 500 licitacoes por combinacao de estado e modalidade. Para Sao Paulo com Pregao Eletronico, existem ate 11.400 resultados -- o sistema descarta 95,6% sem que o usuario saiba. Oportunidades de negocio sao silenciosamente perdidas.

2. **Ausencia de reconhecimento gramatical:** O sistema nao reconhece variantes de palavras. "Uniformizado" nao aparece quando se busca "uniforme". "Confeccionado" nao aparece para "confeccao". Toda uma classe de licitacoes relevantes e invisivel.

3. **Parametro `palavraChave` nao utilizado:** Toda a filtragem e feita localmente apos buscar todos os resultados da API. Se o parametro `palavraChave` da API PNCP for utilizado, o volume de dados cai 10-20x, eliminando o problema de truncamento e reduzindo drasticamente o tempo de processamento.

**Acentuacao (ponto positivo confirmado):**

A busca trata acentos corretamente em todas as camadas -- "licitacao" e "licitacao" (com cedilha e til) retornam resultados identicos. A normalizacao Unicode cobre todas as diacriticas do portugues brasileiro. Nao ha falhas. A unica recomendacao e informar o usuario sobre isto com uma dica sutil no campo de busca, reduzindo incerteza especialmente para usuarios com teclados internacionais.

**Impacto direto no negocio:**
- Usuarios perdem confianca ao ver resultados irrelevantes misturados com oportunidades reais
- Oportunidades de negocio sao perdidas silenciosamente por truncamento -- o usuario nem sabe que existiam
- Competidores com busca mais precisa capturam clientes insatisfeitos
- Para um SaaS de busca, a qualidade dos resultados e literalmente o que o cliente paga para ter

### Buscas de Grande Volume

Usuarios que buscam em **27 estados** com janela de **30+ dias** sao provavelmente os mais engajados e potencialmente os clientes premium ou enterprise. Representam maior receita por usuario e maior lifetime value. Sao exatamente estes usuarios que enfrentam os piores problemas.

**O resultado que o usuario nunca ve (race condition de timeout):**

Quando um usuario busca em 27 estados, o backend precisa de ate 10 minutos e 30 segundos para processar. Mas o frontend desiste aos 10 minutos exatos. Existe uma janela de 30 segundos onde o backend completa com sucesso, armazena os resultados no cache, mas o usuario ja viu a mensagem "A consulta excedeu o tempo limite" e saiu. Minutos de processamento desperdicados. Resultados prontos que ninguem vera.

**O servidor que pode cair (pressao de memoria):**

Uma unica busca de 27 estados por 90 dias consome ate **460MB de memoria**. O servidor tem 512MB. Os dados sao armazenados duplamente -- uma copia em Python e outra no cache Redis. Para 85.000 itens, sao ~120MB desnecessarios na copia Python. Duas buscas grandes simultaneas (920MB) derrubam o sistema para todos os usuarios.

**A barra de progresso que mente (ETA impreciso):**

As estimativas de tempo sao fixas: "faltam ~15 segundos" independente do volume. Para 85.000 itens, a filtragem leva 30-60 segundos, nao 15. A barra de progresso trava em 60% durante o processamento. O usuario conclui que o sistema travou e abandona a busca, ou aciona suporte.

**O aviso que nao existe (sem advertencia proativa):**

O usuario seleciona 27 estados + 90 dias e clica em buscar. Nenhum banner, nenhuma estimativa de tempo, nenhuma sugestao de reduzir o escopo. Nenhuma indicacao de que a busca sera demorada ou que pode exceder limites do sistema. O usuario descobre os problemas da pior forma possivel: esperando.

**Impacto direto no negocio:**
- Usuarios premium (3-5x receita media) tem a pior experiencia da plataforma
- Abandono de buscas longas gera percepcao de produto instavel
- Risco de indisponibilidade por OOM afeta todos os usuarios, nao apenas quem fez a busca grande
- Custo de infraestrutura elevado sem necessidade -- se `palavraChave` funcionar, o volume cai drasticamente

### Experiencia do Usuario

Alem dos problemas de busca e grande volume, a experiencia geral apresenta falhas que afetam diretamente retencao e conversao.

**Erro silencioso na listagem de resultados (CRITICO):**

Quando a paginacao de resultados falha -- seja por timeout, erro de memoria ou falha de rede -- o sistema engole o erro silenciosamente. Sem mensagem. Sem botao de retry. Sem logging. O usuario ve "Carregando..." para sempre e conclui que o produto nao funciona. Este e o tipo de experiencia que causa abandono imediato e permanente. E especificamente para buscas de grande volume, onde paginacao e essencial, o impacto e inaceitavel.

**Impossivel avaliar rapidamente a relevancia dos resultados:**

Os termos de busca nao sao destacados nos resultados. O campo "objeto" exibe texto puro, sem nenhuma indicacao visual de por que aquela licitacao foi retornada. Em uma lista com centenas de resultados, o usuario precisa ler cada descricao inteira para avaliar relevancia. Isto multiplica por 3 a 5 vezes o tempo de avaliacao e dificulta a identificacao de falsos positivos -- o usuario nao consegue distinguir rapidamente um resultado bom de um ruim.

**Termos compostos nao funcionam pela interface:**

O usuario quer buscar "camisa polo" (duas palavras, um conceito). Ao digitar no campo de busca, o espaco cria dois tokens separados: "camisa" e "polo". O backend ja suporta termos compostos via aspas, mas a interface nao oferece nenhuma forma de usar esta funcionalidade. O campo de busca nao menciona aspas, virgulas, ou qualquer mecanismo de agrupamento. Resultado: buscas imprecisas para necessidades especificas.

**Contraste abaixo do padrao de acessibilidade:**

Valores monetarios e datas -- exatamente as informacoes mais importantes para o usuario B2B -- usam uma cor com contraste de 4.1:1, abaixo do minimo de 4.5:1 exigido pelo padrao WCAG AA. Usuarios com baixa visao ou em ambientes com muita luz tem dificuldade para ler dados financeiros.

**Buscas salvas existem apenas no navegador:**

Todas as buscas salvas residem no localStorage do navegador. Trocar de dispositivo, limpar dados ou usar outro navegador significa perder todas as configuracoes. Nao ha sincronizacao. Para um usuario que acessa de multiplos dispositivos (escritorio e celular), a funcionalidade e fragil.

**Impacto direto no negocio:**
- Erro silencioso de paginacao causa abandono imediato e gera percepcao de produto quebrado
- Falta de highlight aumenta custo cognitivo por resultado, reduzindo produtividade do usuario
- Problemas de acessibilidade podem ter implicacoes legais (Lei Brasileira de Inclusao 13.146/2015)
- Perda de buscas salvas frustra usuarios recorrentes e reduz stickiness do produto

---

## Analise de Custos

### Custo de RESOLVER

| Categoria | Itens | Horas Estimadas | Custo (R$150/h) |
|-----------|-------|-----------------|-----------------|
| Sistema (infraestrutura, seguranca, arquitetura) | 24 | ~109h | R$ 16.350 |
| Banco de Dados e Busca (persistencia, qualidade) | 16 | ~49h | R$ 7.350 |
| Frontend/UX (interface, experiencia) | 20 | ~33h | R$ 4.950 |
| Investigacoes e validacao (spikes, golden test suite) | -- | ~14h | R$ 2.100 |
| Reserva para contingencias (~15%) | -- | ~38h | R$ 5.700 |
| **TOTAL** | **60** | **~255h (+38h reserva)** | **R$ 43.950** |

**Nota:** O custo sem reserva de contingencia e R$ 38.250. A reserva cobre riscos de descobertas adicionais durante a migracao Supabase e complexidades nao previstas. O investimento planejado para os 3 sprints prioritarios (excluindo backlog) e R$ 20.550.

### Custo de NAO RESOLVER (Risco Acumulado)

| Risco | Probabilidade | Impacto | Custo Potencial (12 meses) |
|-------|---------------|---------|----------------------------|
| **Perda de dados a cada deploy** -- banco efemero impede modelo de assinatura | Certa (100%) | Critico | Impossibilita receita recorrente. Todo o modelo SaaS e inviavel. |
| **Brecha de seguranca** -- JWT sem padrao, timing attack, sem rotacao de chaves | Alta (70%) | Critico | R$ 50.000 - R$ 200.000 (resposta a incidente, dano reputacional, potencial multa LGPD) |
| **Churn por busca de baixa qualidade** -- 20-40% de falsos positivos em buscas customizadas | Alta (60%) | Alto | 15-30% da base perdida em 6 meses. Para 100 usuarios a R$200/mes: R$ 36.000 - R$ 72.000/ano |
| **Perda de usuarios premium** -- experiencia de grande volume degradada | Alta (60%) | Alto | Usuarios enterprise representam 3-5x receita media. R$ 10.000 - R$ 30.000/ano |
| **Queda do servidor** -- OOM em busca grande (460MB de 512MB disponiveis) | Media (40%) | Alto | Indisponibilidade total. R$ 5.000 - R$ 15.000 por incidente |
| **Perda competitiva** -- concorrente com busca superior captura mercado | Media (40%) | Alto | Perda gradual de market share. Custo de reconquista: 5-7x custo de retencao |
| **Resultados relevantes perdidos** -- 95,6% truncados em SP sem que usuario saiba | Alta (80%) | Alto | Oportunidades de negocio invisiveis. Impacto no valor percebido do produto |

**Resumo:** O custo de nao resolver e estimado em **R$ 100.000 - R$ 350.000** ao longo de 12 meses. O investimento para resolver os 3 sprints prioritarios (R$ 20.550) representa **6-17%** do custo de inacao. O ratio custo/beneficio e de **1:5 a 1:17**.

---

## Impacto no Negocio

### Performance

| Problema | Situacao Atual | Apos Resolucao |
|----------|---------------|----------------|
| Paginacao de resultados grandes | ~5 segundos (carrega todos os itens na memoria) | < 200ms (leitura direta do cache via Redis LIST) |
| Memoria do servidor por busca grande | ~460MB (limite do servidor: 512MB) | < 300MB (eliminando duplicacao Python/Redis) |
| Tempo de busca em 27 UFs | 4-7 minutos (resultado pode ser perdido por timeout) | Mesmo tempo, mas com timeout alinhado e aviso previo |
| Volume de dados processados | 100% dos resultados da API (filtro apenas local) | 5-10% (se `palavraChave` funcionar -- reducao de 10-20x) |
| Chamadas de IA | Sem limite de tempo (pode travar indefinidamente) | Timeout configurado, sem risco de travamento |

### Seguranca

| Problema | Risco para o Negocio | Resolucao Planejada |
|----------|---------------------|---------------------|
| JWT implementado manualmente, sem padrao | Tokens podem ser forjados; sem rotacao de chaves | Adotar biblioteca PyJWT com rotacao, audience e issuer |
| Comparacao de chave vulneravel a timing attack (2 pontos no codigo) | Atacante pode descobrir a chave API caractere por caractere | Usar comparacao de tempo constante (hmac.compare_digest) |
| Headers de seguranca ausentes (CSP, HSTS) | Vulneravel a ataques XSS, clickjacking, downgrade HTTPS | Adicionar headers padrao da industria |
| Bypass de autenticacao quando variaveis nao configuradas | Sistema totalmente exposto se credenciais esquecidas | Bloquear startup sem credenciais |

### Experiencia do Usuario

| Problema | Impacto na Retencao | Prioridade |
|----------|---------------------|------------|
| Erro silencioso na paginacao | Abandono imediato -- usuario preso em "Carregando..." sem saida | Critica -- Sprint 1 |
| Sem destaque de termos nos resultados | Avaliacao de relevancia 3-5x mais lenta | Alta -- Sprint 2 |
| Sem aviso para buscas de grande volume | Abandono por falta de expectativa de tempo | Alta -- Sprint 2 |
| Buscas salvas apenas no navegador | Sem continuidade entre dispositivos | Alta -- Sprint 2 |
| Termos compostos impossiveis pela interface | Busca imprecisa para necessidades especificas | Media -- Sprint 3 |
| Contraste abaixo de WCAG AA em valores monetarios | Usuarios com baixa visao nao leem dados financeiros | Alta -- Sprint 2 |

### Manutenibilidade

| Problema | Impacto no Time de Desenvolvimento |
|----------|-------------------------------------|
| Banco de dados sem sistema de migracao | Cada mudanca de schema e manual e arriscada (CREATE TABLE IF NOT EXISTS) |
| 115 entradas redundantes nos filtros de busca | Risco de atualizar uma variante e esquecer a outra |
| Testes de integracao sao placeholder | Regressoes descobertas apenas em producao |
| Dual-write entre Python e Redis sem invalidacao | Complexidade desnecessaria; bugs de sincronizacao inevitaveis |

---

## Timeline Recomendado

### Sprint 1: Quick Wins + Fundacao Critica (2-4 semanas)

**Investimento:** ~65 horas | **R$ 9.750**
**Objetivo:** Eliminar riscos criticos, habilitar persistencia de dados, e realizar a investigacao de maior ROI do projeto.

| Acao | Horas | Por que agora |
|------|-------|---------------|
| **Testar parametro `palavraChave` da API PNCP** | 2h | Pode reduzir volume de dados 10-20x. Resultado muda todas as prioridades. **R$ 300 de investimento que pode economizar R$ 5.000 - R$ 10.000.** |
| Corrigir erro silencioso na listagem (FE-005) | 2h | Usuarios presos em "Carregando..." sem explicacao. Pre-requisito para que problemas de paginacao e memoria se tornem visiveis. |
| Corrigir vulnerabilidades JWT e timing attack (SYS-003 + DB-005 + DB-014) | 5h | Seguranca basica. Bloqueiam ida para producao. Correcoes rapidas e independentes. |
| Migrar banco de dados para Supabase PostgreSQL (SYS-001 + DB-001 + DB-002 + DB-003) | 24-32h | Resolve 7 problemas de uma vez: persistencia, isolamento multi-usuario, sistema de migracoes, backups automaticos, e 3 itens menores. |
| Alinhar timeout frontend com backend | 3h | Elimina janela de 30 segundos onde resultados sao processados mas usuario ja desistiu. |
| Projetar modelo de identidade de usuario (SYS-002) | 24h | Base para contas, assinaturas e personalizacao. Desenvolver em paralelo com migracao Supabase. |

**Resultado esperado:** Dados persistem entre deploys. Usuarios identificados individualmente. Seguranca basica garantida. Erros de paginacao visiveis. Parametro `palavraChave` avaliado.

### Sprint 2: Qualidade de Busca e UX Critica (2-3 semanas)

**Investimento:** ~36 horas | **R$ 5.400**
**Objetivo:** Melhorar significativamente a qualidade dos resultados e a experiencia de grandes volumes.

| Acao | Horas | Por que agora |
|------|-------|---------------|
| Paginacao eficiente via Redis LIST (DB-009) | 6h | Reduz consumo de memoria de ~100MB para kilobytes por pagina. |
| Reativar filtros de exclusao para buscas customizadas | 3h | Reduz resultados irrelevantes em 20-40% para termos personalizados. |
| Aviso proativo para buscas de grande volume (FE-016) | 3h | Banner inline quando usuario seleciona >10 estados ou >30 dias. |
| Destacar termos de busca nos resultados (FE-015) | 5h | Usuario avalia relevancia 3-5x mais rapido. Requer 1h backend + 4h frontend. |
| Corrigir contraste e cores de temas (FE-001 + FE-007) | 2h | Acessibilidade WCAG AA para valores monetarios e datas. |
| Hardening de seguranca -- CORS, CSP, HSTS, auth bypass (SYS-004 + SYS-005 + SYS-007) | 7h | Protecao contra ataques web comuns. |
| Timeout em chamadas de IA (SYS-010) | 2h | Previne travamento do sistema aguardando resposta da OpenAI. |
| Buscas salvas no servidor (SYS-006) | 8h | Sincronizacao entre dispositivos. Depende da migracao Supabase do Sprint 1. |

**Resultado esperado:** Busca mais precisa (20-40% menos falsos positivos). Usuarios de grande volume informados antes de buscar. Interface mais acessivel. Buscas salvas persistentes e sincronizadas.

### Sprint 3: Otimizacao e Refinamento (2-3 semanas)

**Investimento:** ~36 horas | **R$ 5.400**
**Objetivo:** Eliminar classe inteira de falsos negativos, reduzir consumo de memoria, e polir a experiencia.

| Acao | Horas | Por que agora |
|------|-------|---------------|
| Implementar reconhecimento de variantes gramaticais -- stemming PT-BR (RSLP/NLTK) | 10h | "Uniformizado" passa a encontrar "uniforme". Novas oportunidades antes invisiveis. |
| Eliminar duplicacao de dados na memoria (DB-015) | 3h | Reduz ~120MB de consumo desnecessario por busca grande. |
| Protecao contra dados desatualizados na paginacao (FE-019) | 2h | Navegacao rapida nao exibe dados de outra pagina. |
| Mensagem de timeout com orientacao especifica (FE-017) | 2h | Em vez de erro generico, sugere reduzir numero de estados ou periodo. |
| Reducao de gravacoes redundantes no cache (DB-006) | 4h | Cada atualizacao de progresso regravava todo o dataset. |
| Limpeza de filtros redundantes de acentuacao | 2h | Remove 115 entradas duplicadas desnecessarias (com e sem acento do mesmo termo). |
| Melhoria no calculo de relevancia para termos ambiguos | 2h | Combinacao de 3+ termos fracos ("bota + meia + avental") passa a pontuar corretamente. |
| Componente padrao de botao (FE-006) | 3h | Previne inconsistencia visual entre telas. |
| Suporte a termos compostos na interface (FE-020) | 3h | Permitir "camisa polo" como termo unico de busca. |
| Quick wins de qualidade -- spinner, link /termos, teste SourceBadges (FE-004 + FE-008 + FE-011) | 5h | Polimento geral e cobertura de testes. |

**Resultado esperado:** Busca encontra mais resultados relevantes (stemming). Sistema mais estavel e eficiente (menos memoria). Interface mais consistente e precisa.

### Backlog (Prioridade P4/P5)

| Grupo | Descricao | Horas | Notas |
|-------|-----------|-------|-------|
| Limpeza de codigo | Versao hardcoded, MD5, fontes deprecadas, aliases Jest | 7h | Higiene tecnica |
| Infraestrutura | Limites Vercel, refactoring JobStore, retry BFF | 16h | Escalabilidade |
| Modernizacao | React 18 para 19, health check, regex engine | 18h | Longo prazo |
| Funcionalidades | Filtro deadline, OpenAPI, testes integracao, Docker, Mixpanel, logging | 29h | Evolucao |
| Banco de dados | Preferencias usuario, health check DB, cleanup, degradation | 6h | Completude |
| Dados e cache | Backup, transactions, cache keys | 4,5h | Defesa em profundidade |
| Frontend menor | Cor SourceBadges, UUID, dynamic fallback, teste RegionSelector | 3,5h | Quick wins |
| Frontend polimento | Tema Dim, SavedSearches null, page.tsx monolitico, heading acento | 6,75h | Refinamento |
| Longo prazo | Pipeline de ingestao batch PNCP (pre-computed data) | 40h | Elimina buscas on-demand. Requer Supabase. |

**Subtotal Backlog: ~131h | R$ 19.650** -- a ser priorizado conforme necessidade do negocio apos Sprints 1-3.

---

## ROI da Resolucao

| | Investimento | Retorno Esperado |
|--|-------------|------------------|
| **Spike palavraChave** | R$ 300 (2h) | Se funcionar: reducao de 10-20x no volume processado. **R$ 300 que podem economizar R$ 5.000 - R$ 10.000 em trabalho futuro e eliminar problemas de truncamento, memoria e timeout.** |
| **Sprint 1** | R$ 9.750 (65h) | Persistencia de dados habilitada. Sem persistencia, nao ha modelo de assinatura viavel. **Habilita toda a receita futura do SaaS.** |
| **Sprint 2** | R$ 5.400 (36h) | Reducao de 20-40% em falsos positivos. Retencao estimada de 15-25% mais usuarios. Para 100 usuarios a R$200/mes: **R$ 3.600 - R$ 6.000/mes em receita protegida.** |
| **Sprint 3** | R$ 5.400 (36h) | 10% mais resultados relevantes (stemming). Menos memoria consumida. **Diferenciacao competitiva em qualidade de busca.** |
| **Total Sprints 1-3** | **R$ 20.550** | **Plataforma pronta para producao, modelo SaaS viavel, qualidade de busca competitiva** |

| Comparacao | Valor |
|------------|-------|
| Investimento planejado (Sprints 1-3) | R$ 20.550 |
| Custo estimado de nao resolver (12 meses) | R$ 100.000 - R$ 350.000 |
| **Ratio custo/beneficio** | **1:5 a 1:17** |
| Payback estimado | 3-4 meses de operacao com 50+ assinantes |

---

## Proximos Passos

1. [ ] **Aprovar orcamento** -- Sprints 1 e 2 (R$ 15.150) como prioridade imediata
2. [ ] **Executar spike `palavraChave`** -- 2 horas, resultado define prioridades de todos os sprints
3. [ ] **Definir sprint backlog** -- com base no resultado do spike, confirmar ou ajustar prioridades
4. [ ] **Alocar time** -- 1-2 desenvolvedores para Sprint 1 (2-4 semanas)
5. [ ] **Iniciar Sprint 1** -- comecar por FE-005 (erro silencioso) e seguranca JWT em paralelo com planejamento Supabase
6. [ ] **Revisao pos-Sprint 1** -- avaliar resultados, confirmar Sprint 2
7. [ ] **Aprovar Sprint 3** (R$ 5.400) -- apos resultados dos Sprints 1 e 2
8. [ ] **Avaliar backlog** -- priorizar os R$ 19.650 restantes conforme necessidade do negocio

### Decisoes Necessarias

| Decisao | Responsavel | Prazo |
|---------|-------------|-------|
| Aprovar orcamento Sprints 1-2 | Diretor de Produto / CEO | Imediato |
| Resultado do spike `palavraChave` | Time de Desenvolvimento | Semana 1 |
| Modelo de identidade (design SYS-002) | CTO + Produto | Semana 1-2 |
| Credenciais e projeto Supabase | CTO / DevOps | Antes do Sprint 1 (migracao) |
| Aprovar Sprint 3 | Diretor de Produto | Semana 5-6 |

---

## Anexos

### Documentos de Referencia

| Documento | Localizacao |
|-----------|-------------|
| Assessment Tecnico Completo (60 debitos detalhados) | [`docs/prd/technical-debt-assessment.md`](../prd/technical-debt-assessment.md) |
| Inventario com severidade, horas e prioridade | Incluido no assessment (secao "Inventario Completo") |
| Matriz de dependencias entre itens | Incluido no assessment (secao "Dependencias entre Items") |
| Criterios de sucesso com metricas quantitativas | Incluido no assessment (secao "Criterios de Sucesso") |
| Fluxo de dependencias visual | Incluido no assessment (secao "Plano de Resolucao") |

### Glossario para Stakeholders

| Termo | Significado |
|-------|-------------|
| PNCP | Portal Nacional de Contratacoes Publicas -- fonte oficial dos dados de licitacoes |
| Supabase | Plataforma de banco de dados PostgreSQL na nuvem, com backups automaticos |
| Falso positivo (FP) | Resultado de busca que aparece mas nao e relevante para o usuario |
| Falso negativo (FN) | Resultado relevante que deveria aparecer mas nao aparece |
| Stemming | Tecnica que reconhece variantes gramaticais ("uniforme" encontra "uniformizado") |
| WCAG AA | Padrao internacional de acessibilidade digital (nivel intermediario) |
| SaaS | Software as a Service -- modelo de negocio por assinatura |
| Sprint | Ciclo de trabalho com duracao e entregas definidas |
| Debito tecnico | Decisoes de implementacao que funcionam hoje mas criam riscos ou custos futuros |
| OOM | Out of Memory -- quando o servidor fica sem memoria e para de funcionar |

### Metodologia

- **Taxa base:** R$ 150/hora (desenvolvedor mid-senior)
- **Estimativas:** Horas por item, validadas por 4 especialistas (arquiteto, engenheiro de dados, especialista UX, QA)
- **Riscos financeiros:** Estimados com base em benchmarks de mercado para SaaS B2G (Business-to-Government)
- **ROI:** Calculado como (riscos evitados ponderados por probabilidade) / (investimento em resolucao)
- **Commit de referencia:** Todos os detalhes tecnicos verificados contra o codigo-fonte no commit 5e56b38d

---

*Relatorio preparado em 2026-03-09 por @analyst (Athena)*
*Baseado no Technical Debt Assessment FINAL v1.0*
*Validado por: @architect (Atlas), @data-engineer (Delphi), @ux-design-expert (Pixel), @qa (Quartz)*
