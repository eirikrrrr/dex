## Dex

![Icon](./docs/assets/images/rinnegan.png)

[![ Python ](https://img.shields.io/python/required-version-toml?tomlFilePath=https://raw.githubusercontent.com/eirikrrrr/dex/refs/heads/main/pyproject.toml)](https://raw.githubusercontent.com/eirikrrrr/dex/refs/heads/main/pyproject.toml) [![ Repo ]( https://img.shields.io/badge/github-repo-pink?logo=github)](https://github.com/eirikrrrr/dex/tree/main)


A CLI to scrape manga/manhwa/dongua data, store it in SQLite, and query it quickly.

Focused on three tasks:

- scan series/chapters

- query stored data

- export results (`csv` or `json`)

#

---

## Requirements

- Python 3.14+
- `uv`

---

## Quick setup

```bash
uv sync
uv run dex --help
```

If you want to install the command in the virtual environment:

```bash
uv pip install -e .
dex --help
```

---

## Quick usage

### 1) Scan data (series and chapters)

```bash
# Scan provider series catalog
uv run dex scan asurascans series --max-pages 2

# Scan chapters using stored series
uv run dex scan asurascans chapters --max-pages 2
```

### 2) Search series by name

```bash
uv run dex series "Solo"
```

### 3) List all stored series

```bash
# All rows
uv run dex series --all

# With limit
uv run dex series --all --limit 50
```

### 4) View chapters

```bash
# By comic name
uv run dex chapters "Sandmancer"

# By series ID in DB
uv run dex chapters --index 19
```

### 5) Export series

```bash
# Export all to CSV
uv run dex series --all --export csv --output data/series_all.csv

# Export a specific search to JSON
uv run dex series "Sandmancer" --export json --output data/series_sandmancer.json
```

---

## Available commands

```bash
uv run dex list
uv run dex scan <site> <series|chapters> [--max-pages N]
uv run dex series [COMIC_NAME] [--all] [--limit N] [--export csv|json] [--output FILE]
uv run dex chapters [COMIC_NAME] [--index N]
```

---

## Where data is stored

- SQLite DB: `data/crawler.db`
- Exports: where you point with `--output`

