# Relatorio de Debito Tecnico -- Descomplicita (POC)

**Data:** 2026-03-11
**Versao:** 2.0
**Autor:** @analyst (Lens)
**Fontes:** Assessment tecnico (@architect Atlas), revisao de banco de dados (@data-engineer Forge), revisao de UX (@ux-design-expert Pixel), gate de qualidade (@qa Shield)
**Commit de referencia:** 2a76827b (HEAD de main)

---

## Resumo Executivo

### Situacao Atual

O Descomplicita e uma plataforma de busca inteligente de licitacoes publicas brasileiras que consolida dados de multiplas fontes governamentais (PNCP, Portal da Transparencia), aplica filtragem por relevancia com inteligencia artificial e gera resumos executivos automatizados. A plataforma atende empresas e consultores que participam de processos licitatorios, simplificando uma atividade que hoje demanda horas de pesquisa manual em portais dispersos.

O sistema encontra-se em estagio de POC (Prova de Conceito) com base tecnica surpreendentemente solida: mais de 1.925 testes automatizados (1.349 backend + 576 frontend), 9 workflows de CI/CD, autenticacao com Supabase, 5 temas visuais, acessibilidade WCAG AA parcialmente validada com axe-core, monitoramento de erros com Sentry em ambos os lados, e Row Level Security habilitado em todas as tabelas do banco de dados. A arquitetura e moderna (Next.js 16 + FastAPI + Supabase + Redis) e o produto ja funciona de ponta a ponta -- da busca ao download de planilhas Excel.

Uma auditoria tecnica abrangente conduzida por quatro especialistas independentes identificou **57 debitos tecnicos**, dos quais 4 sao criticos. O mais grave afeta diretamente a experiencia de cadastro e login: o modal de autenticacao esta visualmente quebrado em temas escuros, com texto invisivel e botoes sem cor. Ha riscos de seguranca gerenciaveis (biblioteca JWT com vulnerabilidades conhecidas, arquivo de banco legado no repositorio) e questoes de manutencao (arquivo principal do backend com 1.230 linhas). A boa noticia: **o investimento minimo para tornar o produto apresentavel em uma demonstracao e de apenas 12 horas de trabalho** (R$ 1.800).

### Numeros Chave

| Metrica | Valor |
|---------|-------|
| Total de debitos identificados | 57 (apos revisao e deduplicacao) |
| Debitos criticos | 4 |
| Debitos altos | 10 |
| Debitos medios | 16 |
| Debitos baixos | 27 |
| Esforco total estimado | ~152 horas |
| Custo estimado (R$150/h) | R$ 22.800 |
| Esforco minimo (POC viavel) | ~12 horas |
| Custo minimo POC | R$ 1.800 |

### Recomendacao

Recomendamos aprovar imediatamente o investimento minimo de R$ 1.800 (12 horas) para correcoes pre-demonstracao. Este investimento elimina os riscos visuais e de seguranca mais evidentes, tornando o produto apresentavel para investidores e stakeholders com confianca. As demais fases podem ser avaliadas apos a demonstracao, conforme o interesse do mercado e a decisao de escalar o produto.

---

## Analise de Custos

### Custo de RESOLVER

| Categoria | Itens | Horas | Custo (R$150/h) |
|-----------|-------|-------|-----------------|
| Sistema (backend, CI/CD, infra) | 24 | ~83h | R$ 12.450 |
| Banco de dados (schema, seguranca, operacional) | 16 | ~16h | R$ 2.400 |
| Frontend / Experiencia do usuario | 23 | ~53h | R$ 7.950 |
| **TOTAL** | **63** | **~152h** | **R$ 22.800** |

**Nota:** O total bruto de 63 itens inclui 7 novos debitos descobertos durante a revisao dos especialistas. Apos deduplicacao de 6 sobreposicoes entre categorias, o total efetivo e de ~57 debitos unicos. As horas ja refletem os ajustes propostos pelos especialistas.

### Custo de NAO RESOLVER (Risco Acumulado)

