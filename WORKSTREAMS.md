# Mobility Platform Workstreams

This repository uses isolated branches and Git worktrees so agents and people can work in parallel without editing the same files.

## Integration rules

- `main` is the release branch.
- `integration/rigor-upgrade` is the shared integration branch.
- Use owner-scoped `work/<owner>/<stream>` branches in matching
  `.worktrees/<owner>-<stream>` directories.
- Pull requests target `integration/rigor-upgrade`, never `main`.
- Raw data in `Rice WC Hack/` is local, read-only, and must never be staged.
- Raw public pages in `data/raw/operations/` are local hash inputs and must never be staged.
- Generated artifacts are owned by their ETL, GTFS, OSM, or factor pipeline only; do not hand-edit them.
- Shared contracts must change first and require integrator review.
- Every change must include focused tests and `git diff --check` output.

## Ownership matrix

| Stream | Branch | Worktree | Owned paths | Depends on |
| --- | --- | --- | --- | --- |
| W0 Foundation | integration-owned | repository root | `pyproject.toml`, `uv.lock`, `.python-version`, CI, `dashboard/app.py`, shared contracts/source registry, fixtures, `.gitignore`, `WORKSTREAMS.md` | None |
| W1 Public evidence | `work/<owner>/public` | `.worktrees/<owner>-public` | `dashboard/pipeline/gtfs/`, `dashboard/pipeline/public/`, `dashboard/tests/gtfs/`, `dashboard/tests/public/`, `data/snapshots/` including operational evidence | W0 contracts |
| W2 Rice enrichment | `work/<owner>/etl` | `.worktrees/<owner>-etl` | `dashboard/pipeline/etl/`, `dashboard/pipeline/schemas/`, `dashboard/tests/etl/`, Rice-derived cache artifacts | W0 contracts |
| W3 Movement/access and comparison | `work/<owner>/models` | `.worktrees/<owner>-models` | `dashboard/models/movement.py`, `dashboard/models/access.py`, `dashboard/domain/comparison.py`, movement/access/comparison tests under `dashboard/tests/models/` | W0 fixtures |
| W4 Interventions and portfolio | `work/<owner>/interventions` | `.worktrees/<owner>-interventions` | `dashboard/models/interventions.py`, `dashboard/domain/decision_support.py`, `dashboard/domain/portfolio.py`, `dashboard/tests/interventions/`, `dashboard/tests/models/test_portfolio.py` | W0 fixtures |
| W5 UI | `work/<owner>/ui` | `.worktrees/<owner>-ui` | `dashboard/ui/`, `dashboard/viz/`, `dashboard/tests/ui/` | W0 fixtures |
| W6 QA/docs | `work/<owner>/qa-docs` | `.worktrees/<owner>-qa-docs` | `dashboard/tests/integration/`, `docs/`, `DATA_DOCUMENTATION.md`, `SUBMISSION_NARRATIVE.md`, `dashboard/README.md` | W1-W5 interfaces |

`dashboard/app.py` becomes integration-owned after W0. Workstreams wire features through modules and do not edit the application shell.

## Shared interfaces

The `dashboard/mobility_platform/contracts.py` module owns the stable data contracts:

- Contract version: `0.3.0` (`CONTRACT_VERSION`)

- `DataManifest`
- `DataQualityReport`
- `EvidenceMetric`
- `SourceReference`
- `MatchEvent`
- `MovementScenario`
- `AccessGapResult`
- `InterventionPackage`
- `InterventionOutcome`
- `InvestmentRecommendation`
- `CityMetrics`
- `ScenarioConfig`
- `ScenarioResult`

Contract changes require a focused commit and must update the corresponding fixture tests.
`InvestmentRecommendation.match_id` is required; adapters must never infer it from the currently selected match.

## Handoff checklist

Each workstream PR must state:

1. The problem solved and owned paths changed.
2. Inputs, outputs, and contract version.
3. Test command and result.
4. Data/artifact impact.
5. Known limitations and follow-up work.
6. Screenshot or sample output for UI changes.

## Local worktree setup

Start every new workstream from the latest integration commit. Choose a short,
unique owner ID such as your initials or agent name:

```powershell
git fetch origin
$repoRoot = (Get-Location).Path
$owner = "alice"
git worktree add ".worktrees/$owner-public" -b "work/$owner/public" origin/integration/rigor-upgrade
git worktree add ".worktrees/$owner-etl" -b "work/$owner/etl" origin/integration/rigor-upgrade
git worktree add ".worktrees/$owner-models" -b "work/$owner/models" origin/integration/rigor-upgrade
git worktree add ".worktrees/$owner-interventions" -b "work/$owner/interventions" origin/integration/rigor-upgrade
git worktree add ".worktrees/$owner-ui" -b "work/$owner/ui" origin/integration/rigor-upgrade
git worktree add ".worktrees/$owner-qa-docs" -b "work/$owner/qa-docs" origin/integration/rigor-upgrade
```

Only ETL contributors need the local Rice collection. Point their worktree at
the shared read-only directory without copying it:

```powershell
$env:MOBILITY_DATA_ROOT = Join-Path $repoRoot "Rice WC Hack"
```

Existing worktrees must be clean before rebasing or recreating them. Never
discard another contributor's uncommitted work to update a worktree.
