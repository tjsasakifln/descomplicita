# Relatorio de Debito Tecnico -- Descomplicita

**Projeto:** Descomplicita
**Data:** 2026-03-07
**Versao:** 1.0
**Preparado por:** @analyst (Sage), Business Analyst
**Fonte:** Assessment tecnico validado por @architect, @ux-design-expert, @qa

---

## 1. Resumo Executivo

### Situacao Atual

O Descomplicita e uma plataforma de busca de licitacoes publicas que agrega dados do Portal Nacional de Contratacoes Publicas (PNCP) e os apresenta de forma simplificada para empresas que vendem uniformes ao governo. A plataforma funciona e entrega valor -- usuarios conseguem pesquisar licitacoes por estado, setor e palavras-chave, visualizar resultados e exportar para Excel. A interface passou por um rebrand recente (de BidIQ para Descomplicita) e conta com 5 temas visuais, busca por 27 estados e exportacao de dados.

No entanto, uma auditoria tecnica completa revelou **57 debitos tecnicos** que representam riscos concretos ao negocio. O mais grave: a plataforma **nao possui autenticacao** -- qualquer pessoa na internet pode consumir todos os recursos do sistema, fazer requisicoes ilimitadas a API do governo e ate limpar o cache do sistema. Alem disso, a base de testes esta parcialmente quebrada, o que significa que alteracoes futuras podem introduzir defeitos sem deteccao.

A plataforma tambem apresenta lacunas significativas em acessibilidade digital. Com 13 problemas identificados nessa area, o sistema nao atende aos requisitos da Lei Brasileira de Inclusao (Lei 13.146/2015), o que representa risco juridico para uma ferramenta que interage com o setor publico. A boa noticia: o plano de resolucao e viavel -- 10 semanas de trabalho estruturado em 6 sprints eliminam os riscos criticos e posicionam o produto para crescimento sustentavel.

### Numeros Chave

| Metrica | Valor |
|---------|-------|
| Total de Debitos Identificados | 57 |
| Debitos Criticos (acao imediata) | 5 |
| Debitos de Alta Prioridade | 13 |
| Debitos de Media Prioridade | 22 |
| Debitos de Baixa Prioridade | 17 |
| Esforco Total Estimado | 206 - 388 horas |
| Esforco Programado (sem backlog) | 173 - 287 horas |
| Custo Estimado (programado) | R$ 25.950 - R$ 43.050 |
| Custo Estimado (total com backlog) | R$ 30.900 - R$ 58.200 |
| Prazo de Execucao | ~10 semanas (6 sprints) |

### Recomendacao

Recomendamos **aprovar imediatamente o orcamento para os Sprints 0 e 1** (R$ 3.750 - R$ 6.900), que corrigem testes quebrados e fecham vulnerabilidades de seguranca criticas. O lancamento publico ou qualquer acao de marketing **nao deve ocorrer** antes da conclusao do Sprint 1. O plano completo de 10 semanas deve ser aprovado como investimento estrategico -- o custo de nao agir (estimado em R$ 250.000 - R$ 750.000 em cenarios de risco) supera em ate 13x o investimento necessario.

---

## 2. Analise de Custos

### Custo de RESOLVER

| Categoria | Itens | Horas (min-max) | Custo Min (R$150/h) | Custo Max (R$150/h) |
|-----------|-------|-----------------|---------------------|---------------------|
| Seguranca (CORS, auth, rate limit, debug endpoints, input) | 7 | 14 - 28 | R$ 2.100 | R$ 4.200 |
| Arquitetura Frontend (decomposicao do componente monolito) | 4 | 31 - 45 | R$ 4.650 | R$ 6.750 |
| Qualidade Frontend e Acessibilidade | 18 | 36 - 58 | R$ 5.400 | R$ 8.700 |
| Arquitetura Backend (Redis, async, injecao de dependencia) | 7 | 58 - 96 | R$ 8.700 | R$ 14.400 |
| Infraestrutura e Polimento (logs, observabilidade, branding) | 15 | 30 - 53 | R$ 4.500 | R$ 7.950 |
| Correcoes de Emergencia (testes quebrados) | 2 | 3 - 5 | R$ 450 | R$ 750 |
| Backlog (nao programado) | 5 | 22 - 52 | R$ 3.300 | R$ 7.800 |
| **TOTAL PROGRAMADO** | **53** | **173 - 287** | **R$ 25.950** | **R$ 43.050** |
| **TOTAL COM BACKLOG** | **57** | **206 - 388** | **R$ 30.900** | **R$ 58.200** |

