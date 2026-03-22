# USA Laser Engraving Directory

A searchable, filterable directory of USA laser engraving companies and laser equipment / consumable distributors, organized state by state.

## Scope

This directory tracks two main categories:

- **Engraver** — companies offering laser engraving services
- **Distributor** — equipment / consumable distributors and dealer networks (for example Epilog, Trotec, Cermark dealers)

For distributors, we also aim to capture the **main represented brand** where identifiable.

## Data fields

Each entry should include where possible:

- Company name
- State
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

State-by-state workflow:

1. Research one state at a time
2. Collect candidates and dedupe carefully
3. Manually verify before integration
4. Append to `data/directory-data.json`
5. Update `data/metadata.json`
6. Commit + push after each state

## Running locally

Open `index.html` in a browser, or serve with a static server:

```bash
python -m http.server 8000
```

Then visit `http://localhost:8000`
