# grafana-dashboards

The homelab Grafana's dashboards, synced by Grafana Git Sync. Grafana reads
`Dashboards/` from `main` as its source: each directory is a Grafana folder
and each JSON file a dashboard or folder resource. Dashboards in these folders
cannot be saved through the Grafana API; a change is a commit here.

## What writes here

- **Grafana.** Saving, creating or deleting a dashboard in a synced folder
  opens a pull request from a Grafana branch (`dashboard/…`, `import/…`,
  `bulk-delete/…`). Grafana signs its commits, and the pull request is
  squash-merged like any other.
- **Hand-written changes**, on a branch, as a pull request.

`main` accepts only signed commits through a pull request.

## Layout

| Path | Holds |
| --- | --- |
| `Dashboards/<folder>/…/<name>.json` | a dashboard (`dashboard.grafana.app`) |
| `Dashboards/<folder>/…/_folder.json` | the folder's UID and title (`folder.grafana.app`) |

## Checks

CI (`.github/workflows/ci.yaml`) runs on every pull request to `main`, every
push to `main`, and weekly. It runs, once each:

- gitleaks over the full history;
- `scripts/check-dashboards.py`, the rules Grafana needs and a linter cannot
  express: only JSON files (and README files) under `Dashboards/`, each a
  JSON object that is a Dashboard or a Folder resource, Folders only in
  `_folder.json`, a non-empty `metadata.name` unique within its kind, a
  non-empty `spec.title`, a `_folder.json` in every directory, and at least
  one dashboard;
- `yamllint --strict` (`.yamllint.yaml` checks mistakes, not style);
- the pre-commit hooks: workflow and Dependabot schemas, actionlint, and two
  private-key and secret scanners.

`CI` is a required status check on `main`, so a red run blocks the merge of
Grafana's pull requests too.

To run the checks locally:

```sh
python3 -m venv .venv
.venv/bin/pip install -r ci/requirements.txt
PATH="$PWD/.venv/bin:$PATH"
python3 scripts/check-dashboards.py
yamllint --strict .
pre-commit run --all-files
pre-commit install
```

`pre-commit install` also installs the pre-push gitleaks hook, which scans
the commits being pushed.