### Custo de NAO RESOLVER (Risco Acumulado)

| Risco | Probabilidade | Impacto Financeiro | Custo Potencial |
|-------|---------------|-------------------|-----------------|
| Abuso da API (sem autenticacao): atacante consome todos os 10 slots de processamento, causando indisponibilidade total para usuarios reais | Alta (70%) | Perda de usuarios + custo de recuperacao | R$ 15.000 - R$ 50.000 |
| Bloqueio pela API do PNCP: requisicoes abusivas via nossa plataforma resultam em bloqueio do nosso acesso ao portal do governo | Media (40%) | Produto para de funcionar completamente | R$ 50.000 - R$ 150.000 |
| Penalidade por inacessibilidade (LBI 13.146/2015): ferramenta voltada ao setor publico sem conformidade WCAG AA | Baixa (15%) | Multa administrativa + processo civil | R$ 20.000 - R$ 100.000 |
| Vazamento de dados via CORS aberto: terceiros acessam dados de buscas e resultados de outros usuarios | Media (30%) | Dano reputacional + notificacao LGPD | R$ 30.000 - R$ 100.000 |
| Exploracoes via container rodando como root | Baixa (10%) | Comprometimento do servidor + dados | R$ 50.000 - R$ 200.000 |
| Incapacidade de escalar: arquitetura in-memory perde dados a cada deploy, impossibilita multiplas instancias | Alta (80%) | Teto de crescimento, perda de oportunidade | R$ 50.000 - R$ 150.000 |
| Velocidade de desenvolvimento estagnada: componente monolito de 1.071 linhas impede novas funcionalidades | Alta (90%) | Atraso em features, custo de manutencao elevado | R$ 30.000 - R$ 80.000 |

**Custo potencial ponderado de nao agir: R$ 115.000 - R$ 365.000**

**Cenario pessimista (multiplos riscos simultaneos): R$ 250.000 - R$ 750.000**

---

## 3. Impacto no Negocio

### 3.1 Seguranca -- Risco Imediato

A plataforma esta operando **sem nenhuma camada de protecao**. Especificamente:

- **Qualquer site na internet** pode fazer requisicoes ao nosso backend (CORS aberto para todas as origens)
- **Nao existe autenticacao** -- nenhuma chave de API, nenhum login, nenhuma identificacao de usuario
- **Endpoints de debug estao expostos** -- qualquer pessoa pode limpar o cache do sistema ou acessar informacoes internas
- **Nao ha limite de requisicoes** -- um unico usuario pode consumir todos os recursos do sistema
- **O container roda com privilegios de administrador** -- em caso de invasao, o atacante tem controle total

**Traducao para o negocio:** Antes de qualquer acao de marketing ou divulgacao publica, estas vulnerabilidades precisam ser corrigidas. Um concorrente, bot ou agente malicioso pode facilmente derrubar o servico ou abusar do acesso ao PNCP.

### 3.2 Performance e Experiencia do Usuario