| Risco | Probabilidade | Impacto | Custo Potencial |
|-------|---------------|---------|-----------------|
| **Falha na demonstracao** -- modal de login invisivel em temas escuros causa constrangimento perante investidores | Alta | Critico | Perda de oportunidade de investimento (incalculavel) |
| **Vulnerabilidade de seguranca** -- biblioteca JWT com CVEs conhecidos (python-jose) explorada | Media | Alto | Comprometimento de contas, dano reputacional, responsabilidade legal |
| **Vazamento de dados** -- arquivo SQLite legado com historico de buscas exposto no repositorio | Baixa | Alto | Violacao de privacidade, risco LGPD |
| **Perda de banco de dados** -- alteracoes de schema nao rastreadas impedem recriacao do banco | Media | Alto | Indisponibilidade total, perda de dados de usuarios |
| **Abandono de usuarios** -- inconsistencias visuais transmitem falta de profissionalismo | Alta | Medio | Reducao de 20-40% na retencao |
| **Lentidao no desenvolvimento** -- arquivo principal com 1.230 linhas dificulta novas features | Alta | Medio | Aumento de 2-3x no tempo de desenvolvimento |

---

## Impacto no Negocio

### Para o POC / Demonstracao

**O que funciona hoje:**
- Busca de licitacoes em todos os 27 estados com filtragem inteligente por relevancia
- Geracao automatica de resumo executivo via IA (gpt-4.1-nano)
- Download de resultados em Excel e CSV (ate 10.000 itens)
- Sistema de buscas salvas (com e sem conta, migracao automatica no primeiro login)
- 5 temas visuais (claro, papel, sepia, escuro suave, escuro)
- Progresso em tempo real com grid visual por estado e barra de progresso com ETA dinamico
- Cancelamento de buscas em andamento
- Aviso proativo para buscas de grande volume (>10 UFs ou >30 dias)
- Destaque de palavras-chave nos resultados com correspondencia por relevancia

**O que pode falhar durante uma demonstracao:**
- O modal de login/cadastro e praticamente invisivel em temas escuros -- texto preto sobre fundo escuro, botoes sem cor, campos de entrada sem borda. Se o apresentador trocar o tema, o constrangimento e garantido.
- Os badges de tipo de licitacao (licitacao vs. ata) na lista de resultados usam cores fixas que nao acompanham o tema, criando inconsistencia visivel na mesma pagina onde o resumo executivo mostra badges tematizados corretamente.
- O destaque de palavras-chave nos resultados usa amarelo padrao do navegador, que fica deslocado em temas escuros (dim/dark).
- O rodape ainda mostra "v2.0" enquanto o sistema e apresentado como versao 3.x.

**O que causaria constrangimento perante investidores:**
- Alguem inspecionar o repositorio e encontrar um arquivo de banco de dados SQLite com dados potenciais de usuarios.
- Um diretorio com nome invalido na raiz do projeto, sugerindo descuido na gestao do codigo.
- A biblioteca python-jose (com CVEs publicados) ainda listada nas dependencias.

### Seguranca

Quatro questoes de seguranca merecem atencao imediata:

1. **Biblioteca JWT com vulnerabilidades conhecidas:** O sistema usa duas bibliotecas para validacao de tokens de autenticacao (python-jose e PyJWT). A migracao para PyJWT foi iniciada na versao 3.3, mas o arquivo `supabase_auth.py` -- que valida todos os tokens de sessao do Supabase -- ainda usa a python-jose, que tem CVEs publicados e nao recebe manutencao ativa. As dependencias do projeto ainda listam ambas as bibliotecas.

2. **Validacao de audiencia desabilitada:** O sistema aceita tokens JWT sem verificar se foram emitidos para este projeto especifico (`verify_aud: False` no codigo). Em ambientes compartilhados, um token de outro projeto Supabase poderia ser aceito indevidamente.

3. **Arquivo de banco legado no repositorio:** O antigo banco de dados SQLite (`descomplicita.db`, 32KB) permanece no repositorio apos a migracao completa para Supabase, junto com a dependencia `aiosqlite`. Pode conter historico de buscas com UFs, setores e termos pesquisados por usuarios.

4. **Alteracoes de schema nao rastreadas:** Pelo menos uma alteracao critica no banco (`DEFAULT auth.uid()` na coluna `user_id` de `saved_searches`) foi feita diretamente no painel do Supabase sem registro nas migracoes. Se o banco precisar ser recriado a partir das migracoes, a funcionalidade de buscas salvas quebrara silenciosamente.

