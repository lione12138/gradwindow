---
name: gradwindow-seo
description: Audit and improve GradWindow search visibility without weakening its admissions-data trust boundaries. Use for SEO reviews, Semrush keyword or competitor research, indexability and crawlability fixes, metadata or structured-data work, internal linking, sitemap and robots changes, search landing pages, social previews, and SEO regression checks in the GradWindow repository.
---

# GradWindow SEO

Improve discoverability with evidence, crawlable content, and verified data. Treat rankings and admissions dates as trust-sensitive facts.

## Workflow

1. Start with `git status --short --branch` and preserve unrelated changes.
2. Read `AGENTS.md`, then inspect `web/`, `src/gradwindow/site.py`, `tests/test_site.py`, `data/applications.json`, and the generated-page inputs relevant to the request.
3. Build to a disposable directory outside the repository or under `site/`; never hand-edit `site/`.
4. Run `scripts/audit_site.py <build-dir> --base-url https://gradwindow.com` to establish a technical baseline.
5. When Semrush is connected, use it for current keyword, ranking, competitor, and backlink evidence. Record the database, locale, date, and metric behind every recommendation. If it is unavailable, say so and continue with local and live-site evidence; never invent Semrush results.
6. Read [references/seo-checklist.md](references/seo-checklist.md) for prioritization, keyword mapping, and trust rules.
7. Implement the smallest high-value change in source files. Prefer crawlability, unique intent, and useful internal links over adding repetitive metadata.
8. Add or update regression tests for behavioral SEO changes.
9. Rebuild, rerun the audit script, and run the repository checks required by `AGENTS.md`.
10. Report evidence, modified surfaces, verification results, and remaining measurement gaps separately.

## Guardrails

- Publish only exact official windows already approved in `data/applications.json` or official recurring policies already accepted by the pipeline.
- Keep predictions explicitly unofficial. Never turn keyword demand into fabricated dates, applicant categories, translations, or university claims.
- Do not create thin pages merely to target keyword variants. Require a distinct user intent, substantive source-backed content, and crawlable internal links.
- Do not add `hreflang` unless separate canonical language URLs exist.
- Do not block a `noindex` page in `robots.txt`; crawlers must be able to read the directive.
- Keep canonical URLs absolute, HTTPS, unique, and independent of filters or tracking parameters.
- Preserve official source links and the distinction between verified, recurring, predicted, and manual-check records.
- Treat third-party SEO metrics as prioritization evidence, not authority for admissions facts.

## Expected output

Return:

- the baseline evidence and highest-priority issues;
- Semrush findings with provenance when the connector was usable;
- implemented changes and why they help users and crawlers;
- exact validation commands and outcomes;
- follow-up items that require post-deployment search-console or ranking data.
