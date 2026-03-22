# CA-TX Sign Companies Proposal

## Summary

| Metric | Count |
|--------|-------|
| **California** | 8 companies |
| **Texas** | 6 companies |
| **Total** | 14 companies |

---

## Strongest Entries

These entries have website + email + phone or address (multiple contact channels):

### California

| Company | Contact Quality | Notes |
|---------|-----------------|-------|
| **Front Signs** | ⭐⭐⭐ | Website + email + phone + physical address (Burbank). Full-service with CAD, metal/plastic/wood laser cutting capabilities. |
| **RMS Laser Group** | ⭐⭐⭐ | Website + email + phone. 25+ years, ADA signage specialist, full laser/UV/CNC capabilities. |
| **Houston Sign Company** | ⭐⭐⭐ | Website + email + phone + physical address (Houston, TX). Industrial labeling, custom signage. |
| **Texas Sign & Graphics** | ⭐⭐⭐ | Website. Wholesale manufacturer with extensive capabilities (laser, UV, digital cutting, sublimation). |

### Texas

| Company | Contact Quality | Notes |
|---------|-----------------|-------|
| **Houston Sign** | ⭐⭐⭐ | Website + email + phone + address. Long-established Houston sign company. |
| **Texas Sign & Graphics** | ⭐⭐⭐ | Website. Major wholesale supplier to sign shops across Texas. |
| **Digi Printing & Cutting** | ⭐⭐ | Website. San Antonio-based, ADA signs specialist, family operated since 2010. |
| **Fire Light Laser** | ⭐⭐ | Phone provided. Austin-area, awards/trophies/signs specialist. |

---

## Weak Entries (Avoid Merging or Flag)

These entries lack sufficient contact information or are too thin:

| Company | State | Issue |
|---------|-------|-------|
| **American Laser Co** | CA | Website only, no email/phone/address on contact page |
| **Evans Tool and Die** | CA | Industrial shop, sign division not prominent |
| **ZLazr** | TX | Website is e-commerce focused, minimal company info |
| **South Texas Signs** | TX | Website exists but limited contact details |
| **Lazer Image Inc** | CA | No contact info visible on homepage |

---

## Recommended Merge Approach

If adding Sign Company as a new filter/category to the USA Laser Directory:

1. **Create a new category filter**: "Sign Company" separate from "Laser Service Provider"

2. **Include these as sub-entries** rather than full directory entries initially:
   - Strong entries (4 CA + 4 TX): Full inclusion with all contact details
   - Medium entries (4 CA + 2 TX): Include with available data, flag as "partial"

3. **Suggested fields**:
   - `category`: "Sign Company" (distinct from laser cutting services)
   - `services`: Array of capabilities (laser cutting, engraving, UV printing, etc.)
   - `certifications`: Note if ADA-compliant (important for sign companies)

4. **Deduplication logic**:
   - Primary key: `domain` + `company_name`
   - Flag potential duplicates: Same address, similar names, shared phone

5. **Quality tiers for display**:
   - Tier 1 (high): Full contact + website + services list
   - Tier 2 (medium): Website + partial contact
   - Tier 3 (low): Website only → consider excluding

---

## Contact Coverage

| State | Full Contact | Partial | Website Only |
|-------|-------------|---------|--------------|
| CA | 2 | 4 | 2 |
| TX | 2 | 3 | 1 |
| **Total** | **4 (29%)** | **7 (50%)** | **3 (21%)** |

---

## Notes

- **Innotech Laser** appeared in Texas search results but is actually headquartered in Pennsylvania (Warminster, PA) - excluded from this proposal
- **Proj X Enterprise** website has changed to PMI certification services - no longer a sign company
- Companies were selected based on explicit laser cutting/engraving capabilities for signs
- Priority given to companies with visible websites and at least one additional contact channel