### Experiencia do Usuario

- **Modal de autenticacao quebrado (critico):** 6 tokens CSS inexistentes (`--card-bg`, `--text-primary`, `--text-secondary`, `--border-color`, `--input-bg`, `--accent-color`) causam falha visual completa em temas escuros e degradacao em temas claros. Afeta diretamente a conversao de cadastro e login -- a porta de entrada do produto.
- **Inconsistencias visuais nos resultados:** Badges de tipo de licitacao com cores fixas de Tailwind ao lado de badges tematizados corretamente na mesma pagina. Texto de erro com cores que ignoram o tema selecionado.
- **Componentes prontos mas nao utilizados:** Um botao reutilizavel bem implementado (com variantes primary/secondary/ghost/danger, tamanhos e estado de carregamento com Spinner integrado) existe no codigo mas nao e usado em nenhum lugar da aplicacao. O botao principal "Buscar" replica manualmente as mesmas classes.
- **Acessibilidade:** Acentos ausentes em rotulos de navegacao para leitores de tela ("Pagina anterior" em vez de "Pagina anterior" com acento); destaque de palavras (tag `<mark>`) sem estilizacao tematica, usando amarelo padrao do navegador que pode ter contraste inadequado em temas escuros.

### Manutenibilidade

- **Arquivo principal com 1.230 linhas:** Toda a logica de endpoints, pipeline de busca, parsing de termos e execucao de tarefas esta concentrada em `main.py`. Dificulta revisao de codigo, testes isolados e integracao de novos desenvolvedores.
- **Sem padrao de qualidade no backend:** Nenhuma ferramenta de analise estatica (linter, formatador, verificador de tipos) esta configurada para o codigo Python. Erros de estilo e bugs de tipo passam despercebidos ate producao.
- **Cobertura de testes frontend insuficiente:** Branches cobertos em apenas 52,74%, significando que quase metade dos caminhos logicos do frontend nao sao testados contra regressoes.
- **Sem pre-commit hooks:** Codigo pode ser commitado sem passar por linting, formatacao ou verificacao de tipos.

---

## Timeline Recomendado

### Fase 0: Pre-Demonstracao (1-2 dias) -- R$ 1.800

**12 horas de correcoes criticas que tornam o produto apresentavel com confianca.**

| Correcao | Horas | Impacto |
|----------|-------|---------|
| Corrigir modal de login/cadastro -- mapear 6 tokens CSS para tokens existentes do design system + migrar classes hardcoded de erro/sucesso para tokens semanticos | 3h | Login e cadastro funcionais em todos os 5 temas |
| Alinhar badges de resultados (ItemsList) com padrao tematizado do SearchSummary + corrigir texto de erro | 2h | Consistencia visual na pagina principal de resultados |
| Remover banco de dados SQLite legado (`descomplicita.db`) + dependencia `aiosqlite` do requirements.txt + adicionar ao `.gitignore` | 0.5h | Elimina risco de dados expostos no repositorio |
| Completar migracao JWT: migrar `supabase_auth.py` de python-jose para PyJWT e remover python-jose das dependencias | 1.5h | Elimina biblioteca com CVEs conhecidos |
| Habilitar validacao de audiencia (`verify_aud=True`, `audience="authenticated"`) na verificacao de tokens Supabase | 1h | Fecha brecha de autenticacao |
| Criar migracao para rastrear `DEFAULT auth.uid()` em `saved_searches.user_id` | 1h | Garante reprodutibilidade do banco de dados |
| Adicionar CHECK constraint de status (`queued`, `completed`, `failed`, `cancelled`) + corrigir propagacao do status `cancelled` | 1h | Integridade e consistencia de dados |
| Versao dinamica no rodape + remover diretorio invalido + organizar markdowns da raiz | 1h | Profissionalismo do repositorio |
| **Total** | **12h** | **Produto pronto para demonstracao** |

**ROI da Fase 0:** Com R$ 1.800, o produto passa de "POC com problemas visiveis" para "POC apresentavel com confianca". Este e o investimento com maior retorno de todo o roadmap.

### Fase 1: Quick Wins (1 semana) -- R$ 2.250

