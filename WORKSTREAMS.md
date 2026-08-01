# Mobility Platform Workstreams

This repository uses isolated branches and Git worktrees so agents and people can work in parallel without editing the same files.

## Integration rules

- `main` is the release branch.
- `integration/rigor-upgrade` is the shared integration branch.
- Work only on `work/<stream>` branches in `.worktrees/<stream>` directories.
- Pull requests target `integration/rigor-upgrade`, never `main`.
- Raw data in `Rice WC Hack/` is local, read-only, and must never be staged.
- Generated artifacts are owned by ETL or GTFS only; do not hand-edit them.
- Shared contracts must change first and require integrator review.
- Every change must include focused tests and `git diff --check` output.

## Ownership matrix

| Stream | Branch | Worktree | Owned paths | Depends on |
| --- | --- | --- | --- | --- |
| W0 Foundation | `work/foundation` | `.worktrees/foundation` | `dashboard/app.py`, `dashboard/mobility_platform/`, `dashboard/requirements.txt`, `.gitignore`, `WORKSTREAMS.md` | None |
| W1 ETL | `work/etl` | `.worktrees/etl` | `dashboard/pipeline/etl/`, `dashboard/pipeline/schemas/`, `dashboard/tests/etl/`, `dashboard/cache/manifest.json` | W0 contracts |
| W2 GTFS | `work/gtfs` | `.worktrees/gtfs` | `dashboard/pipeline/gtfs/`, `dashboard/tests/gtfs/`, `data/gtfs_transit_scores.*` | W0 contracts |
| W3 Models | `work/models` | `.worktrees/models` | `dashboard/domain/`, `dashboard/models/`, `dashboard/tests/models/` | W0 contracts |
| W4 UI | `work/ui` | `.worktrees/ui` | `dashboard/ui/`, `dashboard/viz/`, `dashboard/tests/ui/` | W0 contracts |
| W5 QA/docs | `work/qa-docs` | `.worktrees/qa-docs` | `dashboard/tests/integration/`, `docs/`, `DATA_DOCUMENTATION.md`, `SUBMISSION_NARRATIVE.md`, `dashboard/README.md` | W1–W4 interfaces |

`dashboard/app.py` becomes integration-owned after W0. Workstreams wire features through modules and do not edit the application shell.

## Shared interfaces

The `dashboard/mobility_platform/contracts.py` module owns the stable data contracts:

- Contract version: `0.2.0` (`CONTRACT_VERSION`)

- `DataManifest`
- `DataQualityReport`
- `EvidenceMetric`
- `CityMetrics`
- `ScenarioConfig`
- `ScenarioResult`

Contract changes require a focused commit and must update the corresponding fixture tests.

## Handoff checklist

Each workstream PR must state:

1. The problem solved and owned paths changed.
2. Inputs, outputs, and contract version.
3. Test command and result.
4. Data/artifact impact.
5. Known limitations and follow-up work.
6. Screenshot or sample output for UI changes.

## Local worktree setup

```powershell
git worktree add .worktrees/foundation -b work/foundation integration/rigor-upgrade
git worktree add .worktrees/etl -b work/etl integration/rigor-upgrade
git worktree add .worktrees/gtfs -b work/gtfs integration/rigor-upgrade
git worktree add .worktrees/models -b work/models integration/rigor-upgrade
git worktree add .worktrees/ui -b work/ui integration/rigor-upgrade
git worktree add .worktrees/qa-docs -b work/qa-docs integration/rigor-upgrade
```

Point every worktree at the shared local data without copying it:

```powershell
$env:MOBILITY_DATA_ROOT = "C:\Users\cps8\mobility-platform\Rice WC Hack"
```
