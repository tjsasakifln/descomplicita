# Story 3.1 -- Otimizacao: Melhorias Pos-POC

## Contexto

Apos as fases 0, 1 e 2 resolverem debitos criticos, quick wins e fundacoes estruturais, esta story consolida todos os itens de medio/longo prazo que melhoram escalabilidade, cobertura de testes e experiencia do usuario. Estes itens sao pos-POC: devem ser executados apenas apos validacao do produto com stakeholders e decisao de escalar.

A story tambem inclui itens explicitamente marcados como "Fora de Escopo POC" no assessment, que so devem ser implementados se houver demanda comprovada.

Referencia: `docs/prd/technical-debt-assessment.md` -- Secao "Sprint 3: Otimizacao" e "Fora de Escopo POC"

## Objetivo

Completar a resolucao de debitos tecnicos remanescentes, elevar cobertura de testes, implementar testes de integracao reais no CI, e avaliar melhorias de experiencia do usuario que dependem de feedback real de uso.

## Tasks

### Qualidade e Cobertura (~24h)

- [ ] **Task 1** (TD-SYS-004) -- Implementar testes de integracao reais no CI substituindo stubs/placeholders existentes nos workflows -- 8h
- [ ] **Task 2** (TD-SYS-009 / TD-UX-014) -- Aumentar cobertura de testes frontend: branches de 52.74% para 65%+, lines mantido em 65%+. Focar em caminhos criticos nao cobertos (auth flows, error handling, edge cases de busca) -- 16h

### Design System e UX (~12h)

- [ ] **Task 3** (TD-UX-020) -- Criar componentes Input e Select reutilizaveis seguindo padrao do Button (variantes, tamanhos, estados de erro/disabled). Substituir ~10 inputs com classes duplicadas -- 4h
- [ ] **Task 4** (TD-UX-005) -- Implementar rota de resultados com deep-linking (`/resultado/:job_id`). Requer design de URL, tratamento de TTL/expiracao do Redis, UX de resultado expirado -- 8h

### Governanca e Infraestrutura (~11h)

- [ ] **Task 5** (TD-SYS-012) -- Implementar estrategia de depreciacao e versionamento de API. Definir headers de depreciacao, documentar lifecycle de endpoints -- 4h
- [ ] **Task 6** (TD-SYS-020) -- Expandir configuracao ESLint com regras TypeScript strict e plugins de acessibilidade (eslint-plugin-jsx-a11y) -- 3h
- [ ] **Task 7** (TD-SYS-017) -- Implementar logging estruturado no frontend com correlacao `X-Correlation-Id` para rastreamento cross-stack -- 4h

### Limpeza Residual (~6h)

- [ ] **Task 8** (TD-DB-003) -- Adicionar UNIQUE constraint em `users.email` (defesa em profundidade; `auth.users` ja protege) -- 0.5h
- [ ] **Task 9** (TD-DB-012) -- Adicionar trigger/constraint para limitar quantidade de saved_searches por usuario no DB -- 1h
- [ ] **Task 10** (TD-DB-013) -- Implementar metricas de falha de persistencia em `database.py` (contadores em vez de silent `except: log + return None`) -- 1.5h
- [ ] **Task 11** (TD-UX-009) -- Adicionar skeleton loading state para select de setores na pagina inicial -- 1h
- [ ] **Task 12** (TD-UX-015) -- Adicionar indicacao visual quando setores estao em modo fallback/cache -- 1h
- [ ] **Task 13** (TD-UX-017) -- Auditar dados do carouselData.ts com especialista juridico (categorias, fontes, precisao) -- 1h

### Fora de Escopo POC (avaliar sob demanda) (~36h)

- [ ] **Task 14** (TD-UX-016) -- SSE para progresso em tempo real (substituir polling com backoff). So implementar se houver reclamacoes de latencia -- 12h
- [ ] **Task 15** (TD-UX-018) -- PWA / Service Worker. So implementar se houver demanda offline comprovada -- 8h
- [ ] **Task 16** (TD-UX-012) -- i18n framework. So implementar se houver plano de internacionalizacao -- 16h

## Criterios de Aceite

- [ ] Testes de integracao no CI executam cenarios reais (nao stubs)
- [ ] Coverage frontend branches >= 65%
- [ ] Componentes Input e Select reutilizaveis criados e adotados
- [ ] Zero debitos criticos ou altos remanescentes
- [ ] Todos os 57 debitos rastreados com status (resolvido / aceito / deferido)
- [ ] Items "Fora de Escopo POC" documentados com criterios de gatilho

## Testes Requeridos

- [ ] Testes de integracao CI com cobertura de cenarios reais (integration)
- [ ] Coverage report mostra branches >= 65% (CI)
- [ ] Testes unitarios dos componentes Input/Select (unit)
- [ ] Testes de rota de resultado: deep-link funcional, expirado mostra UX adequada (e2e)
- [ ] ESLint expandido passa sem erros no CI (CI)
- [ ] Testes de metricas de persistencia: contadores incrementam em cenarios de falha (unit)

## Estimativa

- **Horas:** 89h (53h priorizavel + 36h sob demanda)
- **Complexidade:** Complexo (multiplas areas, longa duracao, requer priorizacao continua)

## Dependencias

- **Depende de:** Stories 2.1 (linter + hooks + main.py decomposto) e 2.2 (auth consolidado, migration runner)
- **Bloqueia:** Nenhuma (story terminal do epic)

## Definition of Done

- [ ] Codigo implementado e revisado para cada task
- [ ] Todos os testes passando
- [ ] Coverage targets atingidos
- [ ] Review aprovado para cada PR
- [ ] Sem regressoes
- [ ] Relatorio final de debitos tecnicos atualizado com status de cada item

---

*Story criada em 2026-03-11 por @pm (Sage)*
*Debitos: TD-SYS-004 (Alto), TD-SYS-009/TD-UX-014 (Alto/Medio), TD-UX-020 (Medio), TD-UX-005 (Medio), TD-SYS-012 (Medio), TD-SYS-020 (Baixo), TD-SYS-017 (Medio), TD-DB-003 (Baixa), TD-DB-012 (Baixa), TD-DB-013 (Baixa), TD-UX-009 (Baixo), TD-UX-015 (Baixo), TD-UX-017 (Baixo), TD-UX-016 (Baixo), TD-UX-018 (Baixo), TD-UX-012 (Baixo)*
