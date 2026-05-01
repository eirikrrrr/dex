import click
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from crawler.database.repository import CrawlerRepository
from crawler.database.sqlite import SQLiteDatabase
from crawler.utils.cleaners.asurascans import AsuraScan

_DB_PATH = "data/crawler.db"

_PROVIDERS: dict[str, tuple[str, type]] = {
    "asurascans": ("https://asurascans.com/", AsuraScan),
}

_SERIES_EXPORT_FIELDS = [
    "id",
    "title",
    "status",
    "chapters_count",
    "rating",
    "provider",
    "detail_url",
    "image_url",
    "last_scraped_at",
]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _get_repository() -> CrawlerRepository:
    db = SQLiteDatabase(_DB_PATH)
    db.initialize()
    return CrawlerRepository(db)


def _resolve_provider(site: str) -> tuple[str, str, type]:
    provider_name = site.lower().strip()
    if provider_name not in _PROVIDERS:
        available = ", ".join(sorted(_PROVIDERS.keys()))
        raise click.ClickException(f"Unknown site '{site}'. Available: {available}")

    base_url, crawler_class = _PROVIDERS[provider_name]
    return provider_name, base_url, crawler_class


@click.group()
def dex() -> None:
    """Dex — manga scraper CLI."""


@dex.command("list")
def list_providers() -> None:
    """List all registered providers."""
    repo = _get_repository()
    providers = repo.get_all_providers()

    if not providers:
        click.echo("No providers registered yet. Run 'dex scan' first.")
        return

    click.echo(f"\n{'ID':<5} {'NAME':<20} {'BASE URL':<40} {'ACTIVE'}")
    click.echo("-" * 75)
    for p in providers:
        active = "yes" if p["is_active"] else "no"
        click.echo(f"{p['id']:<5} {p['name']:<20} {p['base_url']:<40} {active}")
    click.echo()