- **Usuarios moveis nao veem resultados apos a busca** -- o formulario ocupa a tela inteira e nao ha redirecionamento automatico para os resultados. Usuarios podem abandonar o produto pensando que a busca falhou.
- **Contraste de cores insuficiente** -- textos secundarios nao atendem ao padrao minimo de legibilidade (WCAG AA 4.5:1), dificultando a leitura em ambiente externo ou por usuarios com baixa visao.
- **Dados perdidos a cada atualizacao do sistema** -- buscas em andamento, cache de resultados e arquivos de download sao armazenados apenas em memoria. Cada deploy zera tudo.
- **Arquivos Excel trafegam como texto dentro de respostas JSON** -- metodo ineficiente que consome mais banda e memoria do que necessario, impactando usuarios com conexoes lentas.

### 3.3 Acessibilidade -- Risco Juridico

A Lei Brasileira de Inclusao (Lei 13.146/2015) exige acessibilidade digital, especialmente em ferramentas que interagem com o setor publico. Foram identificados **13 problemas de acessibilidade**:

- Dialogos modais sem "armadilha de foco" (usuarios de teclado ficam presos)
- Menus dropdown nao fecham com a tecla Escape
- Nao existe link "pular para o conteudo" para usuarios de leitor de tela
- Hierarquia de titulos ausente (dificulta navegacao por leitor de tela)
- Botoes sem rotulos descritivos para tecnologias assistivas

### 3.4 Velocidade de Desenvolvimento

O maior gargalo tecnico e um unico arquivo de 1.071 linhas (`page.tsx`) que contem **toda** a interface do usuario -- formularios, logica de negocio, animacoes, downloads e buscas salvas. Isso significa:

- **Qualquer mudanca na interface corre risco de quebrar funcionalidades nao relacionadas**
- **Dois desenvolvedores nao conseguem trabalhar simultaneamente** na interface
- **Testes sao praticamente impossiveis** -- a cobertura real e de 49%, nao os 91.5% reportados anteriormente
- **Novas funcionalidades levam 3-5x mais tempo** para implementar neste formato

---

## 4. Timeline Recomendado

### Sprint 0: Correcoes de Emergencia (Semana 1, Dias 1-2)

**O que:** Corrigir testes automatizados quebrados (2 testes de backend referenciam nome antigo "BidIQ"; 1 teste E2E referencia cores desatualizadas).

**Por que:** Sem testes funcionando, nao ha rede de seguranca para as mudancas seguintes. Prerequisito absoluto.

| Esforco | Custo |
|---------|-------|
| 3 - 5 horas | R$ 450 - R$ 750 |

---

### Sprint 1: Seguranca + Ganhos Rapidos (Semanas 1-2)

**O que:** Restringir CORS, implementar autenticacao por chave de API, adicionar limite de requisicoes, proteger container, bloquear endpoints de debug, corrigir contraste de cores, adicionar atalhos de teclado.

**Por que:** Fechar a superficie de ataque antes de qualquer exposicao publica. Os ganhos rapidos de acessibilidade (contraste, tecla Escape, link de pular navegacao) sao correcoes de poucas linhas com alto impacto na experiencia.

| Esforco | Custo |
|---------|-------|
| 22 - 41 horas | R$ 3.300 - R$ 6.150 |

**Marco:** Apos Sprint 1, a plataforma pode ser divulgada com seguranca basica.

---

### Sprint 2: Arquitetura Frontend (Semanas 3-4)

**O que:** Decompor o componente monolito de 1.071 linhas em 8-10 componentes menores e 2 hooks reutilizaveis. Meta: arquivo principal com menos de 150 linhas.

**Por que:** Desbloquear desenvolvimento paralelo, possibilitar testes adequados e reduzir risco de regressao em todas as mudancas futuras da interface.

| Esforco | Custo |
|---------|-------|
| 31 - 45 horas | R$ 4.650 - R$ 6.750 |

**Marco:** Interface modular, testavel e pronta para receber novas funcionalidades.

---

### Sprint 3: Qualidade Frontend + Acessibilidade (Semanas 5-6)

**O que:** Corrigir todos os 13 problemas de acessibilidade (foco em dialogos, ARIA roles, hierarquia de titulos), alinhar sistema de design com os 5 temas, implementar code splitting.

