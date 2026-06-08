#!/usr/bin/env python3
"""
Second-pass reviewer for recovered email candidates.

This script is intentionally conservative. It focuses on candidates that were
not auto-filled in the first pass because the email domain did not match the
website domain, but still have strong evidence from the company's own site.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from recover_emails import DEFAULT_INPUT, DEFAULT_OUTPUT_DIR, is_valid_business_email


COMMON_MAILBOX_DOMAINS = {
    "aol.com",
    "bellsouth.net",
    "gmail.com",
    "hotmail.com",
    "mindspring.com",
    "swbell.net",
    "yahoo.com",
}

KNOWN_FALSE_POSITIVE_DOMAINS = {
    "eyebytes.com",
    "indiantypefoundry.com",
    "lab6.com",
    "latofonts.com",
    "leadlane.io",
    "markmywordsmedia.com",
    "micahrich.com",
    "opencart.com",
    "pixelspread.com",
    "rfuenzalida.com",
    "rhobositsolutions.com",
    "typemade.mx",
}

GENERIC_WORDS = {
    "and",
    "company",
    "co",
    "custom",
    "design",
    "engraving",
    "graphics",
    "inc",
    "laser",
    "lasering",
    "llc",
    "sign",
    "signs",
    "shop",
    "the",
}


def email_domain(email: str) -> str:
    return email.lower().rsplit("@", 1)[1]


def compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def company_tokens(company: str) -> set[str]:
    tokens = {
        token
        for token in re.split(r"[^a-z0-9]+", company.lower())
        if len(token) >= 4 and token not in GENERIC_WORDS
    }
    return tokens


def source_path(url: str) -> str:
    return urlparse(url).path.lower()


def choose_status(candidate: dict[str, str], row: dict[str, object]) -> tuple[str, str]:
    email = candidate["email"].lower()
    domain = email_domain(email)
    local = email.rsplit("@", 1)[0]
    score = int(candidate["score"])
    source_kind = candidate["source_kind"]
    reasons = candidate["reasons"].lower()
    path = source_path(candidate["source_url"])
    tokens = company_tokens(str(row.get("company") or candidate["company"]))
    compact_company = compact(str(row.get("company") or candidate["company"]))
    compact_email = compact(local + domain.rsplit(".", 1)[0])

    valid, reason = is_valid_business_email(email)
    if not valid:
        return "reject", reason
    if domain in KNOWN_FALSE_POSITIVE_DOMAINS:
        return "reject", "known template/developer/service domain"

    contact_evidence = "found on contact/about-style page" in reasons or any(
        hint in path for hint in ("/contact", "/about", "/hours", "/staff", "/team")
    )
    token_match = any(token in compact_email for token in tokens)
    compact_match = bool(compact_company) and (
        compact_company[:10] in compact_email or compact_email[:10] in compact_company
    )

    if source_kind in {"mailto", "cloudflare"}:
        if score >= 75 and contact_evidence:
            return "accept", "direct mailto/cloudflare on contact-style page"
        if domain in COMMON_MAILBOX_DOMAINS and (score >= 70 or token_match):
            return "accept", "direct mailto common small-business mailbox"
        if score >= 65 and (token_match or compact_match):
            return "accept", "direct mailto with company-name match"
        return "manual", "direct email, but weak company/contact evidence"

    if source_kind == "visible":
        if score >= 65 and domain in COMMON_MAILBOX_DOMAINS and contact_evidence and token_match:
            return "accept", "visible small-business mailbox with company-name match"
        if score >= 70 and contact_evidence and (token_match or compact_match):
            return "accept", "visible contact-page email with company-name match"
        return "manual", "visible text needs human source check"

    return "manual", "unhandled source kind"


def load_rows(path: Path) -> list[dict[str, object]]:
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise TypeError(f"Expected list JSON in {path}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    rows = load_rows(args.input)
    rows_by_id = {str(row["id"]): row for row in rows}
    invalid_ids = {
        str(row["id"])
        for row in rows
        if not is_valid_business_email(str(row.get("email") or ""))[0]
    }
    already_applied_ids = {
        str(row["id"])
        for row in rows
        if "Second-pass email recovery:" in str(row.get("notes") or "")
    }
    review_ids = invalid_ids | already_applied_ids

    candidates_path = args.output_dir / "recovered_emails_candidates.csv"
    reviewed_path = args.output_dir / "second_pass_review.csv"
    accepted_path = args.output_dir / "second_pass_accepted.csv"
    summary_path = args.output_dir / "second_pass_summary.json"

    grouped: dict[str, list[dict[str, str]]] = {}
    with candidates_path.open(newline="") as handle:
        for candidate in csv.DictReader(handle):
            if candidate["id"] not in review_ids:
                continue
            if not is_valid_business_email(candidate["email"])[0]:
                continue
            grouped.setdefault(candidate["id"], []).append(candidate)

    reviewed: list[dict[str, str]] = []
    accepted_by_id: dict[str, dict[str, str]] = {}
    for row_id, candidates in grouped.items():
        row = rows_by_id[row_id]
        classified = []
        for candidate in candidates:
            if (
                row_id in already_applied_ids
                and str(row.get("email") or "").lower() == candidate["email"].lower()
            ):
                status, review_reason = "accept", "already applied second-pass candidate"
            else:
                status, review_reason = choose_status(candidate, row)
            candidate = dict(candidate)
            candidate["review_status"] = status
            candidate["review_reason"] = review_reason
            classified.append(candidate)
            reviewed.append(candidate)

        accepted = [c for c in classified if c["review_status"] == "accept"]
        if accepted:
            accepted.sort(
                key=lambda c: (
                    int(c["score"]),
                    c["source_kind"] in {"mailto", "cloudflare"},
                    "found on contact/about-style page" in c["reasons"].lower(),
                ),
                reverse=True,
            )
            accepted_by_id[row_id] = accepted[0]

    fieldnames = [
        "id",
        "company",
        "state",
        "website",
        "email",
        "score",
        "source_kind",
        "source_url",
        "reasons",
        "review_status",
        "review_reason",
    ]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for path, records in (
        (reviewed_path, reviewed),
        (accepted_path, list(accepted_by_id.values())),
    ):
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

    if args.apply:
        for row_id, candidate in accepted_by_id.items():
            row = rows_by_id[row_id]
            row["email"] = candidate["email"]
            note = f"Second-pass email recovery: {candidate['review_reason']}."
            existing = str(row.get("notes") or "").strip()
            if "Second-pass email recovery:" not in existing:
                row["notes"] = f"{existing} | {note}" if existing else note
        args.input.write_text(json.dumps(rows, indent=2) + "\n")

    summary = {
        "currently_invalid_rows": len(invalid_ids),
        "already_applied_rows": len(already_applied_ids),
        "rows_with_review_candidates": len(grouped),
        "candidate_records_reviewed": len(reviewed),
        "accepted_rows": len(accepted_by_id),
        "accepted_records": sum(
            1 for candidate in reviewed if candidate["review_status"] == "accept"
        ),
        "manual_records": sum(
            1 for candidate in reviewed if candidate["review_status"] == "manual"
        ),
        "rejected_records": sum(
            1 for candidate in reviewed if candidate["review_status"] == "reject"
        ),
        "applied": args.apply,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
