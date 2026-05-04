from typing import Any, Optional
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
            url = self._build_url(f"/biblioteca/page/{page}/")
            response = self.client.get(url)
            if not response.ok:
                break

            html = response.text
            language = self.detect_page_language(html)
            if language:
                print(f"Detected page language: {language}")

            catalog_page = self._parse_browse_html(html)
            if not catalog_page.get("series"):
                break

            yield from catalog_page["series"]
            page += 1

    def scrapper_series(self) -> dict[str, any]:
        for i in self.get_series_endpoint():
            print(i)

        return {
                "detected": False,
                "endpoint": "/browse?page=<n>",
                "url": None,
                "items": [],
                "total_items": 0,
                "pages_scanned": 'x',
                "sync": 'x',
            }

    def scrapper_chapters(self) -> dict[str, Any]:
        pass
