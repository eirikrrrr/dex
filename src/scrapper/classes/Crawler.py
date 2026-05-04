"""Abstract base class for all site-specific crawlers."""

import re
from abc import ABC, abstractmethod
from typing import Any, Optional
from urllib.parse import urljoin

from database.repository import CrawlerRepository
from database.sqlite import SQLiteDatabase
from scrapper.classes.HttpClient import HttpClient


class BaseCrawler(ABC):
    """
    Blueprint for all crawler implementations.

    Subclasses must implement:
        - provider_name (str): Unique name for this provider.
        - get_title() -> Optional[str]
        - get_browse_endpoint() -> Iterator[dict[str, Any]]
        - _extract_card(card) -> dict[str, Any]
        - _parse_browse_html(html) -> dict[str, Any]
        - get_catalog_via_scrapper(content_type) -> dict[str, Any]

    Shared infrastructure (ready to use in subclasses):
        - self.client          — HttpClient instance
        - self.repository      — CrawlerRepository instance
        - self.options_extra   — runtime options dict
        - self._build_url()    — urljoin helper
        - self._parse_int()    — regex int extractor
        - self.detect_page_language() — extract <html lang="...">
    """

    provider_name: str

    def __init__(
        self,
        url_base: str,
        db_path: str = "data/crawler.db",
        options_extra: Optional[dict[str, Any]] = None,
    ) -> None:
        self.url_base = url_base
        self.client = HttpClient()
        self.repository = CrawlerRepository(SQLiteDatabase(db_path))
        self.options_extra: dict[str, Any] = options_extra or {}

    # ------------------------------------------------------------------ #
    # Shared helpers — available to all subclasses, no override needed    #
    # ------------------------------------------------------------------ #

    def _build_url(self, path: str) -> str:
        return urljoin(self.url_base, path)

    def _parse_int(self, text: str) -> Optional[int]:
        match = re.search(r"\d+", text)
        return int(match.group(0)) if match else None

    def detect_page_language(self, html: str) -> Optional[str]:
        # Accepts both quoted and unquoted lang attributes in the html tag.
        quoted_match = re.search(
            r"<html\b[^>]*\blang\s*=\s*(['\"])([^'\"]+)\1",
            html,
            flags=re.IGNORECASE,
        )
        if quoted_match:
            language = quoted_match.group(2).strip().lower()
            return language or None

        unquoted_match = re.search(
            r"<html\b[^>]*\blang\s*=\s*([^\s>]+)",
            html,
            flags=re.IGNORECASE,
        )
        if unquoted_match:
            language = unquoted_match.group(1).strip().lower().strip("\"'")
            return language or None

        return None

    # ------------------------------------------------------------------ #
    # Abstract interface — every subclass MUST implement these            #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def scrapper_series(self) -> dict[str, Any]:
        """
        Iterate all browse pages, sync to DB, and return a run summary.

        Expected keys:
            detected (bool), total_items (int), pages_scanned (int),
            sync (dict with 'processed', 'inserted', 'existing' counts)
        """

    @abstractmethod
    def scrapper_chapters(self) -> dict[str, Any]:
        """
        Optional: If the site has a separate chapter listing, implement this.

        Expected keys:
            detected (bool), total_items (int), pages_scanned (int),
            sync (dict with 'processed', 'inserted', 'existing' counts)
        """
        



