# Infrastructure Layer Notes — Week 8

## 1. CI/CD Scope Clarification

A CI/CD workflow already existed before Week 8 under
`.github/workflows/ci.yml`.

The existing workflow was part of the initial repository setup and was
configured to run on push and pull request events for the `develop` and
`main` branches.

The pre-existing CI configuration included:

- a lint job using Black and flake8;
- a pytest-based test job;
- a PostgreSQL 15 service container;
- Python 3.10;
- test discovery and execution under the `services/` directory.

The existing workflow did not fully match the Week 8 CI/CD requirements.
In particular:

- Python 3.10 was used instead of Python 3.11;
- PostgreSQL 15 was configured, but MySQL 8 was not included;
- tests were executed under `services/` rather than through
  `pytest tests/ -v`;
- no pytest coverage report was uploaded as a GitHub Actions artifact.

Therefore, the Week 8 CI/CD work extends and aligns the existing
configuration with the required PostgreSQL and MySQL test pipeline,
Python 3.11 environment, and coverage artifact reporting.


Based on the available repository history, the workflow was included in
the initial repository setup. However, the available evidence does not
clearly establish whether the configuration was intended as a final CI
setup or as an initial baseline.