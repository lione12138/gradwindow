# Mainz source recovery: 2026-10-03

The official course API still works, but the master's guide moved from
`/en/your-application/masters-degrees/` (HTTP 404) to
<https://www.studium.uni-mainz.de/en/your-application/master/> (HTTP 200).
The new official guide retains the two Summer 2027 admission-category periods.

Update the shared application URL so guide retrieval, programme application
links and window source links all use the current route. Existing catalogue
count limits and exact-date validation remain unchanged.

Live dry run: two successful requests, 133 catalogue programmes plus two
admission-category records, and two exact windows matching the previously
parsed dates. The catalogue has one fewer programme than the prior snapshot;
the discovery diff identifies `mainz-w49023-master-of-science` for review.

No candidates were approved and no public data was removed or rewritten.
Catalogue and shared-route discovery recovered; programme-specific exceptions
and the other 133 programmes' individual windows remain unresolved. This is not
a claim of complete programme-level deadline coverage.
