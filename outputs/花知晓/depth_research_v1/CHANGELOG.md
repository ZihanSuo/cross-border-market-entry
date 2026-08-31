# depth_research_v1

- **variant**: `research_depth`
- **brief**: `briefs/flowerknows_thailand.json`
- **date**: 2026-08-12
- **process exit**: 0 (not `--strict-depth`)
- **Serper**: 7/7 ok; scrape: 0
- **citation**: 1 severe (TBD placeholder in competitor), 9 human-review (homepage-as-evidence)
- **depth gate**: 0 severe / 1 warn (`gap_fill_thin_search`)
- **artifact_check**: **3 severe** / 1 warn — NOT delivery-ready
  - `feas_channel_social_only` (non-social channel URLs < floor)
  - `comp_price_floor` (0 price+URL rows; need ≥5)
  - `comp_scrape_floor` (0 scrapes; need ≥2)
  - warn: `feas_falsifiable_thin`
- **note**: Guardrails blocked competitor draft twice; still left 1 citation severe. Prefer re-run or manual rewrite before treating as finished.
