# Contributing

Start with `docs/ARCHITECTURE.md` and `WORKSTREAMS.md`. Do not develop two
features in the same checkout.

## Create an isolated worktree

```powershell
git fetch origin
$owner = "your-initials"
$stream = "models" # or ui, public, etl, qa-docs
git worktree add ".worktrees/$owner-$stream" -b "work/$owner/$stream" origin/integration/rigor-upgrade
Set-Location ".worktrees/$owner-$stream"
uv sync --all-groups --locked
```

Use a different owner/stream combination for each concurrent branch. Never point
two worktrees at the same branch.

## Before editing

1. Claim one ownership row in `WORKSTREAMS.md` with your colleague.
2. List the files you expect to change.
   For Portfolio work, claim a specific objective renderer under
   `dashboard/ui/portfolio/` rather than the whole page.
3. If an integration seam is required, agree who edits it and land that edit as
   a small separate commit.
4. Rebase from `origin/integration/rigor-upgrade` before opening a pull request.

## Required checks

```powershell
uv run ruff check dashboard
uv run pytest <focused-test-paths>
git diff --check
```

Pull requests target `integration/rigor-upgrade` and use the repository template.
Keep generated snapshots with their owning pipeline change; never hand-edit them.
