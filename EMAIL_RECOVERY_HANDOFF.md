# Email Recovery Pipeline Handoff

This repo has many directory entries with missing or invalid emails. The recovery pass should be Python-first and reviewable, not an AI guessing pass.

## What Was Added

- `tools/recover_emails.py`: a non-destructive crawler/extractor for public business contact emails.
- `tools/review_email_candidates.py`: a conservative second-pass classifier for off-domain/common-mailbox candidates.
- Output folder used by the script: `outputs/email-recovery/`.

The script reads `data/directory-data.json` and writes review files. It does **not** overwrite the source dataset.

## Why This Is Needed

The existing data includes invalid recovered values such as:

- `52033662@n05.jpg`
- `?subject=`
- `605a7baede844d278b89dc95ae0a9123@sentry-next.wixpress.com`

Those are artifacts from page source/image/platform scraping, not real company contact emails.

## Safe Dry Run

```bash
python3 tools/recover_emails.py --limit 10 --max-pages 4 --delay 0.5
```

Useful targeted runs:

```bash
python3 tools/recover_emails.py --state California --limit 25
python3 tools/recover_emails.py --ids 12,20,24 --max-pages 5
```

When ready for a full bounded pass:

```bash
python3 tools/recover_emails.py --limit 0 --max-pages 4 --delay 0.75
```

Note: `--limit 0` means no slicing limit. Use it carefully because it will crawl every row with a missing or invalid email and a website.

## Outputs

The script writes:

- `outputs/email-recovery/recovered_emails_candidates.csv`
  - All valid-looking candidates with score, source page, source type, and reasons.
- `outputs/email-recovery/invalid_existing_emails.csv`
  - Existing email values that should be considered missing/invalid.
- `outputs/email-recovery/directory-data.proposed.json`
  - A proposed filled dataset using only strict auto-fill candidates.
- `outputs/email-recovery/auto_fill_emails.csv`
  - The exact candidates applied to the proposed JSON.
- `outputs/email-recovery/summary.json`
  - Counts for rows scanned, candidates found, and proposed fills.
- `outputs/email-recovery/crawl_log.json`
  - Fetch errors and skipped pages.

## Scoring Rules

Candidates score higher when:

- Found in a `mailto:` link.
- Found on a contact/about-style page.
- Email domain matches the company website domain.
- Local part is useful for business contact, such as `info`, `sales`, `contact`, `hello`, or `support`.

Automatic fills are stricter than candidate extraction. A candidate is only copied into `directory-data.proposed.json` when it meets the score threshold **and** the email domain matches or closely resembles the company website domain. Valid-looking Gmail/Yahoo/outside-domain emails remain in the candidate CSV for manual review.

Candidates are rejected when they look like:

- Image/assets or page fragments.
- Query strings.
- Wix/Sentry/Shopify/Squarespace/platform internals.
- Example/test domains.
- No-reply/legal/privacy/system addresses.

## Review Workflow

1. Run a small sample.
2. Open `recovered_emails_candidates.csv`.
3. Spot-check source URLs for high-score candidates.
4. If the output looks clean, run a larger batch.
5. Diff `directory-data.proposed.json` against `data/directory-data.json`.
6. Only then copy approved emails into the real dataset or write a separate merge script.

AI can help after this stage by reviewing ambiguous candidates, but it should not invent email addresses.

## Second-Pass Review

The first pass intentionally skipped candidates when the email domain did not match the website domain, even if the email came from a direct `mailto:` link. The second pass reviews those candidates with stricter source rules:

- Accept direct `mailto:` or Cloudflare-decoded emails on contact/about-style pages.
- Accept common small-business mailboxes when they are direct links from the business site.
- Accept visible text only when the email strongly matches the company name.
- Reject known template, font, developer, donation, and platform-service domains.
- Leave weak visible-text candidates in `second_pass_review.csv` for manual checking.

Dry run:

```bash
python3 tools/review_email_candidates.py
```

Apply accepted candidates:

```bash
python3 tools/review_email_candidates.py --apply
```

Second-pass outputs:

- `outputs/email-recovery/second_pass_review.csv`
  - All reviewed candidates with `accept`, `manual`, or `reject` status.
- `outputs/email-recovery/second_pass_accepted.csv`
  - The one accepted candidate per row that was eligible for merge.
- `outputs/email-recovery/second_pass_summary.json`
  - Counts for reviewed, accepted, manual, and rejected records.

## Full Run Result - 2026-06-07

Command used:

```bash
python3 tools/recover_emails.py --limit 0 --max-pages 4 --delay 0.5 --timeout 12
```

After review, the proposed output was tightened so automatic fills require a matching or closely resembling website domain. The proposed JSON was then copied into `data/directory-data.json`.

Result:

- Total rows: `550`
- Valid-looking emails after merge: `352`
- Still missing/invalid: `198`
- Candidate emails retained for review: `374`
- Rows with at least one candidate: `260`
- Strict auto-fills applied: `188`
- Known invalid existing emails cleared without replacement: `2`

Known cleared examples:

- Dunham Metal Processing: removed Wix/Sentry internal email.
- Advanced Laser Engraving of Louisiana: removed `info@mysite.com` placeholder.

Remaining work:

- Review `recovered_emails_candidates.csv` for valid Gmail/Yahoo/outside-domain emails that were intentionally not auto-filled.
- Manually investigate sites blocked by `403`, dead domains, expired SSL, or sites that only expose contact forms.

## Second-Pass Result - 2026-06-08

Command used:

```bash
python3 tools/review_email_candidates.py --apply
```

Result:

- Strict invalid/missing rows before second pass: `198`
- Candidate records reviewed: `94`
- Rows with review candidates: `72`
- Additional rows filled: `53`
- Valid business emails after second pass: `405`
- Still missing/invalid after second pass: `145`

The remaining `manual` candidates are mostly visible page-text emails that require source checking, and the rejected candidates include known template/developer/service domains such as font authors, web developers, donation addresses, and lead-generation tooling.

## Third-Pass Result - 2026-06-08

Manual visible-text verification:

```bash
python3 tools/apply_third_pass_manual.py
```

Deeper same-site crawl:

```bash
python3 tools/recover_emails.py --limit 0 --max-pages 8 --delay 0.25 --timeout 12 --output-dir outputs/email-recovery/third-pass-deep
python3 tools/review_email_candidates.py --output-dir outputs/email-recovery/third-pass-deep
```

Results applied:

- Manual verified candidates applied: `8`
- Deeper same-site crawl candidates applied: `4`
- Valid business emails after third pass: `417`
- Still missing/invalid after third pass: `133`

Third-pass outputs:

- `outputs/email-recovery/third_pass_manual_verification.csv`
- `outputs/email-recovery/third_pass_summary.json`
- `outputs/email-recovery/third-pass-deep/`
- `outputs/email-recovery/remaining_missing_triage.csv`
- `outputs/email-recovery/remaining_missing_triage_summary.json`

Remaining triage:

- No email found on accessible site: `88`
- Blocked by `403`: `16`
- Only junk/template/developer candidates: `8`
- `404`/not found: `6`
- Dead DNS: `4`
- SSL problem: `4`
- Connection timeout/disconnect: `3`
- Manual source check remaining: `4`

At this point, the crawler has probably exhausted safe same-site recovery. The next pass should use external lookup sources such as business profiles, search snippets, Facebook/LinkedIn pages, Google/Maps listings, state registrations, and archived pages. Companies that only expose contact forms should be marked separately rather than assigned guessed emails.
