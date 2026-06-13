#!/usr/bin/env python3
"""Merge a province/state scoped Canada + Australia pass.

The seed list comes from region-specific searches. The merge still requires the
existing live direct-site verifier, so social/directory/search-noise results do
not enter the public dataset.
"""

from __future__ import annotations

import collections
import concurrent.futures
import datetime as dt
import json
from pathlib import Path

from verify_and_merge_deeper_pass import DATA_PATH, MAX_WORKERS, META_PATH, clean_email, host_of, norm_key, verify

OUT_DIR = Path(__file__).resolve().parents[1] / "outputs" / "international-region-pass-2026-06-13"

CANADA_REGIONS = [
    "Alberta",
    "British Columbia",
    "Manitoba",
    "New Brunswick",
    "Newfoundland and Labrador",
    "Northwest Territories",
    "Nova Scotia",
    "Nunavut",
    "Ontario",
    "Prince Edward Island",
    "Quebec",
    "Saskatchewan",
    "Yukon",
]

AUSTRALIA_REGIONS = [
    "Australian Capital Territory",
    "New South Wales",
    "Northern Territory",
    "Queensland",
    "South Australia",
    "Tasmania",
    "Victoria",
    "Western Australia",
]

CURATED = [
    # Canada top-up for regions not covered by the first pass.
    ("KB Etching Service", "Canada", "Newfoundland and Labrador", "Engraver", "https://www.kbetching.ca/", None, None, "Paradise, Newfoundland and Labrador local laser engraving provider."),
    ("Atlantic Laser Works", "Canada", "New Brunswick", "Engraver", "https://www.atlanticlaserworks.com/", None, None, "New Brunswick custom laser art and engraving provider."),
    # Australia, state/territory scoped.
    ("Modelcraft Laser", "Australia", "New South Wales", "Engraver", "https://www.mclaser.com.au/", None, None, "Sydney laser cutting and laser engraving service."),
    ("LightScribe", "Australia", "New South Wales", "Engraver", "https://www.lightscribe.com.au/laser-engraving/", None, None, "Sydney laser engraving provider with Australia-wide delivery."),
    ("Industrial Plastic Products", "Australia", "New South Wales", "Engraver", "https://ippl.net.au/", None, None, "Sydney laser engraving, industrial sign and engraving provider."),
    ("SMS Laser Cutting", "Australia", "New South Wales", "Engraver", "https://smslaser.com.au/service/laser-engraving/", None, None, "Sydney and Melbourne laser engraving and cutting service."),
    ("Instant Engraving", "Australia", "Victoria", "Engraver", "https://instantengraving.com.au/", None, None, "Melbourne laser engraving, laser marking and etching service."),
    ("Australian Engraving", "Australia", "Victoria", "Engraver", "https://australianengraving.com.au/", None, None, "Australian engraving and etching provider based in Victoria."),
    ("Melbourne Engraving", "Australia", "Victoria", "Engraver", "https://melbourneengraving.com.au/", None, None, "Melbourne engraving shop and service provider."),
    ("Melbourne City Engraving", "Australia", "Victoria", "Engraver", "https://melbournecityengraving.com.au/", None, None, "Melbourne city engraving provider."),
    ("VR Laser", "Australia", "Victoria", "Engraver", "https://vr-laser.com.au/products/laser-engraving/", None, None, "Melbourne vector and raster laser engraving service."),
    ("Laser Dragon", "Australia", "Queensland", "Engraver", "https://laserdragon.com.au/", None, None, "Brisbane laser cutting, engraving and UV printing provider."),
    ("Verge Laser", "Australia", "Queensland", "Engraver", "https://www.vergelaser.com.au/", None, None, "Brisbane and Gold Coast laser engraving provider."),
    ("Print Promotion", "Australia", "Queensland", "Engraver", "https://printpromotion.com.au/laser-engraving-brisbane", None, None, "North Brisbane personalised gift engraving service."),
    ("Oz Engraving", "Australia", "Queensland", "Engraver", "https://ozengraving.com.au/", None, None, "Australian custom laser engraving provider."),
    ("Grand Engrave", "Australia", "Queensland", "Engraver", "https://grandengrave.com.au/trade-industry-engraving-brisbane/", None, None, "Brisbane trade and industry engraving provider."),
    ("Perthfect Engraver", "Australia", "Western Australia", "Engraver", "https://perthfectengraver.com.au/", None, None, "Perth laser engraving provider."),
    ("WA Engraving", "Australia", "Western Australia", "Engraver", "https://www.waengraving.com.au/", None, None, "Western Australia engraving service."),
    ("PCI Laser Cutting", "Australia", "Western Australia", "Engraver", "https://www.pcilasercutting.com.au/", None, None, "Perth laser cutting and design service."),
    ("Kanyana Engineering", "Australia", "Western Australia", "Engraver", "https://kanyanaengineering.com.au/laser-engraving/", None, None, "Perth laser engraving for stainless plaques, ID labels and compliance plates."),
    ("Artcom Fabrication", "Australia", "Western Australia", "Sign Company", "https://www.artcomfabrication.com.au/etch-engrave", None, None, "Perth signage/fabrication provider with etch and engrave services."),
    ("Adelaide Laser Engraving", "Australia", "South Australia", "Engraver", "https://www.adelaidelaserengraving.com.au/", None, None, "Adelaide custom laser engraving provider."),
    ("Evright Industrial", "Australia", "South Australia", "Engraver", "https://evrightindustrial.com.au/laser-engraving-adelaide/", None, None, "Adelaide industrial laser engraving provider."),
    ("Southern Engraving", "Australia", "South Australia", "Engraver", "https://southernengraving.com.au/laser-engraving-laser-marking-laser-cut/", None, None, "Adelaide laser engraving, marking and cutting provider."),
    ("Hawk Manufacturing", "Australia", "South Australia", "Engraver", "https://hawkmfg.com.au/laser-etching-and-engraving-adelaide/", None, None, "Adelaide laser etching and engraving provider."),
    ("Phrax Laser", "Australia", "South Australia", "Engraver", "https://www.phraxlaser.com.au/", None, None, "Adelaide custom laser cutting and engraving service."),
    ("The Outback Engraver", "Australia", "Northern Territory", "Engraver", "https://outbackengraver.com.au/", None, None, "Darwin engraving provider."),
    ("Laser Legends Darwin", "Australia", "Northern Territory", "Engraver", "https://laserlegends.com.au/", None, None, "Darwin laser engraving provider."),
    ("Territory Engraving", "Australia", "Northern Territory", "Engraver", "https://www.territoryengraving.com.au/", None, None, "Darwin and Northern Territory engraving service."),
    ("Creative Spot NT", "Australia", "Northern Territory", "Engraver", "https://www.creativespotnt.com.au/", None, None, "Darwin creative and engraving provider."),
    ("Evright Industrial Canberra", "Australia", "Australian Capital Territory", "Engraver", "https://evrightindustrial.com.au/laser-engraving-canberra/", None, None, "Canberra laser engraving service page from Evright Industrial."),
]


