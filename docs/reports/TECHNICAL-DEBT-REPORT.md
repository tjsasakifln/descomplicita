# Relatorio de Debito Tecnico

**Projeto:** Descomplicita POC v0.2
**Data:** 2026-03-09
**Versao:** 2.0 (atualizacao do assessment de Janeiro 2026)
**Preparado por:** @analyst (Ada), Business Analyst
**Fonte:** Assessment tecnico FINAL validado por @architect (Atlas), @ux-design-expert (Vera), @qa (Quinn)

---

## Executive Summary

### Situacao Atual

O Descomplicita e uma plataforma de busca e analise de licitacoes publicas de uniformes no Portal Nacional de Contratacoes Publicas (PNCP). O produto funciona e entrega valor: usuarios pesquisam licitacoes por estado, setor e palavras-chave, visualizam resultados com resumos gerados por inteligencia artificial e exportam dados para Excel. A plataforma opera com 5 temas visuais, cobertura de 27 estados e duas fontes de dados ativas (PNCP e BEC-SP).

Uma auditoria tecnica completa, conduzida por tres especialistas independentes (arquitetura, UX e qualidade), identificou **55 debitos tecnicos** que representam riscos concretos ao negocio. Os mais graves dizem respeito a seguranca: a plataforma opera com uma unica chave de API compartilhada por todos os usuarios, sem identificacao individual, sem trilha de auditoria e sem limite de uso por pessoa. Se a chave nao estiver configurada, o sistema fica totalmente exposto na internet. Alem disso, o sistema armazena dados temporarios apenas em memoria, perdendo tudo a cada atualizacao ou reinicializacao.

A boa noticia: comparado ao assessment anterior (versao 1.0, marco 2026), o cenario melhorou significativamente. O numero total de debitos caiu de 57 para 55, a severidade de varios itens foi reavaliada com mais precisao, e o esforco estimado diminuiu de 206-388 horas para 155-232 horas -- uma reducao de 25-40%. O plano de resolucao e viavel: 4 sprints em 5-6 semanas eliminam os riscos criticos e posicionam o produto para crescimento sustentavel.

### Numeros Chave

| Metrica | Valor |
|---------|-------|
| Total de Debitos | 55 |
| Debitos Criticos (acao imediata) | 3 |
| Debitos de Alta Prioridade | 10 |
| Debitos de Media Prioridade | 25 |
| Debitos de Baixa Prioridade | 17 |
| Esforco Total Estimado | 155 - 232 horas |
| Custo Estimado (minimo) | R$ 23.250 |
| Custo Estimado (maximo) | R$ 34.800 |
| Timeline de Execucao | 5-6 semanas (4 sprints) |

### Recomendacao

Recomendamos aprovar o plano de resolucao em 4 sprints, priorizando os Quick Wins (Sprint 1, R$ 1.200) que podem ser executados em 1-2 dias, seguidos imediatamente pelo Sprint 2 de correcoes criticas (R$ 6.600 - R$ 10.350). O lancamento publico ou qualquer acao de marketing **nao deve ocorrer** antes da conclusao do Sprint 2, que endereca as vulnerabilidades de seguranca e os bloqueadores funcionais. O investimento total de R$ 23.250 - R$ 34.800 evita riscos estimados em R$ 150.000 - R$ 450.000, representando um ROI de 5:1 a 13:1.

---

## Analise de Custos

### Custo de RESOLVER

| Categoria | Horas (min) | Horas (max) | Custo Min (R$150/h) | Custo Max (R$150/h) |
|-----------|-------------|-------------|----------------------|----------------------|
| Sistema (Backend) | 78 | 124 | R$ 11.700 | R$ 18.600 |
| Frontend/UX | 43 | 58 | R$ 6.450 | R$ 8.700 |
| Cross-cutting | 34 | 50 | R$ 5.100 | R$ 7.500 |
| **TOTAL** | **155** | **232** | **R$ 23.250** | **R$ 34.800** |

### Custo de NAO RESOLVER (Risco Acumulado)

