import httpx
from typing import Optional


class HttpClient:
    def __init__(
        self,
        timeout: int = 10,
        headers: Optional[dict] = None,
    ) -> None:
        self.timeout = timeout
        self.headers = headers or {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }

    def get(self, url: str, params: Optional[dict] = None) -> httpx.Response:
        response = httpx.get(
            url,
            params=params,
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True,
        )
        response.raise_for_status()
        return response

    def post(self, url: str, data: Optional[dict] = None, json: Optional[dict] = None) -> httpx.Response:
        response = httpx.post(
            url,
            data=data,
            json=json,
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True,
        )
        response.raise_for_status()
        return response
