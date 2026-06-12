#!/usr/bin/env python3
"""Merge a manually curated state-by-state USA laser/sign batch.

This intentionally does not trust search results. The list below is hand-picked
from the noisy state sweep, then every row is passed through the same direct-site
verifier used by the previous production pass.
"""

from __future__ import annotations

import collections
import datetime as dt
import json
import re
from pathlib import Path

from verify_and_merge_deeper_pass import DATA_PATH, META_PATH, clean_email, host_of, norm_key, verify

OUT_DIR = Path(__file__).resolve().parents[1] / "outputs" / "curated-state-batch-2026-06-12"

CURATED = [
    ("Alaska Life Designs", "Alaska", "Engraver", "https://www.alaskalifedesigns.com/", None, None, "Alaska custom engraving and gift personalization candidate."),
    ("Alaska Contract Printing", "Alaska", "Engraver", "https://alaskacontractprinting.com/create/Laser-Engraving?c=5180787", None, None, "Alaska contract printing shop with laser engraving product/service page."),
    ("Alaska Gift Source", "Alaska", "Engraver", "https://alaskagiftsource.com/create/Laser-Engraving?c=5180787", None, None, "Alaska gift shop with laser engraving service/product page."),
    ("Alaska Burning Bear", "Alaska", "Engraver", "https://www.alaskaburningbear.com/", None, None, "Alaska custom laser engraving business for awards, plaques and personalized goods."),
    ("Engraving Tumblers", "California", "Engraver", "https://engravingtumblers.com/hello-los-angeles/", None, None, "Los Angeles custom laser engraving and cutting service."),
    ("Uneak Uniforms", "California", "Engraver", "https://www.uneakuniforms.com/services/laser-engraving", None, None, "California uniform and custom laser engraving service."),
    ("Connecticut Laser & Engraving", "Connecticut", "Engraver", "https://ctlaserengraving.com/contact-us/", None, None, "Connecticut precision pad printing, laser marking and engraving provider."),
    ("Citrus Laser Engraving", "Florida", "Engraver", "https://www.citruslaserengraving.com/", None, None, "Citrus County Florida custom laser engraving business."),
    ("Southwest Florida Laser Engraving", "Florida", "Engraver", "https://swfllaser.com/", None, None, "Southwest Florida laser engraving service provider."),
    ("PX3 Laser", "Florida", "Engraver", "https://px3laser.com/", None, None, "Florida laser engraving and document/product support service."),
    ("Georgia Engraving", "Georgia", "Engraver", "https://georgiaengraving.com/order/", None, None, "Georgia custom laser engraving provider."),
    ("Georgia Stitch and Print", "Georgia", "Engraver", "https://georgiasap.com/laser-engraving/", None, None, "Georgia Stitch and Print custom laser engraving service."),
    ("CNC Woodarts Hawaii", "Hawaii", "Engraver", "https://www.cncwoodarts.com/pages/cnc-woodarts-hawaii-laser-engraving-cutting", None, None, "Hawaii CNC and laser engraving/cutting service."),
    ("Da Laser Guy", "Hawaii", "Engraver", "https://dalaserguy.com/", None, None, "Honolulu and Oahu mobile laser engraving service."),
    ("Sew Unique", "Illinois", "Engraver", "https://www.sewuniqueweb.com/", None, None, "Illinois screen printing, embroidery and laser engraving business."),
    ("Blythe's Sport Shop", "Indiana", "Engraver", "https://teamblythes.com/sports/engraving-lowell-indiana/", None, None, "Lowell Indiana trophy and laser engraving service."),
    ("Ember & Spruce", "Kansas", "Engraver", "https://emberandspruce.com/", None, None, "Topeka Kansas premium personalized gift and commercial laser engraving service."),
    ("One Above Marking", "Maine", "Engraver", "https://www.oneabovemarking.com/", None, None, "Maine onsite laser engraving and marking service."),
    ("Engrave Everything", "Maryland", "Engraver", "https://www.engraveeverything.us/", None, None, "Hagerstown Maryland laser engraving, cutting, custom signs and industrial marking."),
    ("Cutting Edge Engraving", "Minnesota", "Engraver", "https://www.cuttingedge-engraving.net/", None, None, "Minnesota engraving service for signs, plaques, awards and trophies."),
    ("Greater Minnesota Laser Engraving & Awards", "Minnesota", "Engraver", "http://laserengravingmn.com/", "engraving@GreaterMNEngraving.com", "(320) 485-2535", "Winsted Minnesota laser engraving and awards business."),
    ("Red Barn Laser Engraving", "Minnesota", "Engraver", "https://redbarnle.com/", None, None, "Northern Minnesota laser marking, cutting and engraving service."),
    ("Missouri River Monument", "Missouri", "Engraver", "https://morivermonument.com/product/laser-engraving/", None, None, "Missouri monument company with in-house laser engraving."),
    ("A3 Laser Engraving", "Missouri", "Engraver", "https://a3laserengraving.com/", "jraulgur@A3LaserEngraving.com", "660-202-2285", "Marshall Missouri professional laser engraving business."),
    ("The Laser Man Workshop", "New York", "Engraver", "https://www.lasermanworkshop.com/", None, None, "New York same-day local laser engraving workshop."),
    ("AC One Laser Engraving", "North Carolina", "Engraver", "https://www.aconelaserengraving.com/", None, None, "Shiloh North Carolina laser engraving business."),
    ("Ostling's Laser Craft", "North Carolina", "Engraver", "https://www.ostlingslasercraft.com/", None, None, "Raleigh North Carolina laser engraving and custom gift service."),
    ("Tri City Laser", "North Carolina", "Engraver", "https://tricitylaserinc.com/", None, None, "North Carolina laser cutting, engraving and design service."),
    ("Wilmington Engraving", "North Carolina", "Engraver", "https://wilmingtonengraving.com/", None, None, "Wilmington North Carolina engraving service."),
    ("M3 Laser Engraving", "Ohio", "Engraver", "https://www.m3engraving.com/", None, None, "Ohio laser engraving service for branding, signage and promotional products."),
    ("Reflective Edge", "Oklahoma", "Engraver", "https://www.reflectiveedge.com/laser-engraving", None, None, "Oklahoma laser engraving service."),
    ("Silsby Media", "Oklahoma", "Sign Company", "https://www.silsbymedia.com/", None, None, "Midwest City Oklahoma vehicle wrap and signage company."),
    ("Oregon Design Shop", "Oregon", "Engraver", "https://ordesignshop.com/laser-engraving", None, None, "Oregon laser engraving and custom design service."),
    ("Michener Sign", "Pennsylvania", "Sign Company", "https://michenersign.com/engraving/achieve-stunning-detail-with-diamond-drag-engraving/", None, None, "Pennsylvania sign company with engraving services."),
    ("LB3DR", "Rhode Island", "Engraver", "https://lb3dr.com/services/custom-laser-engraving-services-rhode-island/", None, None, "Rhode Island custom laser engraving service."),
    ("CC Laserworks", "South Carolina", "Engraver", "https://cclaserworks.com/", None, None, "South Carolina laser engraving business."),
    ("Tennessee Silencer", "Tennessee", "Engraver", "https://www.tennesseesilencer.com/laser-engraving", None, "865-603-4214", "Tennessee firearm and custom laser engraving service."),
    ("Tennessee Arms Company", "Tennessee", "Engraver", "https://tnarmsco.com/services_7", None, None, "Tennessee laser engraving service for firearms, knives and customer-supplied items."),
    ("BAR Engraving & Woodworks", "Virginia", "Engraver", "https://barengraving.com/", None, "(703) 629-6334", "Rileyville Virginia custom laser engraving and woodworks business."),
    ("Engraving Vancouver", "Washington", "Engraver", "https://engravingvancouver.com/", None, "(360) 404-7500", "Vancouver Washington laser engraving service."),
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = json.loads(DATA_PATH.read_text())
    existing_company = {norm_key(row.get("company")) for row in existing}
    existing_host = {host_of(row.get("website") or "") for row in existing if row.get("website")}
    existing_email = {str(row.get("email")).lower() for row in existing if row.get("email")}

    accepted = []
    rejected = []
    for company, state, category, website, email, phone, notes in CURATED:
        candidate = {
            "sourceFile": "curated-state-batch-2026-06-12",
            "company": company,
            "state": state,
            "county": state,
            "category": category,
            "website": website,
            "email": clean_email(email),
            "phone": phone,
            "address": state,
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
        if key in existing_company or host in existing_host or (candidate_email and candidate_email in existing_email):
            rejected.append({**candidate, "rejectReason": "duplicate before verification"})
            continue
        ok, verified = verify(candidate)
        if not ok:
            rejected.append(verified)
            continue
        accepted.append(verified)
        existing_company.add(key)
        existing_host.add(host_of(verified["website"]))
        if verified.get("email"):
            existing_email.add(verified["email"].lower())

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
                "address": row.get("address") or row["state"],
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

    (OUT_DIR / "accepted.json").write_text(json.dumps(additions, indent=2) + "\n")
    (OUT_DIR / "rejected.json").write_text(json.dumps(rejected, indent=2) + "\n")
    by_state = collections.Counter(row["state"] for row in additions)
    by_category = collections.Counter(row["category"] for row in additions)
    report = [
        "# USA Laser Directory Curated State Batch - 2026-06-12",
        "",
        f"- Curated seed rows: {len(CURATED)}",
        f"- Accepted rows: {len(additions)}",
        f"- Rejected rows: {len(rejected)}",
        f"- New live row count: {len(merged)}",
        f"- Accepted by category: {dict(sorted(by_category.items()))}",
        f"- Accepted by state: {dict(sorted(by_state.items()))}",
        "",
        "Quality gates:",
        "- Rows were manually selected from the noisy state sweep before merge.",
        "- Each row still had to pass direct website fetch and service-evidence verification.",
        "- Existing company/site/email duplicates were rejected.",
        "",
        f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
    ]
    (OUT_DIR / "report.md").write_text("\n".join(report) + "\n")
    print(f"accepted={len(additions)} rejected={len(rejected)} total={len(merged)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