def infer_country(state: str) -> str:
    if state in CANADA_REGIONS:
        return "Canada"
    if state in AUSTRALIA_REGIONS:
        return "Australia"
    return "USA"


def build_metadata(rows: list[dict]) -> dict:
    return {
        "count": len(rows),
        "categories": sorted({row.get("category") for row in rows if row.get("category")}),
        "countries": sorted({row.get("country") or infer_country(row.get("state", "")) for row in rows}),
        "states": sorted({row.get("state") for row in rows if row.get("state")}),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = json.loads(DATA_PATH.read_text())
    for row in existing:
        row["country"] = row.get("country") or infer_country(row.get("state", ""))

    existing_company = {norm_key(row.get("company")) for row in existing}
    existing_host = {host_of(row.get("website") or "") for row in existing if row.get("website")}
    existing_email = {str(row.get("email")).lower() for row in existing if row.get("email")}

    candidates = []
    rejected = []
    seen_host = set()
    for company, country, region, category, website, email, phone, notes in CURATED:
        candidate = {
            "sourceFile": "international-region-pass-2026-06-13",
            "company": company,
            "country": country,
            "state": region,
            "county": region,
            "category": category,
            "website": website,
            "email": clean_email(email),
            "phone": phone,
            "address": f"{region}, {country}",
            "quality": 8,
            "mainBrand": None,
            "linkedin": None,
            "instagram": None,
            "facebook": None,
            "notes": notes,
        }
        host = host_of(website)
        email_key = (candidate.get("email") or "").lower()
        if norm_key(company) in existing_company or host in existing_host or host in seen_host or (email_key and email_key in existing_email):
            rejected.append({**candidate, "rejectReason": "duplicate before verification"})
            continue
        seen_host.add(host)
        candidates.append(candidate)

    accepted = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(verify, candidate) for candidate in candidates]
        for future in concurrent.futures.as_completed(futures):
            ok, verified = future.result()
            if ok:
                accepted.append(verified)
            else:
                rejected.append(verified)

    accepted.sort(key=lambda r: (r.get("country", ""), r["state"], r["category"], r["company"]))
    start_id = max(int(row.get("id") or 0) for row in existing) + 1
    additions = []
    for idx, row in enumerate(accepted, start=start_id):
        additions.append(
            {
                "id": idx,
                "country": row.get("country") or infer_country(row["state"]),
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
                "address": row.get("address") or f"{row['state']}, {row.get('country') or infer_country(row['state'])}",
                "quality": row.get("quality") or 8,
                "sellsPlaques": bool(row.get("sellsPlaques")),
                "mainBrand": row.get("mainBrand"),
                "notes": row.get("notes"),
                "publicationStatus": "public",
                "contactStatus": row.get("contactStatus"),
            }
        )

    merged = existing + additions
    DATA_PATH.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
    META_PATH.write_text(json.dumps(build_metadata(merged), indent=2) + "\n")

    by_country = collections.Counter(row["country"] for row in additions)
    by_region = collections.Counter(f"{row['country']} / {row['state']}" for row in additions)
    covered_canada = sorted({row["state"] for row in merged if row.get("country") == "Canada"})
    covered_australia = sorted({row["state"] for row in merged if row.get("country") == "Australia"})

    (OUT_DIR / "accepted.json").write_text(json.dumps(additions, indent=2, ensure_ascii=False) + "\n")
    (OUT_DIR / "rejected.json").write_text(json.dumps(rejected, indent=2, ensure_ascii=False) + "\n")
    (OUT_DIR / "report.md").write_text(
        "\n".join(
            [
                "# International Region Pass - 2026-06-13",
                "",
                f"- Curated seed rows: {len(CURATED)}",
                f"- Accepted rows: {len(additions)}",
                f"- Rejected / duplicate rows: {len(rejected)}",
                f"- New live row count: {len(merged)}",
                f"- Accepted by country: {dict(sorted(by_country.items()))}",
                f"- Accepted by region: {dict(sorted(by_region.items()))}",
                f"- Canada regions covered in dataset: {covered_canada}",
                f"- Australia regions covered in dataset: {covered_australia}",
                "",
                "Searched but no direct company-site candidate accepted in this pass:",
                "- Canada: Prince Edward Island, Northwest Territories, Nunavut, Yukon",
                "- Australia: Tasmania",
                "",
                "Quality gates:",
                "- Region-specific searches were used only as candidate discovery.",
                "- Each row had to pass direct website fetch and service-evidence verification.",
                "- Existing company/site/email duplicates were rejected.",
                "",
                f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
            ]
        )
        + "\n"
    )
    print(f"accepted={len(additions)} rejected={len(rejected)} total={len(merged)}")
    print(f"report_path={OUT_DIR / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
