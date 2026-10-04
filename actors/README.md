# Article V Actors Directory: data and methods

`actors_public.csv` lists 1,655 people, organizations, official bodies, events, lawsuits, publications, coalitions, funders and registered lobbyists involved in campaigns for and against an Article V convention, from 1788 to 2026. It is the public export of a private research database. Every value is derived from that database by a fixed script, and no row is edited by hand.

- Browse: https://articlevmeasured.pages.dev/actors/
- Charts: https://articlevmeasured.pages.dev/actors/facts/
- Corrections and removal requests: see `CORRECTIONS.md`.

**This is a research collection, not a census.** It was gathered by AI research agents working in topic batches. A larger count can reflect where research looked. A listing records a documented connection to the convention debate. It does not imply endorsement, wrongdoing, or agreement with an affiliated organization.

## Columns

| Column | Meaning |
|---|---|
| `id` | Stable identifier (`AV` plus four digits). IDs never change; when two records are merged, the lower ID survives. |
| `name` | Person, organization, body, event, case or publication. Legislators whose first name could not be confirmed appear in the form `Surname (ST Office)`. |
| `entity_type` | `person`, `org`, `official_body`, `event`, `publication`, `coalition`, `funder`, `lobbyist`, `litigation`, `caucus` or `online_community`. |
| `publish_tier` | `full`: every column is published. `role_only`: a private individual; only name, type, scope, state, affiliation, role, years and sources are published. |
| `stance` | The record's position on calling a convention; see below. Blank for `role_only` rows. |
| `amendment_focus` | Subjects, separated by semicolons (for example `balanced_budget;term_limits`). `plenary` means an open, unlimited convention; `all` marks records that address every subject. |
| `scope` | `national`, `state`, `multistate` or `local`. |
| `state` | Two-letter postal code, `US` for national, or `INTL`. |
| `parent_or_affiliation` | Organization or body the record is tied to, as stated in its sources. |
| `role_title` | Office or role as stated in the sources. |
| `active_years` | Years of documented Article V involvement, for example `2015-2026`. A range ends in `present` only where a source showed current involvement when checked; otherwise it stops at the latest year a source shows. `unknown` marks a start year no source gives. |
| `status` | `active`: a source shows Article V involvement in 2024 or later. `deceased`: sourced. `concluded`: a past event, case or one-time publication. `defunct` or `dormant`: an organization a source shows has ended or paused. `unknown`: no source establishes current status. |
| `website` | Official site, where one exists. |
| `description` | What the record documents, in the database's own words, with dates, bills and quotes taken from the sources. Several notes on one actor are separated by ` \|\| `. |
| `key_people` | People named in the sources in connection with the record. |
| `funding_notes` | Amounts and years from filings or reports, with the source named. Pay is shown only for top officers. |
| `source_urls` | Cited sources, separated by semicolons. Offline sources (the printed program of the October 2026 Harvard Law School conference) are cited by title. |
| `verification` | `fetched`: a page that was loaded supports the record. `primary_document`: an offline primary document supports it. |
| `last_checked` | Date the record was last checked. |

## Stance codes

| Code | Meaning |
|---|---|
| `pro_limited_convention` | Supports a convention limited to one subject or set of subjects. |
| `pro_convention` | Supports a convention, without a limit recorded. |
| `anti_convention` | Opposes a convention. |
| `pro_amendment_via_congress` | Supports the amendment, but proposed by Congress rather than by a convention. |
| `neutral_research` | Research, reference or procedural role without a position. Laws that only set delegate procedures are coded here. |
| `mixed` | Positions differ over time or within the record. |
| `unknown` | No position is established. |
| `unverified` | Shown in place of a position that rests only on an inference or a search result. |

**How stance is assigned:**
- **Own words or actions only.** Stance comes from an actor's own statement, vote, sponsorship, testimony or writing, and reflects the most recent evidence; the history goes in the description.
- **Organizational roles.** Officers and staff of an Article V campaign organization (president, chair, director, founder, coordinator, campaign staff, or a lobbyist registered for a single-purpose Article V group) take the organization's stance. Board, advisory, honorary and scholar listings are affiliation, not stance.
- **Attendance proves nothing.** Being at an event, belonging to an organization, or being listed alongside others is never evidence of a position. A code may describe a statement made years ago.

## How the data was built and checked

1. **Research.** Research agents gathered records in topic batches: national campaigns, opposition, states, official bodies, scholarship, historical campaigns, money and lobbying, the printed program of the October 2026 Harvard Law School conference "V the People", thin-state coverage, Convention of States state directors, and a 2025–26 expansion (bills in every state, lobbyists, official bodies, funding, historical organizers, opposition leaders, scholarship).
2. **Merging.** Duplicates were merged by name and alias, and stable IDs were kept.
3. **Two audits.** An outside AI audit checked a random sample of an earlier version. A second audit, run by the same AI system that built the data, checked every field of a fresh random sample, reviewed every disputed stance, and replaced search-snippet sources. Their findings were corrected. Neither audit gives an error rate for the whole collection.
4. **Field-level sourcing pass.** Every record not already fully confirmed (1,625 records, 17,809 specific claims) was checked against its cited pages: names, roles, dates, numbers, bills, votes, quotes. After the pass, 94% of those claims are supported by a page that was loaded, up from about 83%. Unsupported details were sourced (1,969 claims) or removed (1,035). Most of the remaining claims sit on sites that block automated access, such as several state lobbyist registries. Some of those were verified in an earlier round and kept.
5. **Public export.** Private individuals are published by role only. A stance resting only on inference is not shown. Pay appears only for top officers. The export fails if any email address, phone number, street address or local file path would be published.

## Known gaps

- **Lobbyist registries.** About 20 state registries were not searched, and Kansas and Illinois sit behind CAPTCHAs.
- **Recent bills.** No 2025–26 bills were found for Colorado or Florida, whose search pages failed.
- **Funding.** It is documented only where filings tie money to Article V work; most opposition work is funded from general budgets.
- **State application data.** The application and rescission counts used in the paper are a separate dataset. They are not part of this table.

## License

The actors data is original description with citations, licensed under CC BY 4.0 (see `../LICENSE-CC-BY-4.0.txt` at the repository root). The facts it reports come from the cited sources, whose own terms apply to material taken directly from them.
