#!/usr/bin/env python3
"""Verify and merge deeper USA laser/sign directory candidates.

This pass consumes the existing state-level proposal JSON files, but treats them
as untrusted candidate sources. A row is merged only when a direct website is
live, dedupe checks pass, and fetched page text contains relevant service terms.
"""

from __future__ import annotations

import concurrent.futures
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "directory-data.json"
META_PATH = ROOT / "data" / "metadata.json"
OUT_DIR = ROOT / "outputs" / "deeper-pass-2026-06-12"
REPORT_PATH = OUT_DIR / "report.md"
ACCEPTED_PATH = OUT_DIR / "accepted.json"
REJECTED_PATH = OUT_DIR / "rejected.json"

USER_AGENT = "Mozilla/5.0 (compatible; TetoDirectoryVerifier/1.0)"
MAX_WORKERS = 24
TIMEOUT = 9
MAX_BYTES = 650_000

STATE_ALIASES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}

SIGNAL_TERMS = [
    "laser engraving",
    "laser engraved",
    "laser engrave",
    "laser marking",
    "laser cutting",
    "engraving",
    "engraved",
    "etching",
    "etched",
    "plaque",
    "plaques",
    "trophy",
    "awards",
    "signage",
    "sign company",
    "custom signs",
    "vehicle graphics",
    "vinyl graphics",
    "wraps",
    "banners",
    "channel letters",
    "dimensional letters",
    "monument signs",
]

BAD_HOST_PARTS = [
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "yelp.com",
    "yellowpages.com",
    "mapquest.com",
    "google.com",
    "bing.com",
    "domainmarket",
    "hugedomains",
]

BAD_EMAILS = {
    "info@mysite.com",
    "example@example.com",
    "info@example.com",
    "email@example.com",
}


def norm_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def host_of(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def site_key(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{host_of(url)}"


def clean_url(url: Any) -> str | None:
    url = norm_text(url)
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    host = host_of(url)
    if not host or any(bad in host for bad in BAD_HOST_PARTS):
        return None
    return url


def clean_email(email: Any) -> str | None:
    email = norm_text(email).strip(".,;:")
    if not email or email.lower() in BAD_EMAILS:
        return None
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return None
    return email


def normalize_state(value: Any, fallback: str = "") -> str:
    value = norm_text(value or fallback)
    if not value:
        return ""
    return STATE_ALIASES.get(value.upper(), value)


def iter_dicts(value: Any):
    if isinstance(value, dict):
        if "company" in value and ("website" in value or "url" in value):
            yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def load_candidates() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted(ROOT.glob("*proposal.json")):
        try:
            payload = json.loads(path.read_text())
        except Exception:
            continue
        for raw in iter_dicts(payload):
            category = norm_text(raw.get("category"))
            if category not in {"Engraver", "Sign Company"}:
                continue
            company = norm_text(raw.get("company"))
            website = clean_url(raw.get("website") or raw.get("url"))
            state = normalize_state(raw.get("state") or raw.get("county"))
            if not company or not website or not state:
                continue
            key = (norm_key(company), host_of(website))
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "sourceFile": path.name,
                    "company": company,
                    "state": state,
                    "county": state,
                    "category": category,
                    "website": website,
                    "email": clean_email(raw.get("email")),
                    "linkedin": raw.get("linkedin") or None,
                    "instagram": raw.get("instagram") or None,
                    "facebook": raw.get("facebook") or None,
                    "phone": norm_text(raw.get("phone")),
                    "address": norm_text(raw.get("address") or raw.get("city_or_metro")),
                    "quality": int(raw.get("quality") if str(raw.get("quality")).isdigit() else 7),
                    "mainBrand": raw.get("mainBrand") or None,
                    "notes": norm_text(raw.get("notes")),
                }
            )
    return candidates


def fetch(url: str) -> tuple[str, str, int]:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    with urlopen(req, timeout=TIMEOUT) as resp:
        status = getattr(resp, "status", 200)
        final_url = resp.geturl()
        raw = resp.read(MAX_BYTES)
    text = raw.decode("utf-8", errors="ignore")
    return final_url, text, status


def textify(page: str) -> str:
    page = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", page)
    page = re.sub(r"(?is)<[^>]+>", " ", page)
    return html.unescape(re.sub(r"\s+", " ", page)).lower()


def page_score(text: str, category: str) -> tuple[int, list[str]]:
    hits = [term for term in SIGNAL_TERMS if term in text]
    score = len(hits)
    if category == "Sign Company" and any(term in text for term in ["signage", "custom signs", "vehicle graphics", "banners", "wraps"]):
        score += 2
    if category == "Engraver" and any(term in text for term in ["laser engraving", "laser marking", "engraving", "etched"]):
        score += 2
    return score, hits[:8]