| Risco | Probabilidade | Impacto | Custo Potencial |
|-------|---------------|---------|-----------------|
| **Abuso da API sem autenticacao:** qualquer pessoa na internet pode consumir todos os recursos do sistema, derrubar o servico ou fazer requisicoes ilimitadas ao PNCP | Alta (70%) | Indisponibilidade total + bloqueio pelo PNCP | R$ 30.000 - R$ 100.000 |
| **Perda de dados em cada deploy:** buscas em andamento, cache de resultados e arquivos sao armazenados apenas em memoria e perdidos a cada atualizacao | Alta (80%) | Usuarios perdem trabalho, experiencia degradada | R$ 20.000 - R$ 60.000 |
| **Falhas de download para arquivos grandes:** limite de 10 segundos no Vercel combinado com bufferizacao tripla em memoria pode impedir exportacoes Excel | Media (50%) | Funcionalidade core quebrada | R$ 15.000 - R$ 40.000 |
| **Penalidade por inacessibilidade (LBI 13.146/2015):** ferramenta voltada ao setor publico sem conformidade WCAG AA em contraste de cores e campos de formulario | Baixa (15%) | Multa administrativa + processo civil | R$ 20.000 - R$ 100.000 |
| **Busca com funcionalidade quebrada:** usuarios nao conseguem pesquisar termos como "camisa polo" (espaco cria tokens separados em vez de manter a expressao) | Alta (90%) | Resultados incorretos, abandono do produto | R$ 25.000 - R$ 75.000 |
| **Esgotamento do sistema sob carga:** chamadas de IA sem timeout + threads compartilhadas podem travar o sistema inteiro quando multiplos usuarios buscam simultaneamente | Media (40%) | Sistema para de responder | R$ 15.000 - R$ 50.000 |
| **Incapacidade de escalar:** arquitetura in-memory limita a uma unica instancia do servidor | Alta (80%) | Teto de crescimento, perda de oportunidade | R$ 30.000 - R$ 80.000 |

**Custo potencial ponderado de nao agir: R$ 95.000 - R$ 305.000**

**Cenario pessimista (multiplos riscos simultaneos): R$ 150.000 - R$ 450.000**

---

## Impacto no Negocio

### Seguranca

O sistema opera com protecao minima. As vulnerabilidades mais relevantes para o negocio:

- **Sem identificacao de usuarios** -- todos compartilham a mesma chave de acesso. Nao e possivel saber quem faz o que, nem responsabilizar usos indevidos. Se a chave nao estiver configurada, qualquer pessoa na internet acessa tudo.
- **Headers de seguranca ausentes** -- protecoes padrao da web (CSP, HSTS) nao estao implementadas, deixando o sistema mais vulneravel a ataques comuns como injecao de scripts maliciosos.
- **Configuracao de CORS permissiva** -- aceita qualquer tipo de requisicao de qualquer origem, embora as origens permitidas estejam corretamente restritas.
- **Risco de compliance com LGPD** -- sem trilha de auditoria e sem avaliacao de informacoes pessoais em logs, ha risco de nao conformidade com a lei de protecao de dados.

### Performance

Os problemas de performance impactam diretamente a experiencia do usuario e a viabilidade de crescimento:

- **Arquivos Excel duplicados em memoria** -- o mesmo arquivo e armazenado 3 vezes simultaneamente (no processamento, no cache Redis e na resposta ao usuario), triplicando o consumo de memoria.
- **Sem paginacao** -- todos os resultados de uma busca sao retornados de uma vez. Com muitas licitacoes, o tempo de resposta aumenta e o consumo de memoria cresce.
- **Limite de 10 segundos no servidor** -- a plataforma de hospedagem (Vercel) impoe um limite de 10 segundos por requisicao. Downloads de arquivos grandes podem falhar.
- **Requisicoes desnecessarias** -- o sistema faz entre 60 e 300 requisicoes extras por busca para verificar o progresso, sem otimizacao. Isso gera carga desnecessaria no servidor.

### Experiencia do Usuario

Problemas que afetam diretamente a adocao e retencao de usuarios:

- **Busca por termos compostos nao funciona** -- pesquisar "camisa polo" cria dois filtros separados ("camisa" e "polo") em vez de buscar a expressao completa. Este e um bloqueador funcional critico para o caso de uso principal do produto.
- **Licitacoes vencidas nos resultados** -- o filtro de prazo esta desabilitado, mostrando licitacoes que ja encerraram o periodo de propostas. Usuarios perdem tempo analisando oportunidades que nao existem mais.
- **Problemas de contraste visual** -- alguns temas visuais (Sepia, Paperwhite) nao atendem ao padrao minimo de legibilidade, dificultando a leitura para usuarios com baixa visao ou em ambientes com muita luz.
- **Campos obrigatorios nao sinalizados para leitores de tela** -- usuarios com deficiencia visual que usam tecnologias assistivas nao sabem quais campos precisam preencher.
- **Buscas salvas apenas no navegador** -- se o usuario trocar de dispositivo ou limpar o navegador, perde todas as buscas salvas.

### Manutenibilidade

Problemas que afetam a velocidade de entrega de novas funcionalidades:

