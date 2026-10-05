# University of Vienna directory migration — 2026-10-05

The old master's directory redirects to:
https://studieren.univie.ac.at/en/find-your-degree-programme/masters-programmes

The new directory no longer appends `(Master)` to link labels and uses both
`find-your-degree-programme` and `find-you-degree-programme` in detail URLs.
The old path/label checks therefore returned zero programmes. Both spellings
are present in the official HTML; neither is a guessed URL correction.

Accept these official master's detail paths with plain names, retain the legacy
path/label combination, and require the university's study-site hostname. Exclude
directory navigation, visiting-master guidance and external links. The shared
catalogue builder still deduplicates repeated links. The minimum remains 105.
The general admissions route was also updated to its verified redirect target:
https://studieren.univie.ac.at/en/applying-for-a-programme/admission-info/mag

Live dry run: 114 programme names versus 113 in the saved catalogue, with 18 new
candidate IDs. Seventeen former IDs are absent because names and/or programme
offerings changed; these need review and must not be automatically classified as
closures. The Physics detail page returned HTTP 200 and confirms its master's
programme heading:
https://studieren.univie.ac.at/en/find-you-degree-programme/masters-programmes/physics-masters-programme

This is catalogue recovery only. Exact application-window discovery and applicant
scope review remain pending. No operational candidate/state or public data files
were written, no programme IDs were manually remapped, and no dates were inferred.
