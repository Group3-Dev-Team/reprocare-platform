# Data coverage and known limitations

ReproCare only shows facts it can attribute to a source. Where a fact is not recorded, the interface says so
instead of treating it as a negative. This page explains which data the application needs, what a fresh
installation contains, and how to add verified data.

## What each feature depends on

| Feature | Data it reads | When the data is missing |
| --- | --- | --- |
| Service filter (home search, Find Care, map) | `facility_services` links between facilities and the 11 service categories | Searches that include a service return no match. Find Care re-checks each coverage filter on its own and offers "Browse without this filter". |
| Insurer filter and "Care by insurer" | `facility_insurers` links | Same as above. Insurer acceptance is shown as "not recorded", never as "not accepted". |
| Laboratory test menus | `lab_tests` rows per laboratory | Laboratory pages show the listing without a test menu. The service slug `lab` (Laboratory tests) and the facility type `laboratory` are separate fields. |
| Specialists and practitioners | `practitioners` rows with registration evidence | The Specialists page shows "Practitioner profiles are not listed yet". |
| Appointment requests | `facilities.accepts_appointment_requests` and active staff accounts linked to the facility | Listings show "Contact facility" (phone, email or website) instead of "Request appointment". No facility publishes bookable time slots, so the application never offers instant booking. |
| Google ratings | `facility_external_profiles` snapshots from Google Places | No rating is shown. Ratings and written reviews are separate; a rating count is not a count of written reviews. |
| Public reviews (Facebook, TikTok, Instagram) | `external_posts` and `external_comments` with an approved moderation decision and attribution scope | Each source tab shows an accurate empty state. Organization-wide posts are never counted as branch feedback. |
| Community programmes, costs and coverage | `community_programs` rows maintained by administrators | Programme pages show an empty state. Costs are only displayed where a programme lists them. |
| Inpatient / outpatient setting | No field yet | Not offered as a filter until verified data and a schema change are approved. |

The directory imported through the bot (Google Places) supplies names, types, locations, coordinates, contacts,
opening hours and rating snapshots. It does not supply service, insurer, laboratory-menu or practitioner
relationships. Those must come from facilities, regulators or other permitted authoritative sources.

## How to build a verified directory

1. **Facility identity.** Establish permission to use and maintain a source. The
   [Kenya Master Health Facility Registry](https://kmhfr.health.go.ke/public/about) provides code-based facility
   identities, service information and a documented API. Match on facility codes and verified location; name and
   town alone are insufficient for ambiguous results.
2. **Services and insurers.** Cross-check each service and insurer link with the facility, and record the source
   and the date it was checked. Import insurer coverage only from attributable official sources, and keep missing
   coverage distinct from rejection. Re-imports that omit `services` or `insurers` keep the existing links (see
   [DATA_IMPORT_CONTRACT.md](DATA_IMPORT_CONTRACT.md)).
3. **Practitioners.** Verify each practitioner and specialty with the relevant regulator. For doctors and dentists
   use the [KMPDC register](https://registers.kmpdc.go.ke/) and the
   [KMPDC specialist recognition list](https://kmpdc.go.ke/specialties-specialist-recognition/). Confirm facility
   affiliation separately through official rosters or facility attestation. A registration entry does not confirm
   current employment, appointment access or fees.
4. **Staging and review.** Stage candidates with stable authority IDs, source URLs, evidence dates and review status.
   Quarantine unmatched or conflicting names. Never publish from a fuzzy match.
5. **Dry run.** Run imports with deduplication and quality reports first. Test matched and ambiguous records, service
   combinations, and that list, map and reference totals agree.

A suitable first pilot is antenatal care in Nairobi: it exercises the service filter, county aliases and the
List / Grid / Map parity checks with a small, reviewable set of facilities.

## Public feedback attribution rules

* A Facebook page linked from several listings (for example a hospital group's shared page) is an
  **organization** source. Its posts appear under "organization-wide activity" and are never counted as feedback
  for an individual branch.
* Use **facility** attribution only when the post or page evidence identifies that location.
* Website-platform pages (for example a `/wix` link) and generic Facebook path categories (`people`, `brand`) are not
  facility pages. Withhold them and correct the stored profile link.
* Every Facebook post requires an administrator decision at `/dashboard/admin/facebook-feedback` before it is shown.
  Publishing requires a note, explicit comment selection and an attribution scope.
* Commenters are members of the public. ReproCare does not verify that they were patients, and public feedback is
  presented separately from moderated ReproCare patient reviews.

## Regression checks for data-dependent features

* List and map results agree for county spellings ("Nairobi", "Nairobi City", "Nairobi County",
  "Wilaya ya Nairobi"), Google rating thresholds and published review counts.
* Facility-specific public feedback excludes organization-scope posts and follows comment visibility rules.
* A homepage search for a service with no recorded links keeps the other filters and offers results without the
  service filter.
* The staff facility selector lists facilities on focus, filters while typing, and supports Arrow keys, Enter
  and Escape. Choosing a role only fills the enquiry; it never grants staff access.