- **Velocidade de desenvolvimento atual** -- a base de codigo tem acoplamentos que dificultam mudancas isoladas. Um componente de interface com mais de 450 linhas precisa ser decomposto para permitir evolucao mais rapida.
- **Risco de regressao** -- sem testes de integracao entre frontend e backend, e sem testes de regressao visual, cada mudanca pode introduzir defeitos nao detectados.
- **Codigo morto** -- 3 das 5 fontes de dados originais estao desabilitadas mas o codigo permanece na base, aumentando a complexidade de manutencao.
- **Custo de novas features** -- sem banco de dados, sem versionamento de API e sem testes de contrato, cada funcionalidade nova exige mais cuidado e tempo para implementar com seguranca.

---

## Evolucao desde Janeiro 2026

Este relatorio atualiza a versao 1.0 publicada em 07/03/2026, incorporando revisoes de dois especialistas adicionais (UX e QA). Principais mudancas:

### O que melhorou

| Aspecto | Antes (v1.0) | Agora (v2.0) |
|---------|--------------|--------------|
| Total de debitos | 57 | 55 (-2) |
| Debitos criticos | 5 | 3 (-2) |
| Esforco estimado | 206-388 horas | 155-232 horas (-25 a -40%) |
| Custo estimado | R$ 30.900 - R$ 58.200 | R$ 23.250 - R$ 34.800 (-25 a -40%) |
| Timeline | 10 semanas (6 sprints) | 5-6 semanas (4 sprints) |
| Especialistas envolvidos | 1 (arquiteto) | 3 (arquiteto + UX + QA) |

### O que mudou

- **Severidades recalibradas** -- 9 itens tiveram severidade ajustada com base em risco real, nao teorico. Por exemplo: codigo morto de fontes desabilitadas foi rebaixado de Critico para Alto (o sistema funciona bem com 2 fontes), e problemas de contraste foram promovidos de Medio para Alto (obrigacao legal).
- **Plano mais compacto** -- o assessment anterior incluia sprints separados para decomposicao de componentes frontend e infraestrutura. A reavaliacao consolidou o trabalho em 4 sprints focados em impacto.
- **Custos mais precisos** -- faixas de estimativa mais estreitas (155-232h vs 206-388h) gracas a validacao cruzada por 3 especialistas.

### O que e novo

- **3 novos debitos de acessibilidade** identificados pela revisao UX: cores hardcoded que nao respeitam temas, campos sem sinalizacao para leitores de tela, e timeout de confirmacao inacessivel.
- **Cadeia de falhas em cascata** documentada: chamadas de IA sem timeout podem travar o sistema inteiro quando combinadas com compartilhamento de threads.
- **Grafo de dependencias** entre debitos, permitindo planejamento mais inteligente da ordem de resolucao.

### O que permanece

- **Autenticacao** continua sendo o debito mais critico (P0), sem resolucao desde a identificacao.
- **Dados em memoria** continuam sendo perdidos a cada deploy.
- **Busca por termos compostos** continua quebrada.

---

## Timeline Recomendado

### Sprint 1: Quick Wins (1-2 dias)

Correcoes rapidas que geram resultado imediato e constroem confianca na equipe.

| Item | Descricao em linguagem de negocio | Horas |
|------|-----------------------------------|-------|
| Acentos em badges | Corrigir texto sem acentuacao visivel para usuarios | 0.25h |
| Formulario com submissao nativa | Melhorar experiencia em dispositivos moveis (botao "Enviar" no teclado) | 2.1h |
| Campos obrigatorios sinalizados | Usuarios de leitores de tela sabem o que preencher | 0.5h |
| Prevencao de perda de busca | Aviso antes de sair da pagina durante busca ativa | 0.5h |
| Limpeza de arquivo de teste vazio | Higiene de codigo (5 minutos) | 0.1h |
| Versao centralizada | Evitar inconsistencias na identificacao da versao do sistema | 1h |
| Restricao de headers | Fechar permissividade desnecessaria na API | 1h |
| Cores corrigidas para temas | Corrigir elementos visuais quebrados nos temas Sepia e Paperwhite | 1.5h |
| Protecao contra travamento de IA | Adicionar limite de tempo nas chamadas de inteligencia artificial | 2h |

- **Custo:** R$ 1.350 (~9 horas)
- **ROI:** Imediato -- melhoria de qualidade perceptivel + prevencao de travamento do sistema

### Sprint 2: Correcoes Criticas (1 semana)

Itens que bloqueiam o lancamento publico e a evolucao do produto.

