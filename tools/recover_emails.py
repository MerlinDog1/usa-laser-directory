#!/usr/bin/env python3
"""
Recover public business contact emails for usa-laser-directory.

This script is intentionally non-destructive:
- reads data/directory-data.json
- identifies missing or invalid emails
- lightly crawls known company websites
- writes review outputs under outputs/email-recovery/
- never overwrites data/directory-data.json
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
from dataclasses import dataclass
from email.utils import parseaddr
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, unquote, urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen


DEFAULT_INPUT = Path("data/directory-data.json")
DEFAULT_OUTPUT_DIR = Path("outputs/email-recovery")

EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+-])([A-Za-z0-9._%+\-']{1,80}@[A-Za-z0-9.-]{1,120}\.[A-Za-z]{2,24})(?![A-Za-z0-9._%+-])",
    re.I,
)

CONTACT_PATH_HINTS = (
    "contact",
    "about",
    "team",
    "staff",
    "location",
    "locations",
    "support",
    "quote",
    "request",
    "service",
)

GOOD_LOCAL_PARTS = {
    "info",
    "sales",
    "contact",
    "hello",
    "support",
    "office",
    "service",
    "orders",
    "admin",
    "customerservice",
}

BAD_LOCAL_PARTS = {
    "example",
    "test",
    "noreply",
    "no-reply",
    "donotreply",
    "do-not-reply",
    "postmaster",
    "webmaster",
    "abuse",
    "privacy",
    "legal",
}

BAD_DOMAIN_PARTS = (
    "sentry",
    "wixpress",
    "wix.com",
    "wixstatic",
    "shopify",
    "squarespace",
    "wordpress.com",
    "example.com",
    "example.org",
    "domain.com",
    "email.com",
    "mysite.com",
    "yourdomain",
    "godaddy",
    "mailchimp",
    "constantcontact",
)

BAD_SUFFIXES = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".css",
    ".js",
    ".json",
    ".xml",
    ".pdf",
)


@dataclass
class Candidate:
    row_id: int | str
    company: str
    state: str
    website: str
    email: str
    score: int
    source_url: str
    source_kind: str
    reasons: list[str]


class LinkEmailParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[str] = []
        self.mailtos: list[str] = []
        self.cfemails: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k.lower(): v or "" for k, v in attrs}
        if tag.lower() == "a":
            href = attrs_dict.get("href", "").strip()
            if href.lower().startswith("mailto:"):
                self.mailtos.append(href)
            elif href:
                self.links.append(urljoin(self.base_url, href))
        cfemail = attrs_dict.get("data-cfemail")
        if cfemail:
            self.cfemails.append(cfemail)


def decode_cfemail(value: str) -> str | None:
    try:
        data = bytes.fromhex(value)
        key = data[0]
        return "".join(chr(b ^ key) for b in data[1:])
    except Exception:
        return None


def canonical_email(raw: str) -> str | None:
    if not raw:
        return None
    raw = html.unescape(unquote(str(raw))).strip()
    if raw.lower().startswith("mailto:"):
        raw = raw[7:]
    raw = raw.split("?", 1)[0].strip()
    _, parsed = parseaddr(raw)
    candidate = parsed or raw
    candidate = candidate.strip(" \t\r\n<>[](){}'\".,;:")
    if not candidate:
        return None
    match = EMAIL_RE.search(candidate)
    if not match:
        return None
    return match.group(1)


def is_valid_business_email(email: str | None) -> tuple[bool, str]:
    clean = canonical_email(email or "")
    if not clean:
        return False, "not an email"
    lower = clean.lower()
    local, domain = lower.rsplit("@", 1)
    if any(ch in lower for ch in ("?", "&", "=", "/")):
        return False, "contains URL/query characters"
    if any(lower.endswith(suffix) for suffix in BAD_SUFFIXES):
        return False, "looks like an asset filename"
    if any(part in domain for part in BAD_DOMAIN_PARTS):
        return False, "platform/system/example domain"
    if local in BAD_LOCAL_PARTS:
        return False, "role address not useful for sales/contact"
    if len(local) > 64 or len(domain) > 253:
        return False, "email too long"
    if "." not in domain or domain.startswith(".") or domain.endswith("."):
        return False, "invalid domain"
    return True, "valid"


def registered_domain(url_or_domain: str) -> str:
    parsed = urlparse(url_or_domain if "://" in url_or_domain else f"https://{url_or_domain}")
    host = (parsed.netloc or parsed.path).lower().split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    parts = [p for p in host.split(".") if p]
    if len(parts) >= 3 and parts[-2] in {"co", "com", "net", "org"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def fetch(url: str, timeout: int, user_agent: str) -> tuple[str | None, str | None]:
    req = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5",
        },
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type and not content_type.startswith("application/xhtml"):
                return None, f"skipped non-html content-type {content_type}"
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read(1_500_000).decode(charset, errors="replace")
            return body, None
    except HTTPError as exc:
        return None, f"http {exc.code}"
    except URLError as exc:
        return None, f"url error {exc.reason}"
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def extract_candidates_from_html(body: str, source_url: str, row: dict) -> tuple[list[Candidate], list[str]]:
    parser = LinkEmailParser(source_url)
    parser.feed(body)

    emails: list[tuple[str, str]] = []
    for mailto in parser.mailtos:
        parsed = canonical_email(mailto)
        if parsed:
            emails.append((parsed, "mailto"))
    for match in EMAIL_RE.finditer(html.unescape(body)):
        parsed = canonical_email(match.group(1))
        if parsed:
            emails.append((parsed, "visible"))
    for encoded in parser.cfemails:
        decoded = decode_cfemail(encoded)
        parsed = canonical_email(decoded or "")
        if parsed:
            emails.append((parsed, "cloudflare"))

    seen: set[str] = set()
    candidates: list[Candidate] = []
    site_domain = registered_domain(row.get("website", ""))
    for email, kind in emails:
        key = email.lower()
        if key in seen:
            continue
        seen.add(key)
        valid, reason = is_valid_business_email(email)
        if not valid:
            continue
        score, reasons = score_email(email, kind, site_domain, source_url)
        if reason != "valid":
            reasons.append(reason)
        candidates.append(
            Candidate(
                row_id=row.get("id", ""),
                company=row.get("company", ""),
                state=row.get("state", ""),
                website=row.get("website", ""),
                email=email,
                score=score,
                source_url=source_url,
                source_kind=kind,
                reasons=reasons,
            )
        )
    return candidates, parser.links


def score_email(email: str, source_kind: str, site_domain: str, source_url: str) -> tuple[int, list[str]]:
    score = 40
    reasons = [f"found as {source_kind}"]
    local, domain = email.lower().rsplit("@", 1)
    email_domain = registered_domain(domain)
    if source_kind == "mailto":
        score += 25
        reasons.append("mailto link")
    elif source_kind == "cloudflare":
        score += 20
        reasons.append("cloudflare-protected email")
    else:
        score += 10
        reasons.append("visible page text")
    if site_domain and email_domain == site_domain:
        score += 25
        reasons.append("email domain matches website")
    elif site_domain and (site_domain in email_domain or email_domain in site_domain):
        score += 15
        reasons.append("email domain resembles website")
    elif domain in {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com", "sbcglobal.net", "pacbell.net"}:
        score += 5
        reasons.append("common small-business mailbox")
    if local in GOOD_LOCAL_PARTS:
        score += 10
        reasons.append("useful contact role")
    if any(hint in urlparse(source_url).path.lower() for hint in CONTACT_PATH_HINTS):
        score += 10
        reasons.append("found on contact/about-style page")
    return min(score, 100), reasons


def candidate_pages(home_url: str, body: str, links: Iterable[str], max_pages: int) -> list[str]:
    home_url = normalize_url(home_url)
    home_domain = registered_domain(home_url)
    ranked: list[tuple[int, str]] = [(0, home_url)]
    seen = {home_url}
    for raw in links:
        url = normalize_url(raw)
        if not url or url in seen:
            continue
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if registered_domain(url) != home_domain:
            continue
        path = parsed.path.lower()
        if any(path.endswith(suffix) for suffix in BAD_SUFFIXES):
            continue
        rank = 50
        for i, hint in enumerate(CONTACT_PATH_HINTS):
            if hint in path:
                rank = min(rank, 10 + i)
        if rank < 50:
            ranked.append((rank, url))
            seen.add(url)
    ranked.sort(key=lambda item: (item[0], len(item[1])))
    return [url for _, url in ranked[:max_pages]]


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not urlparse(url).scheme:
        url = f"https://{url}"
    url, _ = urldefrag(url)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    return parsed.geturl()


def target_rows(rows: list[dict], states: set[str] | None, ids: set[str] | None) -> list[dict]:
    selected = []
    for row in rows:
        valid, _ = is_valid_business_email(row.get("email"))
        if valid:
            continue
        if not row.get("website"):
            continue
        if states and str(row.get("state", "")).lower() not in states:
            continue
        if ids and str(row.get("id")) not in ids:
            continue
        selected.append(row)
    return selected


def best_by_row(candidates: list[Candidate]) -> dict[str, Candidate]:
    best: dict[str, Candidate] = {}
    for candidate in candidates:
        key = str(candidate.row_id)
        current = best.get(key)
        if current is None or candidate.score > current.score:
            best[key] = candidate
    return best


def write_outputs(rows: list[dict], candidates: list[Candidate], invalid_rows: list[dict], output_dir: Path, threshold: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    deduped_candidates = dedupe_candidates(candidates)

    with (output_dir / "recovered_emails_candidates.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "company", "state", "website", "email", "score", "source_kind", "source_url", "reasons"],
        )
        writer.writeheader()
        for c in sorted(deduped_candidates, key=lambda item: (str(item.row_id), -item.score, item.email.lower())):
            writer.writerow(
                {
                    "id": c.row_id,
                    "company": c.company,
                    "state": c.state,
                    "website": c.website,
                    "email": c.email,
                    "score": c.score,
                    "source_kind": c.source_kind,
                    "source_url": c.source_url,
                    "reasons": "; ".join(c.reasons),
                }
            )

    with (output_dir / "invalid_existing_emails.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "company", "state", "website", "email", "reason"])
        writer.writeheader()
        for row in invalid_rows:
            _, reason = is_valid_business_email(row.get("email"))
            writer.writerow(
                {
                    "id": row.get("id", ""),
                    "company": row.get("company", ""),
                    "state": row.get("state", ""),
                    "website": row.get("website", ""),
                    "email": row.get("email", ""),
                    "reason": reason,
                }
            )

    proposed = [dict(row) for row in rows]
    invalid_by_id = {str(row.get("id")): row for row in invalid_rows}
    best = best_by_row(deduped_candidates)
    applied = 0
    cleared_invalid = 0
    autofills: list[Candidate] = []
    for row in proposed:
        invalid_original = invalid_by_id.get(str(row.get("id")))
        if invalid_original and row.get("email"):
            original = row.get("email")
            row["email"] = None
            row["notes"] = (
                f"{row.get('notes', '').rstrip()} | "
                f"Email recovery cleanup: removed invalid existing email {original!r}"
            ).strip(" |")
            cleared_invalid += 1
        candidate = best.get(str(row.get("id")))
        if candidate and is_auto_fill_candidate(candidate, threshold):
            original = invalid_original.get("email") if invalid_original else row.get("email")
            row["email"] = candidate.email
            note = f"Email recovery candidate: {candidate.email} ({candidate.score}) from {candidate.source_url}"
            if original:
                note += f"; replaced invalid existing email {original!r}"
            row["notes"] = f"{row.get('notes', '').rstrip()} | {note}".strip(" |")
            applied += 1
            autofills.append(candidate)
    (output_dir / "directory-data.proposed.json").write_text(json.dumps(proposed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with (output_dir / "auto_fill_emails.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "company", "state", "website", "email", "score", "source_kind", "source_url", "reasons"],
        )
        writer.writeheader()
        for c in sorted(autofills, key=lambda item: str(item.row_id)):
            writer.writerow(
                {
                    "id": c.row_id,
                    "company": c.company,
                    "state": c.state,
                    "website": c.website,
                    "email": c.email,
                    "score": c.score,
                    "source_kind": c.source_kind,
                    "source_url": c.source_url,
                    "reasons": "; ".join(c.reasons),
                }
            )

    summary = {
        "rows_total": len(rows),
        "invalid_or_missing_email_rows": len(invalid_rows),
        "candidate_count": len(deduped_candidates),
        "rows_with_candidates": len(best),
        "proposed_fills_at_threshold": applied,
        "invalid_existing_emails_cleared": cleared_invalid,
        "threshold": threshold,
        "auto_fill_rule": "score >= threshold and email domain matches/resembles website domain",
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def is_auto_fill_candidate(candidate: Candidate, threshold: int) -> bool:
    if candidate.score < threshold:
        return False
    reasons = set(candidate.reasons)
    return "email domain matches website" in reasons or "email domain resembles website" in reasons


def dedupe_candidates(candidates: list[Candidate]) -> list[Candidate]:
    by_row_email: dict[tuple[str, str], Candidate] = {}
    for candidate in candidates:
        key = (str(candidate.row_id), candidate.email.lower())
        current = by_row_email.get(key)
        if current is None or candidate.score > current.score:
            candidate.email = candidate.email.lower()
            by_row_email[key] = candidate
    return list(by_row_email.values())


def run(args: argparse.Namespace) -> int:
    rows = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise SystemExit("Expected data/directory-data.json to be a list of company records")

    states = {state.strip().lower() for state in args.state.split(",") if state.strip()} if args.state else None
    ids = {item.strip() for item in args.ids.split(",") if item.strip()} if args.ids else None
    invalid_rows = [row for row in rows if not is_valid_business_email(row.get("email"))[0]]
    selected = target_rows(rows, states, ids)
    if args.limit > 0:
        selected = selected[: args.limit]

    all_candidates: list[Candidate] = []
    crawl_log: list[dict] = []
    for index, row in enumerate(selected, start=1):
        home_url = normalize_url(row.get("website", ""))
        if not home_url:
            continue
        print(f"[{index}/{len(selected)}] {row.get('company')} <{home_url}>", flush=True)
        body, error = fetch(home_url, args.timeout, args.user_agent)
        if error:
            crawl_log.append({"id": row.get("id"), "company": row.get("company"), "url": home_url, "status": error})
            continue
        first_candidates, links = extract_candidates_from_html(body or "", home_url, row)
        all_candidates.extend(first_candidates)
        pages = candidate_pages(home_url, body or "", links, args.max_pages)
        for page_url in pages[1:]:
            if args.delay:
                time.sleep(args.delay)
            page_body, page_error = fetch(page_url, args.timeout, args.user_agent)
            if page_error:
                crawl_log.append({"id": row.get("id"), "company": row.get("company"), "url": page_url, "status": page_error})
                continue
            page_candidates, _ = extract_candidates_from_html(page_body or "", page_url, row)
            all_candidates.extend(page_candidates)
        if args.delay:
            time.sleep(args.delay)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "crawl_log.json").write_text(json.dumps(crawl_log, indent=2) + "\n", encoding="utf-8")
    write_outputs(rows, all_candidates, invalid_rows, args.output_dir, args.threshold)
    print(f"Wrote outputs to {args.output_dir}")
    print(f"Candidates: {len(all_candidates)}")
    print(f"Rows with candidates: {len(best_by_row(all_candidates))}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recover public business emails from known company websites.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int, default=10, help="Max target rows to crawl. Default: 10 for safe dry runs.")
    parser.add_argument("--state", help="Comma-separated state filter, e.g. California,Texas")
    parser.add_argument("--ids", help="Comma-separated directory ids to crawl.")
    parser.add_argument("--max-pages", type=int, default=4, help="Max same-site pages per company, including homepage.")
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--delay", type=float, default=0.5, help="Polite delay between requests.")
    parser.add_argument("--threshold", type=int, default=85, help="Score required for proposed JSON fill.")
    parser.add_argument(
        "--user-agent",
        default="USA-Laser-Directory email recovery bot (+https://github.com/MerlinDog1/usa-laser-directory)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