**Por que:** Conformidade com a Lei 13.146/2015, melhoria da experiencia para todos os usuarios (inclusive os que usam apenas teclado ou leitores de tela), reducao do tempo de carregamento.

| Esforco | Custo |
|---------|-------|
| 29 - 47 horas | R$ 4.350 - R$ 7.050 |

**Marco:** Zero violacoes criticas de acessibilidade (WCAG AA).

---

### Sprint 4: Arquitetura Backend (Semanas 7-8)

**O que:** Migrar armazenamento de memoria para Redis (buscas e cache), modernizar cliente HTTP para operacao assincrona, implementar entrega de arquivos Excel via streaming.

**Por que:** Atualmente, cada deploy do sistema perde todos os dados em andamento. A arquitetura atual suporta apenas uma instancia -- impossivel escalar. Este e o maior investimento, mas e o que permite crescimento.

| Esforco | Custo |
|---------|-------|
| 58 - 96 horas | R$ 8.700 - R$ 14.400 |

**Marco:** Sistema resiliente a deploys, escalavel horizontalmente, pronto para crescimento de usuarios.

---

### Sprint 5: Polimento + Infraestrutura (Semanas 9-10)

**O que:** Implementar monitoramento de erros em producao (Sentry), logs estruturados com rastreabilidade, completar migracoes de APIs depreciadas, finalizar rebrand, implementar desligamento gracioso.

**Por que:** Sem monitoramento, erros em producao passam despercebidos. Sem logs estruturados, investigar problemas e como "procurar agulha em palheiro". O rebrand incompleto causa confusao e testes quebrados.

| Esforco | Custo |
|---------|-------|
| 30 - 53 horas | R$ 4.500 - R$ 7.950 |

**Marco:** Produto com observabilidade completa, marca consistente, codigo limpo.

---

## 5. ROI da Resolucao

### Investimento vs. Retorno

| Dimensao | Investimento | Retorno Esperado |
|----------|--------------|------------------|
| Financeiro | R$ 25.950 - R$ 43.050 (programado) | R$ 115.000 - R$ 365.000 em riscos evitados |
| Tempo | 173 - 287 horas de desenvolvimento | Reducao de 40-60% no tempo de implementacao de novas features |
| Prazo | ~10 semanas de execucao | Produto sustentavel, escalavel e conforme a legislacao |
| Seguranca | R$ 5.550 - R$ 10.350 (Sprints 0+1) | Protecao contra indisponibilidade, bloqueio de API e vazamentos |
| Velocidade | R$ 4.650 - R$ 6.750 (Sprint 2) | Desenvolvimento 3-5x mais rapido na interface apos decomposicao |
| Escalabilidade | R$ 8.700 - R$ 14.400 (Sprint 4) | Capacidade de escalar para milhares de usuarios simultaneos |

### Calculo de ROI

**Cenario conservador (custos minimos, riscos medianos):**

- Investimento: R$ 25.950
- Riscos evitados (ponderados por probabilidade): R$ 115.000
- **ROI: 3,4:1** -- cada R$ 1 investido evita R$ 3,40 em perdas potenciais

**Cenario pessimista (custos maximos, riscos altos):**

- Investimento: R$ 43.050
- Riscos evitados: R$ 365.000
- **ROI: 7,5:1** -- cada R$ 1 investido evita R$ 7,50 em perdas potenciais

**Cenario de crise (multiplos riscos simultaneos):**

- Investimento: R$ 43.050
- Perdas potenciais evitadas: R$ 750.000
- **ROI: 16,4:1**

### Beneficios Nao Quantificaveis

- Conformidade com LBI 13.146/2015 (acessibilidade)
- Conformidade com LGPD (protecao de dados)
- Confianca do mercado em ferramenta que interage com o governo
- Capacidade de atrair investimento com base tecnica solida
- Reducao de rotatividade de desenvolvedores (codigo limpo = equipe motivada)