**~15 horas adicionais de correcoes de alto impacto e baixo esforco.**

| Correcao | Horas | Impacto |
|----------|-------|---------|
| Rate limiting nos endpoints de autenticacao (`/auth/login`, `/auth/signup`, `/auth/refresh`) | 2h | Prevencao contra ataques de forca bruta |
| Adotar componente Button existente nos 4-5 botoes da aplicacao (ganha spinner de carregamento integrado) | 3h | Consistencia visual e funcional |
| Estilizar tag `<mark>` por tema para destaque de palavras-chave | 1h | Contraste adequado em temas escuros |
| Mapear tokens CSS faltantes no Tailwind config (`--ink-warning`, `--badge-licitacao-*`, `--badge-ata-*`) | 1h | Elimina estilos inline em SearchSummary e SourceBadges |
| Ajustar timeout do Vercel para buscas grandes e downloads de Excel | 2h | Evita falha em operacoes de longa duracao |
| Politicas RLS granulares por operacao (explicitar WITH CHECK) | 2h | Melhores praticas de seguranca e auditabilidade |
| Acentos em rotulos de acessibilidade da paginacao | 0.5h | Pronuncia correta em leitores de tela |
| Deduplicacao de `dateDiffInDays` + limpeza de repositorio | 1.5h | Higiene de codigo |
| Ativar politica de retencao de dados (GitHub Actions schedule semanal) | 1.5h | Evita acumulo indefinido de dados no banco |
| **Total** | **~15h** | **Produto robusto para uso inicial** |

### Fase 2: Fundacao (2-3 semanas) -- R$ 5.400

**~36 horas de melhorias estruturais que habilitam crescimento sustentavel.**

| Correcao | Horas | Impacto |
|----------|-------|---------|
| Configurar linter Python (ruff) + formatacao automatica | 4h | Gate de qualidade para todo codigo backend |
| Pre-commit hooks (husky + lint-staged para frontend, ruff para backend) | 2h | Prevencao automatica de problemas antes do commit |
| Refatorar endpoints de autenticacao: Pydantic para validacao + reutilizar Supabase client do DI | 7h | Seguranca, validacao automatica, documentacao OpenAPI |
| Runner automatizado de migracoes (supabase db push no CI) | 6h | Habilita todas as migracoes futuras com seguranca |
| Corrigir cache de token JWT no frontend (`backendAuth.ts`) para ambiente serverless | 3h | Confiabilidade da autenticacao entre instancias |
| Criar componentes Input/Select reutilizaveis seguindo padrao do Button | 4h | Completar o design system basico |
| Logging estruturado no frontend com correlacao `X-Correlation-Id` | 4h | Observabilidade e rastreamento de erros cross-stack |
| Melhorias operacionais de banco: cleanup em batches + retention ativa + metricas de falha | 6h | Estabilidade operacional |
| **Total** | **~36h** | **Base solida para escalar o produto** |

### Fase 3: Otimizacao (4-6 semanas) -- R$ 13.350

**~89 horas de melhorias para produto maduro, a executar apos validacao do POC.**

| Correcao | Horas | Impacto |
|----------|-------|---------|
| Refatorar main.py de 1.230 linhas em modulos tematicos | 8h | Manutenibilidade drasticamente melhorada |
| Implementar testes de integracao reais no CI (substituir placeholder) | 8h | Cobertura de cenarios reais, prevencao de regressoes |
| Aumentar cobertura de testes frontend (branches de 52% para 65%+) | 16h | Prevencao sistematica de regressoes |
| Criar componentes adicionais do design system + adotar em toda a app | 4h | Completude e consistencia visual |
| Rotas de resultado com deep-linking (`/resultado/:job_id`) | 8h | Compartilhamento de buscas entre usuarios |
| Estrategia de depreciacao e versionamento de API | 4h | Governanca de API para integradores |
| Expandir configuracao ESLint com regras TypeScript e acessibilidade | 3h | Qualidade incremental do frontend |
| Itens fora de escopo POC: i18n (16h), PWA (8h), SSE (12h) | 38h | So implementar se houver demanda comprovada |
| **Total** | **~89h** | **Produto pronto para escala** |

---

## ROI da Resolucao