@dex.command("series")
@click.argument("comic_name", required=False)
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    help="List all comics in DB.",
)
@click.option(
    "--limit",
    type=click.IntRange(1),
    help="Limit rows for --all output and export.",
)
@click.option(
    "--export",
    "export_format",
    type=click.Choice(["csv", "json"], case_sensitive=False),
    help="Export listed data to file format.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False),
    help="Output file path for export. Defaults to series_export.<ext>.",
)
def series(
    comic_name: Optional[str],
    show_all: bool,
    limit: Optional[int],
    export_format: Optional[str],
    output: Optional[str],
) -> None:
    """List stored series matching COMIC_NAME."""
    repo = _get_repository()

    if show_all:
        if comic_name:
            raise click.ClickException("Do not pass COMIC_NAME when using --all.")
        items = repo.get_all_series(limit=limit)
        header_label = "all comics"
        if limit is not None:
            header_label = f"all comics (limit {limit})"
    else:
        if not comic_name:
            raise click.ClickException("Provide <NOMBRE-DEL-COMIC> or use --all.")
        normalized = comic_name.strip()
        items = repo.get_series_by_name(normalized)
        header_label = f"matching '{normalized}'"

    if not items:
        click.echo("No series found.")
        return

    click.echo(f"\nSeries {header_label} ({len(items)} total)\n")
    click.echo(f"{'ID':<6} {'TITLE':<42} {'STATUS':<12} {'CHS':<6} {'RATING':<8} {'PROVIDER':<14} {'LINK'}")
    click.echo("-" * 170)
    for s in items:
        title = (s["title"] or "")[:40]
        status = (s["status"] or "-")[:10]
        chapters = s["chapters_count"] if s["chapters_count"] is not None else "-"
        rating = s["rating"] if s["rating"] is not None else "-"
        provider = (s.get("provider") or "-")[:12]
        link = s.get("detail_url") or "-"
        click.echo(
            f"{s['id']:<6} {title:<42} {status:<12} {str(chapters):<6} "
            f"{str(rating):<8} {provider:<14} {link}"
        )
    click.echo()

    if export_format:
        normalized_export = export_format.lower().strip()
        export_path = Path(output) if output else Path(f"series_export.{normalized_export}")

        if normalized_export == "json":
            export_path.write_text(
                json.dumps(items, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        else:
            with export_path.open("w", encoding="utf-8", newline="") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=_SERIES_EXPORT_FIELDS)
                writer.writeheader()
                for row in items:
                    writer.writerow({field: row.get(field) for field in _SERIES_EXPORT_FIELDS})

        click.echo(f"Exported {len(items)} row(s) to {export_path}")

@dex.command("chapters")
@click.argument("comic_name", required=False)
@click.option(
    "--index",
    type=click.IntRange(1),
    help="Database ID of the series.",
)
def chapters(comic_name: Optional[str], index: Optional[int]) -> None:
    """List stored chapters for COMIC_NAME or by --id."""
    repo = _get_repository()
    print('RARARARARARAAAAAAAAAA')
    if index is not None:
        items = repo.get_chapters_by_series_id_global(index)
        header = f"\nChapters for series_id={index} ({len(items)} total)\n"
    else:
        if not comic_name:
            raise click.ClickException("Provide <COMIC-NAME> or use --id.")
        normalized = comic_name.strip()
        items = repo.get_chapters_by_series_name_global(normalized)
        header = f"\nChapters matching '{normalized}' ({len(items)} total)\n"

    if not items:
        click.echo("No chapters found.")
        return

    click.echo(header)
    click.echo(f"{'ID':<6} {'SERIES_ID':<10} {'SERIES':<40} {'CH#':<6} {'UPLOADED':<20} {'URL'}")
    click.echo("-" * 130)
    for c in items:
        s = (c["series_title"] or "")[:38]
        ch_num = c["chapter_number"] if c["chapter_number"] is not None else "-"
        uploaded = (c.get("published_at") or "-")[:18]
        click.echo(
            f"{c['id']:<6} {c['series_id']:<10} {s:<40} {str(ch_num):<6} "
            f"{uploaded:<20} {c['chapter_url']}"
        )
    click.echo()

@dex.command("scan")
@click.argument("site")
@click.argument("target", type=click.Choice(["series", "chapters"], case_sensitive=False))
@click.option(
    "--max-pages",
    "max_pages",
    type=click.IntRange(1, 1000),
    default=20,
    show_default=True,
    help="Maximum number of pages to scan.",
)
def scan(site: str, target: str, max_pages: int) -> None:
    """Run scanner for SITE and TARGET type (series|chapters)."""
    provider_name, base_url, crawler_class = _resolve_provider(site)
    normalized_target = target.lower().strip()

    db = SQLiteDatabase(_DB_PATH)
    db.initialize()

    click.echo(f"SCANNING  : '{provider_name}' ({base_url})")
    click.echo(f"TARGET    : {normalized_target}")
    click.echo(f"MAX_PAGES : {max_pages}")
    click.echo(f"DATETIME  : {_now()}\n")
    crawler = crawler_class(
        base_url,
        options_extra={
            "MAX_PAGES": max_pages,
        },
    )

    if normalized_target == "series":
        catalog = crawler.scrapper_series()
    else:
        if hasattr(crawler, "scrapper_chapters"):
            catalog = crawler.scrapper_chapters()
        else:
            raise click.ClickException(
                f"Chapter scan is not implemented yet for site '{provider_name}'."
            )

    if not catalog.get("detected"):
        click.echo("Browse structure not detected. The site may have changed.")
        raise SystemExit(1)

    total = catalog.get("total_items", 0)
    pages_scanned = catalog.get("pages_scanned", 0)
    sync = catalog.get("sync", {})
    inserted = sync.get("inserted", 0)
    existing = sync.get("existing", 0)

    click.echo(f"Done. {total} item(s) found in {pages_scanned} page(s).")
    click.echo(f"Inserted: {inserted} | Existing: {existing}")
    click.echo(f"Timestamp: {_now()}\n")
