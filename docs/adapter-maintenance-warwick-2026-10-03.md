# Warwick catalogue recovery: 2026-10-03

The official postgraduate course directory no longer contains the legacy
`.feed-item-list-item` markup. Its `course-search.js` fetches the public
SiteBuilder data-entry endpoint with the page path
`/study/postgraduate/courses/course-list`.

Sources inspected directly:

- <https://warwick.ac.uk/study/postgraduate/courses/>
- <https://warwick.ac.uk/study/postgraduate/courses/course-search.js>
- <https://sitebuilder.warwick.ac.uk/sitebuilder2/api/dataentry/entries.json?page=%2Fstudy%2Fpostgraduate%2Fcourses%2Fcourse-list>

The updated adapter recognises the new directory shell, reads the official JSON,
excludes hidden and research-only entries, requires an explicit master's
qualification, resolves relative official links, and preserves the legacy HTML
parser. Duplicate URLs and external hosts are filtered. Award suffixes including
PGDip/PGCert alternatives are normalised before generating programme IDs.

Live dry run: 262 API entries, 132 taught master's programmes after filtering,
three successful official requests. The previous catalogue contained 116
programmes. Added and missing IDs require review because the university has
changed course names and offerings. No public records were removed or promoted.

Catalogue discovery recovered. Programme-level application-window discovery
remains pending: no exact opening/closing pairs are inferred from course start
dates or the central on-time application policy. The 110-programme completeness
guard and application-policy validation remain enabled.
