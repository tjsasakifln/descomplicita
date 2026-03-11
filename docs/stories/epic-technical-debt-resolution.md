# Epic: Resolucao de Debitos Tecnicos -- Descomplicita POC

## Objetivo

Resolver os debitos tecnicos identificados no assessment tecnico para tornar o POC viavel, seguro e apresentavel para stakeholders. O foco e eliminar riscos criticos de demonstracao (visual e seguranca), consolidar quick wins de alto impacto, e estabelecer fundacoes para crescimento sustentavel.

## Escopo

- ~57 debitos tecnicos identificados (apos deduplicacao de 63 brutos)
- ~152 horas de esforco estimado total
- Foco POC: 12h de correcoes bloqueantes (Fase 0)
- Assessment validado por 4 especialistas: @architect (Atlas), @data-engineer (Forge), @ux-design-expert (Pixel), @qa (Shield)
- Commit de referencia: 2a76827b (HEAD de main)

## Timeline

| Fase | Descricao | Duracao | Horas | Custo (R$150/h) |
|------|-----------|---------|-------|-----------------|
| **Fase 0** | Pre-Demo (BLOQUEANTE) | 1-2 dias | 12h | R$ 1.800 |
| **Fase 1** | Quick Wins | 1 semana | 15h | R$ 2.250 |
| **Fase 2** | Fundacao | 2-3 semanas | 36h | R$ 5.400 |
| **Fase 3** | Otimizacao | 4-6 semanas | 89h | R$ 13.350 |
| **Total** | | ~8 semanas | **152h** | **R$ 22.800** |

## Stories

| Story | Nome | Fase | Horas | Prioridade | Status |
|-------|------|------|-------|------------|--------|
| [Story 0.1](story-0.1-pre-demo-visual.md) | Pre-Demo: Correcoes Visuais | Fase 0 | 5.5h | BLOQUEANTE | Pendente |
| [Story 0.2](story-0.2-pre-demo-security.md) | Pre-Demo: Seguranca e Integridade | Fase 0 | 6.5h | BLOQUEANTE | Pendente |
| [Story 1.1](story-1.1-quick-wins-frontend.md) | Quick Wins: Frontend e Design System | Fase 1 | 8h | Alta | Pendente |
| [Story 1.2](story-1.2-quick-wins-backend.md) | Quick Wins: Backend e Infraestrutura | Fase 1 | 7h | Alta | Pendente |
| [Story 2.1](story-2.1-main-decomposition.md) | Fundacao: Decomposicao do main.py | Fase 2 | 14h | Media | Pendente |
| [Story 2.2](story-2.2-auth-consolidation.md) | Fundacao: Consolidacao de Autenticacao | Fase 2 | 22h | Media | Pendente |
| [Story 3.1](story-3.1-optimization.md) | Otimizacao: Melhorias Pos-POC | Fase 3 | 89h | Baixa | Pendente |

## Distribuicao por Area

| Area | Stories | Horas |
|------|---------|-------|
| Frontend/UX | 0.1, 1.1, parcial de 3.1 | ~48h |
| Backend/Sistema | 0.2, 1.2, 2.1, 2.2, parcial de 3.1 | ~88h |
| Database | 0.2, parcial de 1.2 e 3.1 | ~16h |

## Criterios de Sucesso do Epic

- [ ] Todos os debitos criticos resolvidos (4 itens)
- [ ] AuthModal funcional em todos os 5 temas (light, paperwhite, sepia, dim, dark)
- [ ] Artefatos SQLite removidos (descomplicita.db, aiosqlite, referencias)
- [ ] python-jose substituido por PyJWT em todo o codebase
- [ ] verify_aud habilitado na validacao de tokens Supabase
- [ ] Schema drift rastreado em migracoes SQL
- [ ] Coverage mantida >= thresholds atuais (backend 70%+, frontend branches 52.74%+)
- [ ] Zero vulnerabilidades criticas em dependencias
- [ ] Badges e cores consistentes com design tokens em todos os temas

## Definition of Done

- [ ] Todos os stories da Fase 0 (0.1 + 0.2) completos
- [ ] Todos os stories da Fase 1 (1.1 + 1.2) completos
- [ ] QA review aprovado para cada story
- [ ] Demo realizada com sucesso em pelo menos 3 temas distintos
- [ ] Nenhuma regressao nos 1.925+ testes existentes
- [ ] CI/CD verde em todos os 9 workflows

## Documentos de Referencia

| Documento | Localizacao |
|-----------|-------------|
| Assessment tecnico completo | `docs/prd/technical-debt-assessment.md` |
| Relatorio executivo | `docs/reports/TECHNICAL-DEBT-REPORT.md` |
| Revisao banco de dados | `docs/reviews/db-specialist-review.md` |
| Revisao UX | `docs/reviews/ux-specialist-review.md` |
| Gate de qualidade | `docs/reviews/qa-review.md` |

## Grafo de Dependencias entre Stories

```
Story 0.1 (Visual) -----> Story 1.1 (Quick Wins Frontend)
                                |
Story 0.2 (Seguranca) --> Story 1.2 (Quick Wins Backend)
                                |
                          Story 2.1 (main.py) ---> Story 3.1 (Otimizacao)
                          Story 2.2 (Auth)    --/
```

- Stories 0.1 e 0.2 sao independentes entre si (podem ser executadas em paralelo)
- Story 1.1 depende de 0.1 (tokens visuais corrigidos antes de adotar Button)
- Story 1.2 depende de 0.2 (seguranca basica antes de hardening adicional)
- Stories 2.1 e 2.2 dependem de 1.2 (linter configurado)
- Story 3.1 depende de todas as anteriores

---

*Epic criado em 2026-03-11 por @pm (Sage)*
*Baseado no Technical Debt Assessment v1.0 FINAL*