| Item | Descricao em linguagem de negocio | Horas |
|------|-----------------------------------|-------|
| Autenticacao de usuarios | Cada usuario tera acesso individual, com rastreabilidade e limites de uso | 8-16h |
| Busca por termos compostos | Usuarios poderao pesquisar "camisa polo" como uma expressao unica | 3h |
| Otimizacao de memoria e downloads | Eliminar triplicacao de dados em memoria e resolver falhas de download | 8-16h |
| Sistema de filas duravel | Buscas em andamento sobrevivem a atualizacoes do sistema | 12-20h |
| Remocao de codigo morto | Limpar 3 fontes de dados desabilitadas, reduzindo complexidade | 8-16h |
| Auditoria de contraste visual | Garantir legibilidade em todos os 5 temas (obrigacao legal) | 4h |

- **Custo:** R$ 6.450 - R$ 11.250 (~43-75 horas)
- **ROI:** Seguranca + estabilidade -- habilita lancamento publico

### Sprint 3: Fundacao Tecnica (1-2 semanas)

Fortalecimento da base tecnica para suportar crescimento.

| Item | Descricao em linguagem de negocio | Horas |
|------|-----------------------------------|-------|
| Modernizacao de chamadas de IA | Sistema nao trava mais quando multiplos usuarios buscam ao mesmo tempo | 4-8h |
| Downloads sem limite de tempo | Arquivos grandes nao falham por timeout do servidor | 4-8h |
| Paginacao de resultados | Resultados carregam mais rapido, consumindo menos dados | 8-16h |
| Headers de seguranca | Protecoes padrao da web implementadas (CSP, HSTS) | 4-8h |
| Timeout acessivel | Usuarios com deficiencia tem tempo suficiente para confirmar acoes | 1h |
| Reducao de requisicoes | Sistema inteligente que reduz carga no servidor em 80% | 2-4h |
| Teste automatico pos-atualizacao | Sistema verifica automaticamente se esta funcionando apos cada deploy | 2-4h |
| Filtro de prazo | Usuarios veem apenas licitacoes com prazo aberto | 4-8h |

- **Custo:** R$ 4.350 - R$ 8.550 (~29-57 horas)
- **ROI:** Performance + velocidade de desenvolvimento

### Sprint 4: Polimento e Evolucao (1-2 semanas)

Itens que habilitam a proxima fase de crescimento do produto.

| Item | Descricao em linguagem de negocio | Horas |
|------|-----------------------------------|-------|
| Banco de dados | Habilita historico de buscas, preferencias e funcionalidades que exigem persistencia | 8-16h |
| Versionamento de API | Atualizacoes no backend nao quebram a interface do usuario | 4-8h |
| Testes de contrato | Backend e frontend validados automaticamente um contra o outro | 4-8h |
| Componentes de interface acessiveis | Menus e dialogos funcionam corretamente com leitores de tela | 3h |
| Alinhamento visual de temas | Eliminacao de flash visual ao trocar de tema | 3h |
| Indicador de conexao | Usuarios sabem quando estao sem internet (em vez de erros genericos) | 4h |
| Simplificacao de componente grande | Componente de 450+ linhas dividido em partes menores e testaveis | 6h |
| Testes de integracao | Frontend e backend testados juntos automaticamente no CI | 4-8h |

- **Custo:** R$ 5.400 - R$ 8.400 (~36-56 horas)
- **ROI:** Experiencia do usuario + velocidade de entrega de novas funcionalidades

---

## ROI da Resolucao

| Dimensao | Investimento | Retorno Esperado |
|----------|--------------|------------------|
| Financeiro | R$ 23.250 - R$ 34.800 | R$ 95.000 - R$ 305.000 em riscos evitados |
| Tempo | 155 - 232 horas | Reducao de 40-60% no tempo para novas funcionalidades |
| Prazo | 5-6 semanas | Produto seguro, estavel e pronto para escalar |
| Seguranca | R$ 7.800 - R$ 12.600 (Sprints 1+2) | Protecao contra indisponibilidade, abuso e bloqueio pelo PNCP |
| Performance | R$ 4.350 - R$ 8.550 (Sprint 3) | Downloads confiaveis, busca rapida, servidor estavel |
| Escalabilidade | R$ 5.400 - R$ 8.400 (Sprint 4) | Banco de dados + API versionada = fundacao para crescer |

### Calculo de ROI

**Cenario conservador:**

- Investimento: R$ 23.250
- Riscos evitados (ponderados por probabilidade): R$ 95.000
- **ROI: 4:1** -- cada R$ 1 investido evita R$ 4 em perdas potenciais

**Cenario moderado:**

