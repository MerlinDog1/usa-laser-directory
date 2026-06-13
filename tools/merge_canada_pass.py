#!/usr/bin/env python3
"""Merge a curated Canada pass into the laser engraving directory.

Rows are manually seeded from Canadian city/province searches, then each row
must pass the existing direct-site service-evidence verifier before merge.
"""

from __future__ import annotations

import collections
import concurrent.futures
import datetime as dt
import json
from pathlib import Path

from verify_and_merge_deeper_pass import DATA_PATH, MAX_WORKERS, META_PATH, clean_email, host_of, norm_key, verify

OUT_DIR = Path(__file__).resolve().parents[1] / "outputs" / "canada-pass-2026-06-13"

CURATED = [
    ("Artdeco Inc.", "Ontario", "Engraver", "https://artdecoinc.ca/", None, None, "Toronto laser engraving and personalization service."),
    ("KMX Laser", "Ontario", "Engraver", "https://www.kmxlaser.ca/laser-engraving-toronto", None, None, "Toronto laser engraving and cutting service."),
    ("Archer Laser", "Ontario", "Engraver", "https://www.archerlaser.ca/", None, None, "Toronto GTA laser engraving and etching service."),
    ("AKLASER", "Ontario", "Engraver", "https://aklaser.ca/", None, None, "Toronto laser engraving and cutting service."),
    ("iCanLaser", "Ontario", "Engraver", "https://www.icanlaser.com/", None, None, "Toronto laser engraving service."),
    ("Store of Signs", "Ontario", "Sign Company", "https://storeofsigns.com/", None, None, "Ottawa custom signs provider with laser engraving services."),
    ("Woodgrain Ottawa", "Ontario", "Engraver", "https://www.woodgrainottawa.ca/", None, None, "Ottawa laser cutting and engraving studio."),
    ("Zenith CNC Laser", "Ontario", "Engraver", "https://zenithcnclaser.com/", None, None, "Ontario CNC laser cutting and engraving service."),
    ("Gravure Laser", "Ontario", "Engraver", "https://www.gravurelaser.ca/", None, None, "Ontario laser engraving service."),
    ("Canadian Custom Engravers", "Ontario", "Engraver", "https://cce.ca/", None, None, "Canadian custom engraving service provider."),
    ("Trophy Centre", "British Columbia", "Engraver", "https://www.trophycentre.ca/", None, None, "Vancouver trophy and laser engraving provider."),
    ("Laser Engrave Pro", "British Columbia", "Engraver", "https://laserengravepro.ca/", None, None, "Vancouver-area laser engraving business."),
    ("The Engraving Studio", "British Columbia", "Engraver", "https://www.engravingstudio.ca/", None, None, "Vancouver engraving and laser service studio."),
    ("VS Printing Lab", "British Columbia", "Engraver", "https://vsprintinglab.ca/", None, None, "Vancouver printing and laser solutions studio."),
    ("FabLab Vancouver", "British Columbia", "Engraver", "https://www.fablabvan.ca/service", None, None, "Vancouver digital fabrication service with laser cutting and engraving."),
    ("Solocraft", "Alberta", "Engraver", "https://www.solocraft.ca/", None, None, "Calgary laser engraving service."),
    ("Custom Crafted Engraving", "Alberta", "Engraver", "https://customcrafted.ca/", None, None, "Calgary custom product and engraving business."),
    ("Grafix Media", "Alberta", "Engraver", "https://grafix-media.ca/laser-engraving-services/", None, None, "Alberta industrial, commercial and custom laser engraving service."),
    ("DNA Master Works", "Alberta", "Engraver", "https://dnamasterworks.ca/", None, None, "Calgary laser engraving business."),
    ("Lasercraft Calgary", "Alberta", "Engraver", "https://lasercraftcalgary.com/", None, None, "Calgary precision engraving, marking and cutting provider."),
    ("Dimages Engraving", "Alberta", "Engraver", "https://www.dimages.ca/", None, None, "Calgary engraving provider."),
    ("Artful Laser Co.", "Alberta", "Engraver", "https://www.artfullaserco.ca/", None, None, "Edmonton laser engraving service."),
    ("BEAMZ", "Alberta", "Engraver", "https://www.beamz.ca/", None, None, "Edmonton laser engraving business."),
    ("Metalmark", "Alberta", "Engraver", "https://metalmark.ca/", None, None, "Edmonton custom engraving and marking provider."),
    ("Made With Light", "Alberta", "Engraver", "https://madewithlight.ca/aboutlaser-engraving", None, None, "Edmonton laser engraving, cutting and design service."),
    ("LaserArt MTL", "Quebec", "Engraver", "https://www.laserartmtl.ca/", None, None, "Montreal cutting, engraving and printing service."),
    ("Elite Graphic Design", "Quebec", "Engraver", "https://elitegraphicdesign.com/", None, None, "Montreal custom engraving and printing provider."),
    ("Janico Inc.", "Quebec", "Engraver", "https://www.janicoinc.ca/en-ca/engraving.php", None, None, "Montreal laser, mechanical engraving and sandblasting provider."),
    ("Robocut Studio", "Quebec", "Engraver", "https://robocutstudio.com/", None, None, "Montreal digital fabrication studio with laser cutting and engraving."),
    ("Winnipeg Laser Engraving", "Manitoba", "Engraver", "https://www.winnipeglaserengraving.com/", None, None, "Winnipeg laser engraving and etching service."),
    ("Etched Out Winnipeg", "Manitoba", "Engraver", "https://www.etchedoutlaserengraving.ca/laser-engraving-winnipeg", None, None, "Winnipeg laser engraving service."),
    ("B&B Trophy Shack / CM Engrave", "Manitoba", "Engraver", "https://www.cmengrave.ca/", None, None, "Winnipeg signage, awards and engraving provider."),
    ("Kira Design", "Manitoba", "Engraver", "https://www.kiradesign.ca/", None, None, "Winnipeg photography and laser engraving business."),
    ("EurekaTec", "Nova Scotia", "Sign Company", "https://www.eurekatec.ca/", None, None, "Halifax 3D printing, laser engraving and custom signage provider."),
    ("Laser24", "Nova Scotia", "Engraver", "https://www.laser24.ca/", None, None, "Nova Scotia laser cutting and engraving service."),
    ("Laser Impressions Sign Studio", "Saskatchewan", "Sign Company", "https://www.laserimpressions.ca/", None, None, "Saskatoon custom sign studio with laser services."),
    ("Pro-Touch Engraving Ltd.", "Saskatchewan", "Engraver", "https://www.protouch.ca/", None, None, "Saskatoon engraving and signage provider."),
    ("CD Engravings", "Saskatchewan", "Engraver", "https://c-d-custom-engraving.ca/", None, None, "Weyburn Saskatchewan custom engraving business."),
    ("Laser's Edge Engraving", "Saskatchewan", "Engraver", "https://www.lasersedge.ca/", None, None, "Emerald Park Saskatchewan laser engraving provider."),
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = json.loads(DATA_PATH.read_text())
    existing_company = {norm_key(row.get("company")) for row in existing}
    existing_host = {host_of(row.get("website") or "") for row in existing if row.get("website")}
    existing_email = {str(row.get("email")).lower() for row in existing if row.get("email")}

    accepted = []
    rejected = []
    candidates = []
    seen_host = set()
    for company, province, category, website, email, phone, notes in CURATED:
        candidate = {
            "sourceFile": "canada-pass-2026-06-13",
            "company": company,
            "state": province,
            "county": province,
            "category": category,
            "website": website,
            "email": clean_email(email),
            "phone": phone,
            "address": province + ", Canada",
            "quality": 8,
            "mainBrand": None,
            "linkedin": None,
            "instagram": None,
            "facebook": None,
            "notes": notes,
        }
        key = norm_key(company)
        host = host_of(website)
        candidate_email = (candidate.get("email") or "").lower()
        if key in existing_company or host in existing_host or host in seen_host or (candidate_email and candidate_email in existing_email):
            rejected.append({**candidate, "rejectReason": "duplicate before verification"})
            continue
        seen_host.add(host)
        candidates.append(candidate)

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(verify, candidate) for candidate in candidates]
        for future in concurrent.futures.as_completed(futures):
            ok, verified = future.result()
            if ok:
                accepted.append(verified)
            else:
                rejected.append(verified)

    accepted.sort(key=lambda r: (r["state"], r["category"], r["company"]))
    start_id = max(int(row.get("id") or 0) for row in existing) + 1
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
                "address": row.get("address") or f"{row['state']}, Canada",
                "quality": row.get("quality") or 8,
                "sellsPlaques": bool(row.get("sellsPlaques")),
                "mainBrand": row.get("mainBrand"),
                "notes": row.get("notes"),
                "publicationStatus": "public",
                "contactStatus": row.get("contactStatus"),
            }
        )

    merged = existing + additions
    metadata = {
        "count": len(merged),
        "categories": sorted({row.get("category") for row in merged if row.get("category")}),
        "states": sorted({row.get("state") for row in merged if row.get("state")}),
    }
    DATA_PATH.write_text(json.dumps(merged, indent=2) + "\n")
    META_PATH.write_text(json.dumps(metadata, indent=2) + "\n")

    by_province = collections.Counter(row["state"] for row in additions)
    by_category = collections.Counter(row["category"] for row in additions)
    (OUT_DIR / "accepted.json").write_text(json.dumps(additions, indent=2) + "\n")
    (OUT_DIR / "rejected.json").write_text(json.dumps(rejected, indent=2) + "\n")
    (OUT_DIR / "report.md").write_text(
        "\n".join(
            [
                "# Canada Laser Directory Pass - 2026-06-13",
                "",
                f"- Curated seed rows: {len(CURATED)}",
                f"- Accepted rows: {len(additions)}",
                f"- Rejected rows: {len(rejected)}",
                f"- New live row count: {len(merged)}",
                f"- Accepted by category: {dict(sorted(by_category.items()))}",
                f"- Accepted by province: {dict(sorted(by_province.items()))}",
                "",
                "Quality gates:",
                "- Rows were manually seeded from Canadian city/province searches.",
                "- Each row had to pass a direct website fetch and service-evidence verification.",
                "- Existing company/site/email duplicates were rejected.",
                "",
                f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
            ]
        )
        + "\n"
    )
    print(f"accepted={len(additions)} rejected={len(rejected)} total={len(merged)}")
    print(f"accepted_path={OUT_DIR / 'accepted.json'}")
    print(f"report_path={OUT_DIR / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
