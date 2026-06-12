#!/usr/bin/env python3
"""Verify and merge hand-seeded web additions for the deeper USA pass."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse
from verify_and_merge_deeper_pass import META_PATH, DATA_PATH, OUT_DIR, clean_email, host_of, verify

MANUAL = [
    {
        "sourceFile": "live-web-search-2026-06-12",
        "company": "DS Laser Engraving",
        "state": "California",
        "county": "California",
        "category": "Engraver",
        "website": "https://www.dslaserengraving.com/",
        "email": None,
        "phone": "530.710.1843",
        "address": "210 High St. Suite D, Mount Shasta, CA 96067",
        "quality": 8,
        "mainBrand": None,
        "linkedin": None,
        "instagram": None,
        "facebook": None,
        "notes": "Mount Shasta laser engraving shop offering engraved gifts, signs and wood stickers.",
    },
    {
        "sourceFile": "live-web-search-2026-06-12",
        "company": "Laser Light Engravers",
        "state": "California",
        "county": "California",
        "category": "Engraver",
        "website": "https://www.laserlightusa.com/",
        "email": None,
        "phone": "661-834-0100",
        "address": "Bakersfield, CA",
        "quality": 8,
        "mainBrand": None,
        "linkedin": None,
        "instagram": None,
        "facebook": None,
        "notes": "Bakersfield industrial laser engraving and signage provider covering metal tags, nameplates, placards and awards.",
    },
    {
        "sourceFile": "live-web-search-2026-06-12",
        "company": "HP Design",
        "state": "Texas",
        "county": "Texas",
        "category": "Engraver",
        "website": "https://www.hpdesign.shop/",
        "email": None,
        "phone": None,
        "address": "McKinney, TX",
        "quality": 8,
        "mainBrand": None,
        "linkedin": None,
        "instagram": None,
        "facebook": None,
        "notes": "McKinney custom laser engraving studio serving awards, corporate gifts, print and embroidery.",
    },
    {
        "sourceFile": "live-web-search-2026-06-12",
        "company": "MnM Laser Engraving",
        "state": "Texas",
        "county": "Texas",
        "category": "Engraver",
        "website": "https://www.mnm-laserengraving.com/",
        "email": "info@mnm-laserengraving.com",
        "phone": None,
        "address": "San Antonio, TX",
        "quality": 8,
        "mainBrand": None,
        "linkedin": None,
        "instagram": None,
        "facebook": None,
        "notes": "San Antonio custom laser engraving and glass etching business.",
    },
    {
        "sourceFile": "live-web-search-2026-06-12",
        "company": "Claude L. Holsapple & Son",
        "state": "Texas",
        "county": "Texas",
        "category": "Engraver",
        "website": "https://www.holsapples.com/",
        "email": "engrave@holsapples.com",
        "phone": "(214) 357-8449",
        "address": "797 N Grove Rd #107, Richardson, TX 75081",
        "quality": 8,
        "mainBrand": None,
        "linkedin": None,
        "instagram": None,
        "facebook": None,
        "notes": "Richardson engraving business with direct phone, email and storefront address.",
    },
    {
        "sourceFile": "live-web-search-2026-06-12",
        "company": "Engravexx",
        "state": "Texas",
        "county": "Texas",
        "category": "Engraver",
        "website": "https://engravexx.com/",
        "email": "info@engravexx.com",
        "phone": "(312) 927-7682",
        "address": "Houston, TX",
        "quality": 7,
        "mainBrand": None,
        "linkedin": None,
        "instagram": None,
        "facebook": None,
        "notes": "USA laser engraving company listing a Houston address and direct contact details.",
    },
]


def norm_key(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def main() -> int:
    rows = json.loads(DATA_PATH.read_text())
    existing_company = {norm_key(row.get("company")) for row in rows}
    existing_site = {host_of(row.get("website") or "") for row in rows if row.get("website")}
    existing_email = {str(row.get("email")).lower() for row in rows if row.get("email")}

    accepted = []
    rejected = []
    for candidate in MANUAL:
        host = host_of(candidate["website"])
        email = (clean_email(candidate.get("email")) or "").lower()
        candidate["email"] = clean_email(candidate.get("email"))
        if norm_key(candidate["company"]) in existing_company:
            rejected.append({**candidate, "rejectReason": "duplicate company"})
            continue
        if host in existing_site:
            rejected.append({**candidate, "rejectReason": "duplicate website host"})
            continue
        if email and email in existing_email:
            rejected.append({**candidate, "rejectReason": "duplicate email"})
            continue
        ok, verified = verify(candidate)
        if not ok:
            rejected.append(verified)
            continue
        accepted.append(verified)

    start_id = max(int(row.get("id") or 0) for row in rows) + 1
    additions = []
    for idx, row in enumerate(accepted, start=start_id):
        additions.append(
            {
                "id": idx,
                "county": row["state"],
                "state": row["state"],
                "category": row["category"],
                "company": row["company"],
                "website": row["website"],
                "email": row.get("email"),
                "linkedin": row.get("linkedin"),
                "instagram": row.get("instagram"),
                "facebook": row.get("facebook"),
                "phone": row.get("phone") or None,
                "address": row.get("address") or row["state"],
                "quality": row["quality"],
                "sellsPlaques": bool(row.get("sellsPlaques")),
                "mainBrand": row.get("mainBrand"),
                "notes": row.get("notes") or None,
                "publicationStatus": "public",
                "contactStatus": row.get("contactStatus"),
            }
        )

    merged = rows + additions
    metadata = {
        "count": len(merged),
        "categories": sorted({row.get("category") for row in merged if row.get("category")}),
        "states": sorted({row.get("state") for row in merged if row.get("state")}),
    }

    DATA_PATH.write_text(json.dumps(merged, indent=2) + "\n")
    META_PATH.write_text(json.dumps(metadata, indent=2) + "\n")
    out_path = OUT_DIR / "manual-web-accepted.json"
    reject_path = OUT_DIR / "manual-web-rejected.json"
    out_path.write_text(json.dumps(additions, indent=2) + "\n")
    reject_path.write_text(json.dumps(rejected, indent=2) + "\n")
    print(f"manual_accepted={len(additions)} manual_rejected={len(rejected)} total={len(merged)}")
    print(f"manual_accepted_path={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
