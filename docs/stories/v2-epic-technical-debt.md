# Epic: Resolucao de Debitos Tecnicos v2.0 -- Descomplicita (Marco 2026)

## Contexto

Este epic sucede o epic v1.0 (Janeiro 2026) que abordou 57 debitos identificados na primeira avaliacao. A avaliacao v2.0 (Marco 2026) identificou 55 debitos usando uma metodologia revisada (Brownfield Discovery com 7 fases). Alguns debitos sao **novos** (nao existiam na v1.0), alguns **permanecem** (existiam na v1.0 mas nao foram totalmente resolvidos), e alguns da v1.0 ja foram implementados e nao aparecem mais.

### Relacao com v1.0

- **v1.0:** 57 debitos (IDs TD-001 a TD-057), 6 sprints, ~173-287 horas
- **v2.0:** 55 debitos (IDs TD-C/H/M/L, UXD, XD-SEC/API/PERF/TEST), 4 sprints, ~155-232 horas
- **Debitos resolvidos na v1.0** que nao aparecem na v2.0: CORS wildcard origins (TD-001), Dockerfile root (TD-002), debug endpoints (TD-055), god component (TD-004), branding Descomplicita (TD-016/054), entre outros
- **Debitos que persistem:** autenticacao (v1 TD-003 -> v2 TD-C02), in-memory job store (v1 TD-005 -> v2 TD-H01/H02), Excel delivery (v1 TD-007 -> v2 TD-C01), cores hardcoded (v1 TD-044 -> v2 UXD-018/019/021), entre outros
- **Debitos novos na v2.0:** UXD-021/022/023, cadeia de cascading failure (TD-M04->TD-L06->TD-H03), polling sem backoff (XD-PERF-03), smoke tests (XD-TEST-02)

## Objetivo

Resolver sistematicamente todos os 55 debitos tecnicos identificados na avaliacao v2.0 (FINAL, validada por QA) em 4 sprints, priorizando seguranca critica, bloqueadores funcionais, e obrigacoes legais de acessibilidade (LBI 13.146/2015).

## Escopo

- Total de debitos: 55 (3 Criticos, 10 Altos, 25 Medios, 17 Baixos)
- Sprints planejados: 4 (Sprint 1: Quick Wins, Sprint 2: Critical, Sprint 3: Foundation, Sprint 4: Polish)
- Timeline: ~4-6 semanas
- Esforco estimado: 155-232 horas
- Fonte autoritativa: `docs/prd/technical-debt-assessment.md` (v2.0 FINAL)

## Criterios de Sucesso

- [ ] Todos os 3 debitos criticos resolvidos (TD-C01, TD-C02, XD-SEC-02)
- [ ] Todos os 10 debitos de alta severidade resolvidos
- [ ] Frontend statement coverage >= 75%
- [ ] Frontend branch coverage >= 60%
- [ ] Backend statement coverage >= 75% (threshold atual: 70%)
- [ ] Zero violacoes WCAG AA criticas/serias (axe-core)
- [ ] Autenticacao JWT stateless implementada
- [ ] Security headers completos (CSP, HSTS, Referrer-Policy, Permissions-Policy)
- [ ] Smoke tests pos-deploy automatizados
- [ ] Vulnerabilidades de dependencias: 0 criticas, 0 altas
- [ ] Jobs sobrevivem restart via fila duravel

## Stories

| Story | Sprint | Horas | Prioridade |
|-------|--------|-------|------------|
| v2-story-0.0: Quick Wins | Sprint 1 (1-2 dias) | ~8h | Alta |
| v2-story-1.0: Security & Critical Fixes | Sprint 2 (1 semana) | ~40-60h | Critica |
| v2-story-2.0: Frontend Architecture | Sprint 3 (1-2 semanas) | ~20-30h | Media |
| v2-story-3.0: Frontend Quality | Sprint 3-4 (1-2 semanas) | ~15-25h | Media |
| v2-story-4.0: Backend Architecture | Sprint 3 (1-2 semanas) | ~25-40h | Alta |
| v2-story-5.0: Polish & Infrastructure | Sprint 4 (1-2 semanas) | ~30-40h | Media |

**Esforco Total Estimado: 155-232 horas**

## Grafo de Dependencias

```
v2-story-0.0 (Quick Wins)
  |
  v
v2-story-1.0 (Security/Critical) --- prerequisito para todas as demais
  |           |           |
  v           v           v
v2-story-2.0  v2-story-4.0  v2-story-3.0
(FE Arch)     (BE Arch)     (FE Quality)
  |           |           |
  +-----+-----+-----------+
        |
        v
  v2-story-5.0 (Polish)
```

Frontend (stories 2.0, 3.0) e Backend (story 4.0) podem ser paralelizados.

## Riscos

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| JWT sem database cria half-solution | Alta | Alto | JWT stateless como interim; planejar DB na mesma sprint |
| Excel streaming quebra rota download BFF | Media | Alto | Feature flag; testar e2e antes de cutover |
| Remocao de dead code quebra source registry | Media | Medio | Testes de integracao do orquestrador antes da remocao |
| CSP quebra inline theme script | Alta | Medio | Resolver TD-M10 antes ou simultaneamente com TD-M07 |
| Rate limiting falha atras de proxy | Media | Alto | Verificar X-Forwarded-For handling |
| Tokenizacao multi-palavras invalida saved searches | Media | Baixo | Migrar saved searches ou fallback de parsing |

## Notas

- Horas assumem um desenvolvedor por task
- Frontend e backend podem ser paralelizados com desenvolvedores separados
- v1.0 IDs (TD-001 a TD-057) e v2.0 IDs (TD-C/H/M/L, UXD, XD-*) sao esquemas independentes
- A avaliacao v2.0 foi validada por @architect, @ux-design-expert e @qa
- Obrigacao legal: LBI 13.146/2015 aplica-se a esta ferramenta governamental

---

*Criado: 2026-03-09*
*Fonte: docs/prd/technical-debt-assessment.md (v2.0 FINAL)*
*Epic v1.0: docs/stories/epic-technical-debt.md (Janeiro 2026)*
