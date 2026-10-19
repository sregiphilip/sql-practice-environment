# SQL practice environment

A local PostgreSQL workbook with a synthetic dataset, built to write and test the SQL for a take-home analytics exercise (Exercise 2, SQL and Data Analysis). The assessment's own tables weren't available, so this dataset reproduces their schema, row counts and sample rows, and every query was run against it rather than written blind.

The synthetic dataset and this environment were generated with the help of Claude (AI).

**Live version:** https://sregiphilip.github.io/sql-practice-environment/

## What's in the workbook

- **The exercise questions**, one tab per sub-question (1a, 1b, 1c, 2a, 2b, 2c, 3, 4), with the full question text above each query.
- **The tables** with their columns, types and row counts in the sidebar. Click a table name to preview it.
- **A SQL editor** that runs real PostgreSQL 17 ([PGlite](https://github.com/electric-sql/pglite)) in the browser.
- **Check my answer**, which says whether a query's result matches the expected result, or matches a defensible alternative definition of the metric. It doesn't show the answer. The page only holds salted fingerprints of the expected results (`check_data.json`), not the results or the reference queries.
- **Auto-save** when run locally. Every query and its latest result are saved to `my_answers.md` and `my_answers.json`, and earlier versions are kept in `history/`. On the live version, queries are kept in your browser instead.

## Tables

| Table | Rows | Columns |
|---|---|---|
| `applications` | 10,000 | `app_id`, `business_id`, `created_at`, `status`, `verified_at` |
| `merchants` | 600 | `merchant_id`, `business_name`, `risk_level`, `account_manager` |
| `transactions` | 50,000 | `txn_id`, `merchant_id`, `amount`, `processed_at`, `requires_review` |

About the data:

- It has no missing values, duplicate rows or inconsistent labels.
- `verified_at` is filled only when `status = 'Verified'`. Statuses are Verified, Pending, In Review and Rejected.
- Each business onboards once. Some rejected businesses re-applied within the same month, so a business can have more than one application.
- Data covers October 2025 to June 2026 and is generated with a fixed random seed, so it is reproducible.

## Run it locally

Requires Python 3 and an internet connection (PostgreSQL loads in the browser from cdn.jsdelivr.net).

```bash
python3 serve.py
```

Then open http://localhost:8765/. Pick a question tab, write SQL, run it (⌘/Ctrl + Enter) and use **Check my answer**.

To regenerate the dataset and rebuild the page:

```bash
python3 generate_data.py
```

## Files

| File | What it is |
|---|---|
| `index.html` | The workbook, with the dataset and answer fingerprints embedded (built from `workbook_template.html`) |
| `serve.py` | Local server that serves the workbook and auto-saves queries to disk |
| `generate_data.py` | Seeded generator for the three CSVs in `data/`, and the build step for `index.html` |
| `check_data.json` | Salted fingerprints of the expected results, used by Check my answer |