| Investimento | Retorno Esperado |
|--------------|------------------|
| R$ 1.800 (Fase 0 -- pre-demo) | Produto apresentavel com confianca; eliminacao de constrangimentos visuais e riscos de seguranca basica |
| R$ 4.050 (Fases 0+1) | Produto robusto para primeiros usuarios; seguranca adequada para uso real; design system coerente |
| R$ 9.450 (Fases 0+1+2) | Base estrutural solida; velocidade de desenvolvimento 2-3x maior; qualidade automatizada |
| R$ 22.800 (todas as fases) | Produto sustentavel, seguro, acessivel e pronto para escalar |

**Analise de ROI:**

- **Investimento minimo (R$ 1.800):** Evita potencial perda de investimento por falha em demonstracao. Se a demonstracao atrair investimento de R$ 50.000+, o retorno e de 27:1 ou superior.
- **Investimento intermediario (R$ 9.450):** Reduz tempo de desenvolvimento de novas features em 2-3x gracas a linting automatizado, design system coerente e migracoes confiáveis. Em 3 meses de desenvolvimento ativo, a economia em horas ja supera o investimento.
- **Custo de nao agir:** Cada mes com a biblioteca python-jose vulneravel e uma janela aberta. Cada demonstracao com o modal de login quebrado e uma oportunidade perdida. O schema drift nao rastreado e uma bomba-relogio que explode na primeira recriacao do banco.

**ROI estimado do investimento total: 5:1 a 10:1** considerando riscos evitados (seguranca, reputacao, produtividade) versus o investimento de R$ 22.800.

---

## Proximos Passos

1. [ ] **Aprovar investimento minimo de R$ 1.800** (12h de correcoes pre-demonstracao)
2. [ ] **Executar Fase 0** em 1-2 dias uteis (prioridade maxima)
3. [ ] **Realizar demonstracao** com produto corrigido
4. [ ] **Avaliar resultado** e decidir sobre Fase 1 (R$ 2.250 adicional)
5. [ ] **Planejar sprints de resolucao** para Fases 2 e 3 conforme roadmap do produto

---

## Nota sobre o Estado do Projeto

E importante destacar que o Descomplicita esta em estado surpreendentemente bom para um POC. A base tecnica inclui:

- **1.925+ testes automatizados** (1.349 backend + 576 frontend + 5 specs E2E) com cobertura acima de 70% no backend
- **9 workflows de CI/CD** automatizados no GitHub Actions (testes, deploy, CodeQL, bundle size, dependabot)
- **Seguranca de dados** com Row Level Security em todas as 4 tabelas do banco
- **Acessibilidade** parcialmente validada (WCAG AA) com axe-core nos testes E2E, `--ink-muted` validado para contraste >= 4.5:1 em todos os 5 temas
- **Monitoramento de erros** com Sentry em frontend e backend, sample rate de 10%
- **5 temas visuais** com tokens semanticos, script de inicializacao para evitar flash, e `prefers-reduced-motion` respeitado
- **Autenticacao robusta** com 3 niveis (Supabase JWT > Custom JWT > API Key), safeguard de producao, e `hmac.compare_digest` contra timing attacks
- **Arquitetura de busca** com pipeline de 8 fases, stemming RSLP para portugues, 3 tiers de keywords com pesos, e fallback deterministico para resumo LLM

Os debitos identificados sao gerenciaveis e **nenhum e bloqueante para um lancamento controlado** (beta fechado). Com o investimento minimo de 12 horas, o produto esta pronto para ser demonstrado com confianca.

---

## Anexos

| Documento | Localizacao |
|-----------|-------------|
| Assessment tecnico completo (57 debitos) | `docs/prd/technical-debt-DRAFT.md` |
| Revisao do especialista em banco de dados | `docs/reviews/db-specialist-review.md` |
| Revisao do especialista em UX | `docs/reviews/ux-specialist-review.md` |
| Gate de qualidade (QA) | `docs/reviews/qa-review.md` |
| Arquitetura do sistema (v5.0) | `docs/architecture/system-architecture.md` |

---

*Relatorio preparado em 2026-03-11 por @analyst (Lens)*
*Baseado no Technical Debt Assessment DRAFT validado por 4 especialistas*
*Gate de qualidade: APPROVED (com condicoes) -- @qa (Shield)*
