# GradWindow SEO checklist

## Prioritization

Use this order unless evidence supports another choice:

1. Indexability: successful status, canonical URL, robots directives, sitemap inclusion.
2. Crawl paths: every indexable page has at least one meaningful internal link from another indexable page.
3. Search intent: the page answers one distinct query with useful, source-backed content.
4. Trust: official, recurring, predicted, and manual-check records remain visibly distinct.
5. On-page signals: unique title, description, H1, descriptive links, and coherent headings.
6. Structured data and social previews: valid JSON-LD and consistent Open Graph/Twitter metadata.
7. Performance and accessibility: prioritize measured Core Web Vitals and blockers.
8. Authority: earn relevant references and links; never manufacture them.

## Semrush evidence workflow

Use only capabilities exposed by the installed connector. Prefer read-only research.

1. Set the target domain to `gradwindow.com` and record the Semrush database/locale.
2. Capture current organic keywords and landing pages.
3. Compare relevant competitors for keyword gaps. Exclude university-owned admissions sites from product-competitor conclusions.
4. Group opportunities by intent rather than exact wording:
   - master's application deadlines;
   - `[university] master's application deadline`;
   - QS Top 200 graduate or master's applications;
   - `[country] master's application deadlines`;
   - `[month/year] master's application deadlines`.
5. Inspect backlink and referring-domain evidence before recommending outreach.
6. Separate observed metrics from inferences. Include the retrieval date.

Do not claim traffic, rank, search volume, difficulty, or backlinks without a returned metric.

## Page rules

- Home: explain the tracker, its official-source policy, coverage, and the difference between verified dates and estimates.
- University pages: include the university, ranking context, country, intake, scope, exact dates, status, and official source when available.
- Country pages: link to covered universities and state what ranking universe is represented.
- Deadline-month pages: label unofficial predictions in every affected row and avoid implying that mixed records are all verified.
- Source/coverage hub: link internally to university, country, and deadline pages while retaining external official links.
- Utility pages: index only if they provide standalone search value. Keep admin pages `noindex`.

## Structured data

- Use `WebSite` on the home page.
- Use `Dataset` only for downloadable public data with a real license and stable distribution URLs.
- Use `BreadcrumbList` only when visible breadcrumbs match it.
- Prefer `CollectionPage` or `WebPage` over unsupported rich-result markup.
- Validate JSON parsing and content accuracy; markup must describe visible content.

## Verification

Build outside source directories:

```powershell
$env:PYTHONPATH='src'
python -m gradwindow.cli build-site --output <temporary-directory>
python .agents/skills/gradwindow-seo/scripts/audit_site.py <temporary-directory> --base-url https://gradwindow.com
pytest tests/test_site.py
ruff check .
ruff format --check .
npm run lint
npm run format:check
```

After deployment, verify the live canonical, robots file, sitemap, rendered text, structured data, search-console coverage, and Semrush landing-page changes. Ranking changes require time and are not a same-day acceptance criterion.
