#!/usr/bin/env python3
"""
Apply manually verified third-pass email decisions.

The decisions here come from checking the source page around each candidate in
`second_pass_review.csv`. Only candidates with clear contact-page or structured
local-business evidence are applied.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from recover_emails import DEFAULT_INPUT, DEFAULT_OUTPUT_DIR, is_valid_business_email


DECISIONS = {
    "148": ("accept", "laserengravingcle@gmail.com", "visible contact block: Ordering Bulk"),
    "186": ("skip", "impallari@gmail.com", "font license author; row already has better email"),
    "187": ("reject", "impallari@gmail.com", "font license author"),
    "244": ("skip", "agustinamingote@gmail.com", "font license author; row already has better email"),
    "264": ("reject", "impallari@gmail.com", "font license author"),
    "280": ("accept", "sales@signs.boston", "mailto contact email on company page"),
    "367": ("reject", "wweeiihhuuaanngg@gmail.com", "font license author"),
    "395": ("accept", "corbin@visibilitysign.com", "LocalBusiness contactPoint email"),
    "407": ("accept", "sales@highvalue.us", "contact block mailto email"),
    "461": ("skip", "support@wichitagiftco.com", "Shopify theme/beacon email; row already has better email"),
    "504": ("accept", "customdencda@gmail.com", "contact page meta description email"),
    "56": ("skip", "sn43@signsnowsac.com", "structured location email; row already has better email"),
    "78": ("skip", "tony@majorleaguesigns.com", "candidate not present on refetched contact page; row already has better email"),
    "81": ("accept", "sales@comengravingshop.com", "visible email in contact page contact section"),
    "85": ("accept", "information@amazingsigns.net", "LocalBusiness email in contact page schema"),
    "99": ("accept", "sblaserengravingllc@gmail.com", "visible email in contact page contact section"),
}


def main() -> int:
    rows = json.loads(DEFAULT_INPUT.read_text())
    rows_by_id = {str(row["id"]): row for row in rows}

    manual_rows = []
    review_path = DEFAULT_OUTPUT_DIR / "second_pass_review.csv"
    with review_path.open(newline="") as handle:
        for candidate in csv.DictReader(handle):
            if candidate["review_status"] != "manual":
                continue
            row_id = candidate["id"]
            decision = DECISIONS.get(row_id)
            if not decision:
                continue
            status, expected_email, reason = decision
            if candidate["email"].lower() != expected_email.lower():
                continue

            row = rows_by_id[row_id]
            current_valid = is_valid_business_email(str(row.get("email") or ""))[0]
            applied = False
            if status == "accept" and not current_valid:
                row["email"] = expected_email
                note = f"Third-pass verified email: {expected_email} ({reason}) from {candidate['source_url']}."
                existing = str(row.get("notes") or "").strip()
                if "Third-pass verified email:" not in existing:
                    row["notes"] = f"{existing} | {note}" if existing else note
                applied = True

            manual_rows.append(
                {
                    "id": row_id,
                    "company": candidate["company"],
                    "state": candidate["state"],
                    "website": candidate["website"],
                    "candidate_email": candidate["email"],
                    "source_url": candidate["source_url"],
                    "decision": status,
                    "reason": reason,
                    "applied": "yes" if applied else "no",
                    "current_email": row.get("email") or "",
                }
            )

    DEFAULT_INPUT.write_text(json.dumps(rows, indent=2) + "\n")

    output_path = DEFAULT_OUTPUT_DIR / "third_pass_manual_verification.csv"
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "id",
                "company",
                "state",
                "website",
                "candidate_email",
                "source_url",
                "decision",
                "reason",
                "applied",
                "current_email",
            ],
        )
        writer.writeheader()
        writer.writerows(manual_rows)

    summary = {
        "manual_candidates_decided": len(manual_rows),
        "accepted_candidates": sum(1 for row in manual_rows if row["decision"] == "accept"),
        "applied_rows": sum(1 for row in manual_rows if row["applied"] == "yes"),
        "rejected_candidates": sum(1 for row in manual_rows if row["decision"] == "reject"),
        "skipped_candidates": sum(1 for row in manual_rows if row["decision"] == "skip"),
    }
    (DEFAULT_OUTPUT_DIR / "third_pass_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
