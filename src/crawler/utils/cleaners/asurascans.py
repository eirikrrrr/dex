from time import sleep
from dataclasses import dataclass
from typing import Any, Iterator, Optional
import re

from selectolax.lexbor import LexborHTMLParser
from crawler.utils.base_crawler import BaseCrawler


@dataclass
class PageItem:
    series_id: str
    title: Optional[str]
    detail_path: Optional[str]
    detail_url: Optional[str]
    image_url: Optional[str]
    rating: Optional[str]
    chapters: Optional[int]
    status: Optional[str]


class AsuraScan(BaseCrawler):
    """
    Crawler implementation for https://asurascans.com

    Inherits shared infrastructure from BaseCrawler:
        - self.client, self.repository, self.options_extra
        - self._build_url(), self._parse_int()
    """

    provider_name = "asurascans"

    def __init__(self, url_base: str, options_extra: Optional[dict[str, Any]] = None) -> None:
        defaults: dict[str, Any] = {
            "MAX_PAGES": 20,
            "RATE_LIMIT": 1,
        }
        super().__init__(
            url_base=url_base,
            options_extra={**defaults, **(options_extra or {})},
        )

    def _extract_card(self, card) -> dict[str, Any]:
        primary_link = card.css_first("a[href]")
        image_node = card.css_first("img")
        title_node = card.css_first("h3")
        rating_node = card.css_first("div.absolute span")
        info_spans = card.css("div.flex.items-center.gap-2.mt-2 span")
        chapters_node = info_spans[0] if len(info_spans) > 0 else None
        status_node = card.css_first("div.flex.items-center.gap-2.mt-2 span.capitalize")
        if not status_node:
            status_node = info_spans[1] if len(info_spans) > 1 else None

        detail_path = primary_link.attributes.get("href", "") if primary_link else ""
        image_url = image_node.attributes.get("src", "") if image_node else ""
        chapters_text = chapters_node.text(strip=True) if chapters_node else ""
        status_text = status_node.text(strip=True) if status_node else ""

        return {
            "series_id": card.attributes.get("data-series-id"),
            "title": title_node.text(strip=True) if title_node else None,
            "detail_path": detail_path or None,
            "detail_url": self._build_url(detail_path) if detail_path else None,
            "image_url": image_url or None,
            "rating": rating_node.text(strip=True) if rating_node else None,
            "chapters": self._parse_int(chapters_text) if chapters_text else None,
            "status": status_text or None,
        }

    def _parse_browse_html(self, html: str) -> dict[str, Any]:
        tree = LexborHTMLParser(html)
        container = tree.css_first("#series-grid-container")
        grid = tree.css_first("#series-grid")

        if not container or not grid:
            return {
                "detected": False,
                "structure": "asurascans_series_grid_v1",
                "items": [],
                "total_items": 0,
            }

        cards = grid.css(".series-card")
        items = [self._extract_card(card) for card in cards]

        return {
            "detected": True,
            "structure": "asurascans_series_grid_v1",
            "items": items,
            "total_items": len(items),
        }

    def get_title(self) -> Optional[str]:
        """
        Fetch and return the title of the main page.
        """

        response = self.client.get(self.url_base)
        tree = LexborHTMLParser(response.text)
        title_node = tree.css_first("title")
        return title_node.text() if title_node else None

    def get_series_endpoint(self) -> Iterator[dict[str, Any]]:
        """
        Looking in: /browse?page=<INT>
        Until get all the series

        Attribute (SELF)

            self.url_base (str): The base URL of the AsuraScan website.
            self.options_extra (dict): A dictionary of extra options for the crawler, such as maximum pages to crawl and rate limits.
            self.client (HttpClient ):  An instance of the HttpClient class for making HTTP requests

        Return:
            
            dict: {
                "status": bool,
                "endpoint": str,
                "url": str,
            }
        """

        page: int = 1

        while page <= self.options_extra.get("MAX_PAGES", 20):
            
            # Build URL
            endpoint: str = f"/browse?page={page}"
            browse: str = self._build_url(endpoint)
            response = self.client.get(browse)
            
            # Parser HTML and check if the structure exists
            tree = LexborHTMLParser(response.text)
            browse_node = tree.css_first("#series-grid-container")
            if browse_node:
                yield {
                    "status": True,
                    "endpoint": endpoint,
                    "url": browse,
                    "html": response.text,
                }
            else:
                break

            rate_limit = self.options_extra.get("RATE_LIMIT", 0)
            if rate_limit:
                sleep(float(rate_limit))
            
            page += 1

    def get_chapters_endpoint(self, serie_url: str) -> Iterator[dict[str, Any]]:
        """
        Look in: /comics/<STR_ID>/chapter/<INT>
        Until get all the chapters for a series
        """
        response = self.client.get(serie_url)
        tree = LexborHTMLParser(response.text)

        chapter_links = tree.css("div.divide-y a[href*='/chapter/']")
        seen_urls: set[str] = set()

        for link in chapter_links:
            chapter_href = link.attributes.get("href", "").strip()
            if not chapter_href:
                continue

            chapter_url = self._build_url(chapter_href)
            if chapter_url in seen_urls:
                continue

            chapter_match = re.search(r"/chapter/(\d+(?:\.\d+)?)", chapter_href)
            if not chapter_match:
                continue

            seen_urls.add(chapter_url)

            number_text = chapter_match.group(1)
            chapter_number = float(number_text) if "." in number_text else int(number_text)

            chapter_title = None
            published_at = None

            title_node = link.css_first("div.flex.items-center.gap-2 span")
            if title_node:
                title_text = title_node.text(strip=True)
                if title_text and not re.match(r"^Chapter\s*\d+(?:\.\d+)?$", title_text):
                    chapter_title = title_text

            date_node = link.css_first("div.flex-shrink-0 span")
            if date_node:
                published_at = date_node.text(strip=True) or None

            chapter_path = chapter_href
            chapter_path_match = re.search(r"(/comics/.+/chapter/\d+(?:\.\d+)?)", chapter_href)
            if chapter_path_match:
                chapter_path = chapter_path_match.group(1)

            yield {
                "external_id": number_text,
                "chapter_number": chapter_number,
                "chapter_title": chapter_title,
                "chapter_url": chapter_url,
                "chapter_path": chapter_path,
                "published_at": published_at,
            }



    def scrapper_series(self) -> dict[str, Any]:
        detected = False
        total_items = 0
        pages_scanned = 0
        sync_summary = {"processed": 0, "inserted": 0, "existing": 0}

        for browse_data in self.get_series_endpoint():
            pages_scanned += 1
            live_page_scanned = pages_scanned
            print(f"\nScanning page {live_page_scanned}\n")
            parsed = self._parse_browse_html(browse_data["html"])
            if not parsed.get("detected"):
                continue

            detected = True
            page_items: list[dict[str, Any]] = parsed.get("items", [])
            total_items += len(page_items)

            if page_items:
                page_sync = self.repository.sync_catalog(
                    provider_name=self.provider_name,
                    base_url=self.url_base,
                    items=page_items,
                )
                sync_summary["processed"] += page_sync.get("processed", 0)
                sync_summary["inserted"] += page_sync.get("inserted", 0)
                sync_summary["existing"] += page_sync.get("existing", 0)


        if not detected:
            return {
                "detected": False,
                "endpoint": "/browse?page=<n>",
                "url": None,
                "items": [],
                "total_items": 0,
                "pages_scanned": pages_scanned,
                "sync": sync_summary,
            }

        return {
            "detected": True,
            "endpoint": "/browse?page=<n>",
            "url": self._build_url("/browse"),
            "items": [],
            "total_items": total_items,
            "pages_scanned": pages_scanned,
            "structure": "asurascans_series_grid_v1",
            "sync": sync_summary,
        }

    def scrapper_chapters(self) -> dict[str, Any]:
        series_targets = self.repository.get_series_scan_targets(self.provider_name)
        max_series = int(self.options_extra.get("MAX_PAGES", 0) or 0)
        if max_series > 0:
            series_targets = series_targets[:max_series]

        if not series_targets:
            return {
                "detected": False,
                "endpoint": "/comics/<series-slug>",
                "url": None,
                "items": [],
                "total_items": 0,
                "pages_scanned": 0,
                "sync": {"processed": 0, "inserted": 0, "existing": 0},
            }

        sync_summary = {"processed": 0, "inserted": 0, "existing": 0}
        series_scanned = 0
        total_items = 0

        for target in series_targets:
            series_scanned += 1
            series_url = target.get("detail_url")
            series_db_id = target.get("id")
            series_title = target.get("title")

            if not series_url or series_db_id is None:
                continue

            print(f"\nScanning chapters for: {series_title}")
            chapter_items = list(self.get_chapters_endpoint(series_url))
            total_items += len(chapter_items)
            if chapter_items:
                summary = self.repository.sync_chapters(
                    provider_name=self.provider_name,
                    base_url=self.url_base,
                    series_id=int(series_db_id),
                    items=chapter_items,
                )
                sync_summary["processed"] += summary.get("processed", 0)
                sync_summary["inserted"] += summary.get("inserted", 0)
                sync_summary["existing"] += summary.get("existing", 0)

            rate_limit = self.options_extra.get("RATE_LIMIT", 0)
            if rate_limit:
                sleep(float(rate_limit))

        return {
            "detected": True,
            "endpoint": "/comics/<series-slug>",
            "url": self._build_url("/comics"),
            "items": [],
            "total_items": total_items,
            "pages_scanned": series_scanned,
            "sync": sync_summary,
        }


