# Out-of-Scope POC: Trigger Criteria for Deferred Items

**Date:** 2026-03-11
**Status:** Documented, awaiting demand signals

## Task 14 — SSE for Real-Time Progress (TD-UX-016)

**Current:** Polling with exponential backoff (1s → 15s), 10-minute timeout.

**Trigger criteria — implement when ANY of:**
- [ ] 3+ user complaints about perceived latency during search progress
- [ ] Analytics show >20% of users refreshing the page during a search
- [ ] Average search time exceeds 3 minutes (SSE reduces perceived wait)
- [ ] Product decision to support real-time collaboration features

**Implementation notes:**
- Replace polling in `useSearchJob.ts` with `EventSource` API
- Backend: Add SSE endpoint `GET /buscar/{job_id}/stream`
- Fallback: Keep polling for browsers without SSE support
- Estimated effort: 12h

---

## Task 15 — PWA / Service Worker (TD-UX-018)

**Current:** Standard web app, no offline capability.

**Trigger criteria — implement when ANY of:**
- [ ] Mobile usage exceeds 40% of total traffic (analytics)
- [ ] Users request offline access to saved search results
- [ ] Product decision to publish on app stores via TWA/PWA
- [ ] Competitor analysis shows PWA as competitive advantage

**Implementation notes:**
- Add `next-pwa` or custom service worker via `public/sw.js`
- Cache strategy: Network-first for API, Cache-first for static assets
- Offline: Show cached saved searches + "you are offline" banner
- Push notifications for completed searches (if user opts in)
- Estimated effort: 8h

---

## Task 16 — i18n Framework (TD-UX-012)

**Current:** All UI text hardcoded in Portuguese (pt-BR).

**Trigger criteria — implement when ANY of:**
- [ ] Business expansion plan to Spanish-speaking countries (LATAM)
- [ ] Government requirement for English or Spanish interface
- [ ] >5% of traffic from non-Portuguese-speaking regions
- [ ] Partnership with international procurement platforms

**Implementation notes:**
- Use `next-intl` or `react-i18next` with App Router support
- Extract all strings to `/messages/{locale}.json`
- Start with pt-BR (current) + es (Spanish) as first target
- URL strategy: `/[locale]/...` prefix
- Estimated effort: 16h

---

## Review Schedule

These criteria should be reviewed quarterly as part of sprint planning.
Next review: 2026-06-11.
