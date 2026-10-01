# Spec 01 — Project setup

## Goal
A clean, installable Python project skeleton with git, ready for the data pipeline.

## Tasks
1. `git init` (if not already a repo). Default branch `main`.
2. Create a virtualenv in `.venv` and a `pyproject.toml` with:
   - package name `evgap`, `src/` layout
   - dependencies: pandas, geopandas, shapely, pyarrow, requests, python-dotenv, streamlit, pydeck, matplotlib
   - dev dependencies: pytest, ruff
3. Install the package in editable mode (`pip install -e ".[dev]"`).
4. Create the folder structure:
```
src/evgap/__init__.py
src/evgap/config.py
src/evgap/fetch.py        (stub with a main() that prints "todo")
src/evgap/build.py        (stub)
src/evgap/charts.py       (stub)
app/streamlit_app.py      (stub that shows a title)
tests/__init__.py
data/raw/.gitkeep
data/processed/.gitkeep
charts/.gitkeep
```
5. `config.py` must contain:
   - `ROOT`, `RAW_DIR`, `PROCESSED_DIR`, `CHARTS_DIR` (pathlib, relative to repo root)
   - `BAY_AREA_COUNTIES`: dict of county name → 5-digit FIPS (see CLAUDE.md)
   - `MIN_EVS_FOR_RANKING = 200`
   - `DMV_LATEST_LABEL = "1/1/2026"` and `DMV_BASELINE_LABEL = "1/1/2024"`
6. `.gitignore`: `.venv/`, `.env`, `__pycache__/`, `data/raw/*` (keep `.gitkeep`), `data/processed/*` except `zip_metrics.csv` and `.gitkeep`, `.streamlit/secrets.toml`.
7. `.env.example` with `NREL_API_KEY=DEMO_KEY`.
8. MIT `LICENSE` with the user's name: Puraav Ghuwalewala.
9. Placeholder `README.md` with just the project title and one-line question.
10. Make `python -m evgap.fetch`, `python -m evgap.build`, `python -m evgap.charts` runnable (each module has `if __name__ == "__main__": main()`).

## Done when
- `pip install -e ".[dev]"` succeeds
- `python -m evgap.fetch` prints `todo` without errors
- `ruff check .` passes
- `pytest -q` runs (0 tests is fine)
- `git status` is clean after the commit `step 01: project setup`