def verify(candidate: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    url = candidate["website"]
    checked_urls = [url]
    texts: list[str] = []
    final_urls: list[str] = []
    try:
        final_url, page, status = fetch(url)
        checked_urls.append(final_url)
        final_urls.append(final_url)
        texts.append(textify(page))
        parsed = urlparse(final_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        for suffix in ["/services", "/laser-engraving", "/engraving", "/signs", "/signage", "/contact", "/about"]:
            try:
                child_url = urljoin(base, suffix)
                checked_urls.append(child_url)
                child_final, child_page, child_status = fetch(child_url)
                final_urls.append(child_final)
                texts.append(textify(child_page))
            except Exception:
                continue
    except Exception as exc:
        return False, {**candidate, "rejectReason": f"fetch failed: {exc}", "checkedUrls": checked_urls}

    host = host_of(url)
    if final_urls and host not in host_of(final_urls[0]):
        final_host = host_of(final_urls[0])
        if host not in final_host and final_host not in host:
            return False, {**candidate, "rejectReason": f"redirected to different host: {final_urls[0]}", "checkedUrls": checked_urls}

    combined = " ".join(texts)
    score, hits = page_score(combined, candidate["category"])
    if score < 2:
        return False, {**candidate, "rejectReason": "no sufficient laser/engraving/signage evidence", "signalHits": hits, "checkedUrls": checked_urls}

    accepted = dict(candidate)
    accepted["website"] = site_key(final_urls[0] if final_urls else url) + "/"
    accepted["quality"] = max(7, min(9, int(candidate.get("quality") or 7) + (1 if len(hits) >= 3 else 0)))
    accepted["sellsPlaques"] = any(term in combined for term in ["plaque", "plaques", "awards", "trophy", "trophies"])
    accepted["publicationStatus"] = "public"
    accepted["contactStatus"] = "verified_email" if accepted.get("email") else "website_verified"
    accepted["notes"] = (accepted.get("notes") or "").strip()
    evidence = f" | Deeper pass: direct website verified; signals: {', '.join(hits[:5])}."
    accepted["notes"] = (accepted["notes"] + evidence).strip()
    accepted["signalHits"] = hits
    accepted["checkedUrls"] = sorted(set(checked_urls))
    return True, accepted


def main() -> int:
    existing = json.loads(DATA_PATH.read_text())
    existing_company = {norm_key(row.get("company")) for row in existing}
    existing_site = {host_of(row.get("website") or "") for row in existing if row.get("website")}
    existing_email = {str(row.get("email")).lower() for row in existing if row.get("email")}

    raw_candidates = load_candidates()
    candidates = []
    pre_rejected = []
    seen_site: set[str] = set()
    for c in raw_candidates:
        email = (c.get("email") or "").lower()
        host = host_of(c["website"])
        if norm_key(c["company"]) in existing_company:
            pre_rejected.append({**c, "rejectReason": "duplicate company"})
            continue
        if host in existing_site:
            pre_rejected.append({**c, "rejectReason": "duplicate website host"})
            continue
        if email and email in existing_email:
            pre_rejected.append({**c, "rejectReason": "duplicate email"})
            continue
        if host in seen_site:
            pre_rejected.append({**c, "rejectReason": "duplicate candidate website host"})
            continue
        seen_site.add(host)
        candidates.append(c)

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = list(pre_rejected)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(verify, candidate) for candidate in candidates]
        for future in concurrent.futures.as_completed(futures):
            ok, row = future.result()
            if ok:
                accepted.append(row)
            else:
                rejected.append(row)

    accepted.sort(key=lambda r: (r["state"], r["category"], r["company"]))
    start_id = max(int(row.get("id") or 0) for row in existing) + 1
    clean_accepted = []
    for idx, row in enumerate(accepted, start=start_id):
        clean_accepted.append(
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

    merged = existing + clean_accepted
    states = sorted({row.get("state") for row in merged if row.get("state")})
    categories = sorted({row.get("category") for row in merged if row.get("category")})
    metadata = {"count": len(merged), "categories": categories, "states": states}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ACCEPTED_PATH.write_text(json.dumps(clean_accepted, indent=2) + "\n")
    REJECTED_PATH.write_text(json.dumps(rejected, indent=2) + "\n")
    DATA_PATH.write_text(json.dumps(merged, indent=2) + "\n")
    META_PATH.write_text(json.dumps(metadata, indent=2) + "\n")

    by_state: dict[str, int] = {}
    by_cat: dict[str, int] = {}
    for row in clean_accepted:
        by_state[row["state"]] = by_state.get(row["state"], 0) + 1
        by_cat[row["category"]] = by_cat.get(row["category"], 0) + 1

    REPORT_PATH.write_text(
        "\n".join(
            [
                "# USA Laser Directory Deeper Pass - 2026-06-12",
                "",
                f"- Source candidates found: {len(raw_candidates)}",
                f"- Candidates after pre-dedupe: {len(candidates)}",
                f"- Accepted new rows: {len(clean_accepted)}",
                f"- Rejected / duplicate rows: {len(rejected)}",
                f"- New live row count: {len(merged)}",
                f"- Accepted by category: {json.dumps(dict(sorted(by_cat.items())), sort_keys=True)}",
                f"- Accepted by state: {json.dumps(dict(sorted(by_state.items())), sort_keys=True)}",
                "",
                "Quality gates:",
                "- Category must be `Engraver` or `Sign Company`.",
                "- Company, state and direct website are required.",
                "- Existing company/site/email duplicates are rejected before fetch.",
                "- Social, map, directory and parked-domain hosts are rejected.",
                "- A live fetched page must contain laser/engraving/signage/awards/plaque/wrap/sign service evidence.",
                "",
                f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
            ]
        )
        + "\n"
    )

    print(f"accepted={len(clean_accepted)} rejected={len(rejected)} total={len(merged)}")
    print(f"accepted_path={ACCEPTED_PATH}")
    print(f"report_path={REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
