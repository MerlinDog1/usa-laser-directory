# International Laser Engraving Directory

A searchable, filterable directory of USA, Canadian and Australian laser engraving companies, sign companies, and laser equipment / consumable distributors, organized by country and state/province.

## Scope

This directory tracks two main categories:

- **Engraver** — companies offering laser engraving services
- **Distributor** — equipment / consumable distributors and dealer networks (for example Epilog, Trotec, Cermark dealers)

For distributors, we also aim to capture the **main represented brand** where identifiable.

## Data fields

Each entry should include where possible:

- Company name
- Country
- State / province
- Category (`Engraver` or `Distributor`)
- Main represented brand (for distributors)
- Website
- Email
- LinkedIn
- Instagram
- Phone
- Address
- Notes
- Quality score

## Workflow

Country and region workflow:

1. Research one state or province at a time
2. Collect candidates and dedupe carefully
3. Manually verify before integration
4. Append to `data/directory-data.json`
5. Update `data/metadata.json`
6. Commit + push after each verified batch

## Running locally

Open `index.html` in a browser, or serve with a static server:

```bash
python -m http.server 8000
```

Then visit `http://localhost:8000`