- Investimento: R$ 29.000 (ponto medio)
- Riscos evitados: R$ 200.000
- **ROI: 7:1** -- cada R$ 1 investido evita R$ 7 em perdas potenciais

**Cenario pessimista (multiplos riscos simultaneos):**

- Investimento: R$ 34.800
- Perdas potenciais evitadas: R$ 450.000
- **ROI: 13:1**

### Beneficios Nao Quantificaveis

- Conformidade com a Lei Brasileira de Inclusao (Lei 13.146/2015)
- Conformidade com LGPD (protecao de dados)
- Confianca do mercado em ferramenta que interage com governo
- Capacidade de atrair investimento com base tecnica solida
- Base de codigo limpa atrai e retem desenvolvedores talentosos

---

## Proximos Passos

1. [ ] Aprovar orcamento de R$ 23.250 - R$ 34.800 para o plano completo (4 sprints, 5-6 semanas)
2. [ ] Iniciar Sprint 1 (Quick Wins) imediatamente -- R$ 1.350, retorno em 1-2 dias
3. [ ] Alocar desenvolvedor backend para Sprint 2 (autenticacao + filas)
4. [ ] Alocar desenvolvedor frontend para Sprint 2 (busca + acessibilidade)
5. [ ] Suspender divulgacao publica ate conclusao do Sprint 2
6. [ ] Medir cobertura de testes do backend (`pytest --cov`) -- acao pendente pre-execucao
7. [ ] Definir provedor Redis e infraestrutura para Sprint 3
8. [ ] Review semanal de progresso a cada sprint

### Decisoes Necessarias

| Decisao | Responsavel | Prazo |
|---------|-------------|-------|
| Aprovar orcamento do plano completo | Diretor de Produto | Imediato |
| Modelo de autenticacao (JWT stateless vs outro) | CTO + Produto | Antes do Sprint 2 |
| Provedor de infraestrutura Redis | CTO / DevOps | Antes do Sprint 3 |
| Banco de dados para persistencia (Sprint 4) | CTO / DevOps | Semana 4 |
| Politica de rotacao de secrets e credenciais | DevOps + Seguranca | Sprint 2 |

---

## Anexos

### Documentos de Referencia

| Documento | Localizacao |
|-----------|-------------|
| Assessment Tecnico Completo (55 debitos detalhados) | [technical-debt-assessment.md](../prd/technical-debt-assessment.md) |
| Arquitetura do Sistema | [system-architecture.md](../architecture/system-architecture.md) |
| Especificacao Frontend | [frontend-spec.md](../frontend/frontend-spec.md) |
| Review QA | [qa-review.md](../reviews/qa-review.md) |
| Review UX Specialist | [ux-specialist-review.md](../reviews/ux-specialist-review.md) |

### Glossario para Stakeholders

| Termo | Significado |
|-------|-------------|
| PNCP | Portal Nacional de Contratacoes Publicas -- fonte dos dados de licitacoes |
| WCAG AA | Padrao internacional de acessibilidade digital (nivel intermediario) |
| LBI | Lei Brasileira de Inclusao (Lei 13.146/2015) -- exige acessibilidade digital |
| LGPD | Lei Geral de Protecao de Dados -- regulamenta tratamento de dados pessoais |
| Sprint | Ciclo de trabalho com duracao e entregas definidas |
| Debito tecnico | Decisoes de implementacao que funcionam hoje mas criam riscos ou custos futuros |
| JWT | Token de autenticacao que identifica usuarios sem precisar de banco de dados |
| Redis | Banco de dados em memoria usado para cache e filas de processamento |
| CSP / HSTS | Protecoes padrao da web que previnem ataques comuns |
| ROI | Retorno sobre investimento -- quanto cada real investido gera em valor ou economia |

### Metodologia

- **Taxa base:** R$ 150/hora (desenvolvedor mid-senior)
- **Faixas de estimativa:** Horas minimas e maximas por item, validadas por 3 especialistas (arquiteto, UX, QA)
- **Riscos financeiros:** Estimados com base em benchmarks de mercado para empresas SaaS B2G (Business-to-Government)
- **ROI:** Calculado como (riscos evitados ponderados por probabilidade) / (investimento em resolucao)
- **Evolucao:** Comparacao direta com assessment v1.0 (07/03/2026)

---

*Relatorio preparado em 2026-03-09*
*Baseado no Assessment Tecnico FINAL v2.0 (Brownfield Discovery Fases 1, 3, 4, 6, 7)*
*Validado por: @architect (Atlas), @ux-design-expert (Vera), @qa (Quinn)*
*Para duvidas, contate @analyst (Ada)*
