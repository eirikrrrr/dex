from time import sleep
from pydoc import html
from turtle import title
from typing import Any, Optional

from selectolax.lexbor import LexborHTMLParser
from scrapper.classes.Crawler import BaseCrawler


class visorIkigai(BaseCrawler):
    """
    Crawler implementation for VisorIkigai (https://visorikigai.yomod.xyz/).

    Inherits shared infrastructure from BaseCrawler:
        - self.client          — HttpClient instance
        - self.repository      — CrawlerRepository instance
        - self.options_extra   — runtime options dict
        - self._build_url()    — urljoin helper
        - self._parse_int()    — regex int extractor
        - self.detect_page_language() — extract <html lang="...">
    """

    provider_name: str = "visorikigai"

    def __init__(self, base_url: str, db_path: str = "data/crawler.db", options_extra: Optional[dict[str, Any]] = None) -> None:
        defaults = {
            "MAX_PAGES": 20,
            "RATE_LIMIT": 1,  # seconds between requests
        }
        super().__init__(base_url, db_path, options_extra = {**defaults, **(options_extra or {})})

    def _extract_card(self, li_item_card):
        """
        Implementation for extracting card data from the series listing page. The HTML structure is assumed to be as follows:
        <li>
          <a href="/series/123">
            <img src="cover.jpg" />
            <h3>Series Title</h3>
            <ul class="flex flex-wrap gap-1">
              <li>Genre1</li>
              <li>Genre2</li>
            </ul>
            <li q:key="Capítulos"><span>10</span></li>
            <li q:key="Estado"><span>Ongoing</span></li>
          </a>
        </li>

        Returns a dict with the following keys
        data: dict = {
            "name": str,
            "url": Optional[str],
            "path": Optional[str],
            "image_url": Optional[str],
            "genres": list[str],
            "chapters": Optional[int],
            "status": Optional[str],
        }

        """

        a_parent = li_item_card.css_first("a")
        print(a_parent)
        if not a_parent:
            return {}
        
        primary_path = a_parent.attributes.get("href")
        url = self._build_url(primary_path) if primary_path else None
        img = a_parent.css_first("img")
        image_url = img.attributes.get("src") if img else None
        h3 = a_parent.css_first("h3")
        name = h3.text(strip=True) if h3 else title
        
        genres_ul = a_parent.css_first("ul.flex.flex-wrap.gap-1")
        genres = []
        if genres_ul:
            genres = [
                li.text(strip=True)
                for li in genres_ul.css("li")
            ]

        chapters_li = a_parent.css_first('li[q\\:key="Capítulos"]')
        chapters = None
        if chapters_li:
            spans = chapters_li.css("span")
            for span in spans:
                text = span.text(strip=True)
                if text.isdigit():
                    chapters = int(text)
                    break
        
        status_li = a_parent.css_first('li[q\\:key="Estado"]')
        status = None
        if status_li:
            spans = status_li.css("span")
            for span in spans:
                text = span.text(strip=True)
                if text and text != "Estado":
                    status = text
                    break

        return {
            "series_id": None,
            "title": name,
            "detail_path": primary_path,
            "detail_url": url,
            "image_url": image_url,
            "rating": None,
            "chapters": chapters,
            "status": status,
            "genres": genres,
        }

    def _parse_html_series_endpoint(self, html) -> dict[str, Any]:
        page_language: str = self.detect_page_language(html)
        tree = LexborHTMLParser(html)
        section = tree.css_first("section.container", default="not-found-ul", strict=True) 
        
        if not section:
            return {
                "detected": False,
                "endpoint": "/series/?pagina=<n>",
                "page_language": page_language,
                "items": [],
                "total_items": 0,
            }
        
        sub_container_with_series_card = section.css_first("ul.grid")
        items: list[dict[str, Any]] = [self._extract_card(li_item_card) for li_item_card in sub_container_with_series_card.css("li")]

        return {
            "detected": True,
            "structure": "ikigai_series_grid_v1",
            "page_language": page_language,
            "items": items,
            "total_items": len(items),
        }

    def get_series_endpoint(self) -> dict[str, any]:
        """
        URL base:   "https://visorikigai.yomod.xyz/series/"
        Looking in: /capitulo/<ID>/
        
        Attributes (self):
            - self.url_base
            - self.client
            - self.options_extra

        """

        page: int = 1

        while page <= self.options_extra.get("MAX_PAGES", 20):
            
            # Build URL
            endpoint = self._build_url(f"/series/?pagina={page}")
            response = self.client.get(endpoint)
            if response.status_code != 200:
                break

            # Parser HTML and check if the structure exists
            tree = LexborHTMLParser(response.text)
            series = tree.css_first("section.container", default="not-found-ul", strict=True)
            if series:
                yield {
                    "status": True,
                    "endpoint": endpoint,
                    "url": series,
                    "html": response.text,
                }
            else:
                break
            rate_limit = self.options_extra.get("RATE_LIMIT", 1)
            if rate_limit > 0:
                sleep(float(rate_limit))

            page += 1

    def scrapper_series(self) -> dict[str, any]:

        detected = False
        total_items: int = 0 
        pages_scanned: int = 0
        sync_summary: dict = {
            "proccesed": 0,
            "inserted": 0,
            "existing": 0,
        }

        for page_data in self.get_series_endpoint():
            pages_scanned += 1
            parsed = self._parse_html_series_endpoint(page_data["html"])
            if not parsed["detected"]:
                continue
            
            detected = True
            page_items: list[dict[str, Any]] = parsed.get("items", [])
            page_language: Optional[str] = parsed.get("page_language")
            if page_language:
                for item in page_items:
                    item["language"] = page_language
            total_items += len(page_items)

            if page_items:
                page_sync = self.repository.sync_catalog(
                    provider_name = self.provider_name,
                    base_url = self.url_base,
                    items = page_items,
                )
                sync_summary["processed"] += page_sync.get("processed", 0)
                sync_summary["inserted"] += page_sync.get("inserted", 0)
                sync_summary["existing"] += page_sync.get("existing", 0)

        if not detected:
            return {
                "detected": False,
                "endpoint": "/series/?pagina=<n>",
                "url": None,
                "items": [],
                "total_items": 0,
                "pages_scanned": 'x',
                "sync": 'x',
            }
        
        return {
            "detected": True,
            "endpoint": "/series/?pagina=<n>",
            "url": self._build_url("/series/"),
            "items": [],
            "total_items": total_items,
            "pages_scanned": pages_scanned,
            "structure": "visorikigai_series_grid_v1",
            "sync": sync_summary,
        }

    def scrapper_chapters(self) -> dict[str, Any]:
        pass
