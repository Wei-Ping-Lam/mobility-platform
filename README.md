# FIFA 2026 Mobility Platform

Evidence-backed Streamlit decision support for transportation readiness,
first/last-mile access, traffic-pressure scenarios, emissions, and investments
across the 11 U.S. FIFA 2026 host cities.

## Quick start

Install uv `0.11.16` or newer, then run:

```powershell
git clone --branch integration/rigor-upgrade https://github.com/Wei-Ping-Lam/mobility-platform.git
cd mobility-platform
uv python install 3.11
uv sync --all-groups --locked
uv run python -m streamlit run dashboard/app.py
```

The tracked compact artifacts support cache-only startup. Raw Rice, GTFS, and
OSM downloads are not required to preview the dashboard and remain untracked.

- [Dashboard and data documentation](dashboard/README.md)
- [Project architecture](docs/ARCHITECTURE.md)
- [Parallel workstream guide](WORKSTREAMS.md)
- [Contribution workflow](CONTRIBUTING.md)
- [Methodology](docs/METHODOLOGY.md)
- [Validation](docs/VALIDATION.md)
- [Source register](docs/SOURCE_REGISTER.md)
