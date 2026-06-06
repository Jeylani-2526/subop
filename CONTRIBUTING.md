# Contributing to SUBOP

Thank you for being part of the SUBOP team. This document defines the rules every team member
follows to keep the repository clean, traceable, and easy to review by the advisor.

---

## Table of Contents

- [Branch Strategy](#branch-strategy)
- [Commit Message Convention](#commit-message-convention)
- [Pull Request Process](#pull-request-process)
- [Code Style](#code-style)
- [Weekly Workflow](#weekly-workflow)

---

## Branch Strategy

SUBOP uses a structured Gitflow adapted for a 3-person team.

### Branch Map

```
main
 └── develop
      ├── milestone/m2-research-feasibility
      ├── milestone/m3-architecture-setup
      ├── feature/postgres-connector          ← Omer
      ├── feature/etl-csv-pipeline            ← Abdullah
      └── feature/home-dashboard-wireframe    ← Beyza
```

### Branch Rules

| Branch | Purpose | Who merges here | Protected? |
|--------|---------|-----------------|------------|
| `main` | Stable, demo-ready code — advisor sees this | Only from `develop` via PR | ✅ Yes |
| `develop` | Integration branch — all features merge here first | Feature / milestone branches | ✅ Yes |
| `milestone/m*` | Milestone-scoped work — spans multiple weeks | Feature branches within the milestone | No |
| `feature/*` | Individual feature or task | Your own work | No |
| `hotfix/*` | Emergency fix to `main` | Merges to both `main` and `develop` | No |

### Rules for `main` and `develop`

- **Never push directly to `main` or `develop`**
- All changes go through a Pull Request
- At least **one team member must review** before merge to `develop`
- At least **two team members must review** before merge to `main`
- `main` is only updated at the end of a milestone, after advisor sign-off

### Creating a Branch

```bash
# Always branch from develop — never from main
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name

# For milestone-scoped work
git checkout -b milestone/m3-architecture-setup
```

---

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/).

### Format

```
type(scope): short description

[optional body — explain WHY, not WHAT]

[optional footer — refs, breaking changes]
```

### Types

| Type | When to use |
|------|-------------|
| `feat` | New feature or module |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no logic change |
| `refactor` | Restructure without feature change |
| `test` | Adding or fixing tests |
| `chore` | Build config, CI, dependencies |
| `perf` | Performance improvement |

### Scopes (match SUBOP module numbers)

| Scope | Module |
|-------|--------|
| `connectors` | Module 1 — Connector Framework |
| `abstraction` | Module 2 — Database Abstraction Layer |
| `etl` | Module 3 — ETL Engine |
| `cdc` | Module 4 — CDC / Real-Time Layer |
| `warehouse` | Module 5 — Metadata-Driven Data Warehouse |
| `bi` | Module 6 — BI Dashboard & OLAP Layer |
| `quality` | Module 7 — Data Quality Engine |
| `lineage` | Module 8 — Data Lineage |
| `catalog` | Module 9 — Data Catalog |
| `security` | Module 10 — Security & Compliance |
| `infra` | Docker, CI/CD, scripts |
| `docs` | Documentation |

### Examples

```bash
feat(connectors): add PostgreSQL connector with psycopg2 driver
feat(abstraction): implement type normalisation for MySQL and PostgreSQL
fix(etl): correct incremental load logic for timestamp-based watermark
docs(architecture): add v1.1 system architecture diagram
chore(infra): add health checks to all docker-compose services
test(connectors): add automated validation test for PostgreSQL SELECT/INSERT/UPDATE
refactor(warehouse): extract SCD Type 2 logic into reusable utility
perf(etl): parallelize CSV ingestion using concurrent.futures
feat(security): implement RBAC middleware for all FastAPI routes
docs(milestones): add M2 week plan and task breakdown
```

---

## Pull Request Process

### Before Opening a PR

- [ ] Your branch is up to date with `develop` (`git rebase develop`)
- [ ] Code runs locally without errors
- [ ] `docker compose up -d` still builds and starts successfully
- [ ] Tests written or updated where relevant
- [ ] Documentation updated if behaviour changed
- [ ] No `.env` file or credentials committed

### PR Title

Use the same format as commit messages:

```
feat(connectors): add PostgreSQL connector with automated validation test
```

### PR Description

Use the PR template (auto-loaded from `.github/pull_request_template.md`).

### Review Rules

- Minimum **1 approval** required before merge to `develop`
- Minimum **2 approvals** required before merge to `main`
- The PR author **cannot approve their own PR**
- Address all review comments before merging

### Merging

Use **Squash and Merge** for feature branches into `develop`.  
Use **Merge Commit** for `develop` into `main` (preserves milestone history).

---

## Code Style

### Python

- Formatter: **Black** (`black .`)
- Linter: **flake8** (`flake8 . --max-line-length=100`)
- Max line length: 100 characters
- Type hints required on all public functions
- Docstrings: Google style

```python
def extract(source_id: str, query: str, params: dict | None = None) -> list[dict]:
    """Extract rows from a registered data source.

    Args:
        source_id: Registered connector identifier (e.g. 'pg-warehouse').
        query:     SQL or NoSQL query string passed to the abstraction layer.
        params:    Optional query parameters for parameterised queries.

    Returns:
        List of row dictionaries with normalised column types.

    Raises:
        ConnectorNotFoundError: If source_id is not registered.
        AbstractionError:       If type normalisation fails for a column.
    """
```

### JavaScript / React (BI Dashboard — M9+)

- Formatter: **Prettier**
- Linter: **ESLint** (Airbnb config)
- Component files: PascalCase (`DashboardHome.jsx`)
- Utility files: camelCase (`formatQualityScore.js`)

### Docker / YAML

- Use 2-space indentation
- Pin image versions explicitly (e.g. `postgres:15`, not `postgres:latest`)
- All services must have health checks

---

## Weekly Workflow

This is the expected rhythm for each team member each week:

| Day | Action |
|-----|--------|
| Monday | Pull `develop`, create or continue feature branch |
| Wednesday | Push work-in-progress — open draft PR if blockers exist |
| Friday | Push completed work, open PR for review |
| Sunday | **Team sync (45 min)** — review open PRs, resolve blockers, merge approved PRs into `develop` |

**Every Sunday:** Abdullah sends the weekly written update to the advisor summarising what was merged
into `develop` that week, what is in progress, and what is blocked.

---

*Questions? Open a GitHub Discussion or raise it at the Sunday sync.*