---

## 6. Proximos Passos

### Acoes Imediatas (esta semana)

1. [ ] **Aprovar orcamento emergencial:** R$ 3.750 - R$ 6.900 para Sprints 0 e 1 (seguranca e testes)
2. [ ] **Suspender divulgacao publica** ate conclusao do Sprint 1 (2 semanas)
3. [ ] **Alocar 1 desenvolvedor backend** para Sprint 0 (2 dias) + Sprint 1 seguranca (1 semana)
4. [ ] **Iniciar Sprint 0** imediatamente -- corrigir testes quebrados

### Acoes de Curto Prazo (semanas 2-4)

5. [ ] **Aprovar orcamento completo:** R$ 25.950 - R$ 43.050 para o plano de 10 semanas
6. [ ] **Alocar 1 desenvolvedor frontend** para Sprint 1 acessibilidade + Sprint 2 decomposicao
7. [ ] **Definir infraestrutura Redis** (Railway, AWS ElastiCache ou similar) para Sprint 4

### Acoes de Medio Prazo (semanas 5-10)

8. [ ] **Executar Sprints 3-5** conforme cronograma
9. [ ] **Configurar Sentry** para monitoramento de producao (Sprint 5)
10. [ ] **Validar conformidade WCAG AA** com ferramenta automatizada (axe-core)

### Decisoes Necessarias

| Decisao | Responsavel | Prazo |
|---------|-------------|-------|
| Aprovar orcamento Sprint 0+1 | Diretor de Produto | Imediato |
| Aprovar orcamento completo (10 semanas) | Diretor Financeiro | Semana 2 |
| Escolher provedor Redis (Railway/AWS/outro) | CTO / DevOps | Semana 6 |
| Escolher storage para Excel (S3/R2/Supabase) | CTO / DevOps | Semana 6 |
| Definir modelo de autenticacao futuro (JWT) | Diretor de Produto + CTO | Semana 4 |

---

## 7. Anexos

### Documentos de Referencia

| Documento | Localizacao |
|-----------|-------------|
| Assessment Tecnico Completo (57 debitos detalhados) | `docs/prd/technical-debt-assessment.md` |
| Arquitetura do Sistema | `docs/architecture/system-architecture.md` |
| Especificacao Frontend | `docs/frontend/frontend-spec.md` |

### Glossario para Stakeholders

| Termo | Significado |
|-------|-------------|
| CORS | Mecanismo de seguranca que controla quais sites podem acessar nossa API |
| WCAG AA | Padrao internacional de acessibilidade digital (nivel intermediario) |
| Redis | Banco de dados em memoria usado para cache e filas (substitui armazenamento temporario) |
| Sprint | Ciclo de trabalho com duracao definida e entregas especificas |
| Debito tecnico | "Atalhos" no codigo que funcionam hoje mas criam problemas futuros |
| PNCP | Portal Nacional de Contratacoes Publicas -- fonte dos dados de licitacoes |
| LBI | Lei Brasileira de Inclusao (Lei 13.146/2015) -- exige acessibilidade digital |
| LGPD | Lei Geral de Protecao de Dados -- regulamenta tratamento de dados pessoais |

### Metodologia de Estimativa de Custos

- **Taxa base:** R$ 150/hora (desenvolvedor mid-senior)
- **Faixas:** Horas minimas e maximas por item, validadas por 3 especialistas (arquiteto, UX, QA)
- **Riscos financeiros:** Estimados com base em benchmarks de mercado para empresas SaaS B2G (Business-to-Government)
- **ROI:** Calculado como (riscos evitados ponderados por probabilidade) / (investimento em resolucao)

---

*Relatorio preparado em 2026-03-07*
*Baseado no Assessment Tecnico v1.0 (commit 9fbd54d0)*
*Para duvidas, contate @analyst (Sage)*
