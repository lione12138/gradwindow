# Purdue directory review — 2026-10-05

The complete official main-campus catalogue contains 122 matching master's
cards and 118 distinct programme names. Biomedical Engineering, Mechanical
Engineering, Software Engineering and Sport Management each have two cards with
the same name and admissions URL. They must not inflate the programme count.

Comparison with the saved 120-entry catalogue identifies exactly two absent
names: Art and Design, Art, and Performance. Source checks:

- The former Art admissions URL now redirects to Artificial Intelligence and
  Machine Learning. That target is not evidence for Art admissions:
  https://www.purdue.edu/academics/ogsps/admissions/gradrequirements/westlafayette/art/
- The former Design, Art, and Performance URL returns HTTP 404:
  https://www.purdue.edu/academics/ogsps/admissions/gradrequirements/westlafayette/design-art-and-performance/
- The current Design admissions page explicitly lists an MFA and design areas:
  https://www.purdue.edu/academics/ogsps/admissions/gradrequirements/westlafayette/design/
- The school's MFA page still describes Art or Design, including studio arts:
  https://cla.purdue.edu/academic/rueffschool/ad/mfa/index.html

The last point prevents treating directory absence as proof of closure. Keep the
two former records for separate programme-scope and admissions review; do not
automatically delete, relabel, merge or redirect them to AI or Design.

After checking the complete directory and exact historical difference, the
completeness floor is rebased from 120 to 118 (the full distinct current count,
with no additional tolerance). Eligible master's cards missing a title or
admissions link now fail explicitly rather than being silently skipped. Duplicate
cards continue to collapse to one programme.

This repair recovers catalogue monitoring only. Window discovery is pending;
the reviewed Design page includes month/day and month-only guidance without a
complete exact opening-and-closing pair. No dates were inferred. No operational
state/candidate files or public data were changed by the dry run.
