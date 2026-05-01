"""Repository layer for SQLite persistence of providers and series."""

from __future__ import annotations

import json
from typing import Any, Optional

from crawler.database.sqlite import SQLiteDatabase


class CrawlerRepository:
    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def get_or_create_provider(self, name: str, base_url: str) -> int:
        with self.db.connect() as connection:
            row = connection.execute(
                "SELECT id FROM providers WHERE name = ?",
                (name,),
            ).fetchone()
            if row:
                return int(row["id"])

            cursor = connection.execute(
                """
                INSERT INTO providers (name, base_url)
                VALUES (?, ?)
                """,
                (name, base_url),
            )
            connection.commit()
            if cursor.lastrowid is None:
                raise RuntimeError("Provider insert failed: no row id returned")
            return int(cursor.lastrowid)

    def series_exists(
        self,
        provider_id: int,
        external_id: str | None,
        detail_url: str | None,
    ) -> int | None:
        with self.db.connect() as connection:
            if external_id:
                row = connection.execute(
                    """
                    SELECT id
                    FROM series
                    WHERE provider_id = ? AND external_id = ?
                    """,
                    (provider_id, external_id),
                ).fetchone()
                if row:
                    return int(row["id"])

            if detail_url:
                row = connection.execute(
                    """
                    SELECT id
                    FROM series
                    WHERE provider_id = ? AND detail_url = ?
                    """,
                    (provider_id, detail_url),
                ).fetchone()
                if row:
                    return int(row["id"])

        return None

    def insert_series(
        self,
        provider_id: int,
        provider_name: str,
        item: dict[str, Any],
    ) -> int:
        metadata = {
            "source": "browse",
            "raw": item,
        }

        with self.db.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO series (
                    provider_id,
                    provider,
                    external_id,
                    slug,
                    title,
                    status,
                    chapters_count,
                    rating,
                    detail_path,
                    detail_url,
                    image_url,
                    metadata_json,
                    last_scraped_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    provider_id,
                    provider_name,
                    item.get("series_id"),
                    self._slug_from_path(item.get("detail_path")),
                    item.get("title"),
                    item.get("status"),
                    item.get("chapters"),
                    self._to_float(item.get("rating")),
                    item.get("detail_path"),
                    item.get("detail_url"),
                    item.get("image_url"),
                    json.dumps(metadata, ensure_ascii=True),
                ),
            )
            connection.commit()
            if cursor.lastrowid is None:
                raise RuntimeError("Series insert failed: no row id returned")
            return int(cursor.lastrowid)

    def ensure_series(
        self,
        provider_name: str,
        base_url: str,
        item: dict[str, Any],
    ) -> dict[str, Any]:
        provider_id = self.get_or_create_provider(provider_name, base_url)
        existing_id = self.series_exists(
            provider_id=provider_id,
            external_id=item.get("series_id"),
            detail_url=item.get("detail_url"),
        )

        if existing_id is not None:
            return {
                "inserted": False,
                "series_db_id": existing_id,
                "provider_id": provider_id,
            }

        new_id = self.insert_series(provider_id, provider_name, item)
        return {
            "inserted": True,
            "series_db_id": new_id,
            "provider_id": provider_id,
        }

    def sync_catalog(
        self,
        provider_name: str,
        base_url: str,
        items: list[dict[str, Any]],
    ) -> dict[str, int]:
        summary = {
            "processed": 0,
            "inserted": 0,
            "existing": 0,
        }

        for item in items:
            detail_url = item.get("detail_url")
            title = item.get("title")
            if not detail_url or not title:
                continue

            result = self.ensure_series(provider_name, base_url, item)
            summary["processed"] += 1
            if result["inserted"]:
                print("✨ New Found: ", item.get("title"))
                summary["inserted"] += 1
            else:
                print("✅ Existing: ", item.get("title"))
                summary["existing"] += 1

        return summary

    def get_all_providers(self) -> list[dict[str, Any]]:
        with self.db.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, base_url, is_active, created_at FROM providers ORDER BY name"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_series_by_provider(self, provider_name: str) -> list[dict[str, Any]]:
        with self.db.connect() as connection:
            rows = connection.execute(
                """
                SELECT s.id, s.title, s.status, s.chapters_count, s.rating,
                       s.detail_url, s.image_url, s.last_scraped_at
                FROM series s
                JOIN providers p ON p.id = s.provider_id
                WHERE p.name = ?
                ORDER BY s.title
                """,
                (provider_name,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_series_by_name(self, series_name: str) -> list[dict[str, Any]]:
        with self.db.connect() as connection:
            rows = connection.execute(
                """
                SELECT s.id, s.title, s.status, s.chapters_count, s.rating,
                       s.detail_url, s.image_url, s.last_scraped_at, p.name AS provider
                FROM series s
                JOIN providers p ON p.id = s.provider_id
                WHERE LOWER(s.title) LIKE LOWER(?)
                ORDER BY s.title
                """,
                (f"%{series_name}%",),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_all_series(self, limit: Optional[int] = None) -> list[dict[str, Any]]:
        with self.db.connect() as connection:
            if limit is None:
                rows = connection.execute(
                    """
                    SELECT s.id, s.title, s.status, s.chapters_count, s.rating,
                           s.detail_url, s.image_url, s.last_scraped_at, p.name AS provider
                    FROM series s
                    JOIN providers p ON p.id = s.provider_id
                    ORDER BY s.id
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT s.id, s.title, s.status, s.chapters_count, s.rating,
                           s.detail_url, s.image_url, s.last_scraped_at, p.name AS provider
                    FROM series s
                    JOIN providers p ON p.id = s.provider_id
                    ORDER BY s.id
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [dict(row) for row in rows]

    def get_series_scan_targets(self, provider_name: str) -> list[dict[str, Any]]:
        with self.db.connect() as connection:
            rows = connection.execute(
                """
                SELECT s.id, s.title, s.detail_url
                FROM series s
                JOIN providers p ON p.id = s.provider_id
                WHERE p.name = ? AND s.detail_url IS NOT NULL
                ORDER BY s.id
                """,
                (provider_name,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_chapters_by_provider(self, provider_name: str) -> list[dict[str, Any]]:
        with self.db.connect() as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.chapter_number, c.chapter_title, c.chapter_url,
                       s.title AS series_title, c.published_at, c.is_available
                FROM chapters c
                JOIN series s ON s.id = c.series_id
                JOIN providers p ON p.id = c.provider_id
                WHERE p.name = ?
                ORDER BY s.title, c.chapter_number
                """,
                (provider_name,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_chapters_by_series_id(
        self,
        provider_name: str,
        series_id: int,
    ) -> list[dict[str, Any]]:
        with self.db.connect() as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.chapter_number, c.chapter_title, c.chapter_url,
                       s.id AS series_id, s.title AS series_title, c.published_at, c.is_available
                FROM chapters c
                JOIN series s ON s.id = c.series_id
                JOIN providers p ON p.id = c.provider_id
                WHERE p.name = ? AND s.id = ?
                ORDER BY c.chapter_number
                """,
                (provider_name, series_id),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_chapters_by_series_name(
        self,
        provider_name: str,
        series_name: str,
    ) -> list[dict[str, Any]]:
        with self.db.connect() as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.chapter_number, c.chapter_title, c.chapter_url,
                       s.id AS series_id, s.title AS series_title, c.published_at, c.is_available
                FROM chapters c
                JOIN series s ON s.id = c.series_id
                JOIN providers p ON p.id = c.provider_id
                WHERE p.name = ? AND LOWER(s.title) LIKE LOWER(?)
                ORDER BY s.title, c.chapter_number
                """,
                (provider_name, f"%{series_name}%"),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_chapters_by_series_id_global(self, series_id: int) -> list[dict[str, Any]]:
        with self.db.connect() as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.chapter_number, c.chapter_title, c.chapter_url,
                       s.id AS series_id, s.title AS series_title, c.published_at, c.is_available
                FROM chapters c
                JOIN series s ON s.id = c.series_id
                WHERE s.id = ?
                ORDER BY c.chapter_number
                """,
                (series_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_chapters_by_series_name_global(self, series_name: str) -> list[dict[str, Any]]:
        with self.db.connect() as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.chapter_number, c.chapter_title, c.chapter_url,
                       s.id AS series_id, s.title AS series_title, c.published_at, c.is_available
                FROM chapters c
                JOIN series s ON s.id = c.series_id
                WHERE LOWER(s.title) LIKE LOWER(?)
                ORDER BY s.title, c.chapter_number
                """,
                (f"%{series_name}%",),
            ).fetchall()
            return [dict(row) for row in rows]

    def chapter_exists(self, series_id: int, chapter_url: str | None) -> int | None:
        if not chapter_url:
            return None

        with self.db.connect() as connection:
            row = connection.execute(
                """
                SELECT id
                FROM chapters
                WHERE series_id = ? AND chapter_url = ?
                """,
                (series_id, chapter_url),
            ).fetchone()
            if row:
                return int(row["id"])
        return None

    def insert_chapter(
        self,
        provider_id: int,
        provider_name: str,
        series_id: int,
        item: dict[str, Any],
    ) -> int:
        metadata = {
            "source": "chapter-list",
            "raw": item,
        }

        with self.db.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO chapters (
                    series_id,
                    provider_id,
                    provider,
                    external_id,
                    chapter_number,
                    chapter_title,
                    chapter_url,
                    chapter_path,
                    published_at,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    series_id,
                    provider_id,
                    provider_name,
                    item.get("external_id"),
                    item.get("chapter_number"),
                    item.get("chapter_title"),
                    item.get("chapter_url"),
                    item.get("chapter_path"),
                    item.get("published_at"),
                    json.dumps(metadata, ensure_ascii=True),
                ),
            )
            connection.commit()
            if cursor.lastrowid is None:
                raise RuntimeError("Chapter insert failed: no row id returned")
            return int(cursor.lastrowid)

    def update_existing_chapter(self, chapter_id: int, item: dict[str, Any]) -> None:
        metadata = {
            "source": "chapter-list",
            "raw": item,
        }

        parsed_title = item.get("chapter_title")
        parsed_published_at = item.get("published_at")

        with self.db.connect() as connection:
            connection.execute(
                """
                UPDATE chapters
                SET
                    chapter_title = CASE
                        WHEN ? IS NOT NULL THEN ?
                        WHEN ? IS NULL AND chapter_title GLOB 'Chapter*' THEN NULL
                        WHEN chapter_title = ? THEN NULL
                        ELSE chapter_title
                    END,
                    chapter_number = COALESCE(?, chapter_number),
                    chapter_path = COALESCE(?, chapter_path),
                    published_at = COALESCE(?, published_at),
                    metadata_json = ?
                WHERE id = ?
                """,
                (
                    parsed_title,
                    parsed_title,
                    parsed_title,
                    parsed_published_at,
                    item.get("chapter_number"),
                    item.get("chapter_path"),
                    parsed_published_at,
                    json.dumps(metadata, ensure_ascii=True),
                    chapter_id,
                ),
            )
            connection.commit()

    def ensure_chapter(
        self,
        provider_name: str,
        base_url: str,
        series_id: int,
        item: dict[str, Any],
    ) -> dict[str, Any]:
        provider_id = self.get_or_create_provider(provider_name, base_url)
        existing_id = self.chapter_exists(series_id=series_id, chapter_url=item.get("chapter_url"))

        if existing_id is not None:
            self.update_existing_chapter(existing_id, item)
            return {
                "inserted": False,
                "chapter_db_id": existing_id,
                "provider_id": provider_id,
            }

        new_id = self.insert_chapter(provider_id, provider_name, series_id, item)
        return {
            "inserted": True,
            "chapter_db_id": new_id,
            "provider_id": provider_id,
        }

    def sync_chapters(
        self,
        provider_name: str,
        base_url: str,
        series_id: int,
        items: list[dict[str, Any]],
    ) -> dict[str, int]:
        summary = {
            "processed": 0,
            "inserted": 0,
            "existing": 0,
        }

        for item in items:
            chapter_url = item.get("chapter_url")
            if not chapter_url:
                continue

            result = self.ensure_chapter(
                provider_name=provider_name,
                base_url=base_url,
                series_id=series_id,
                item=item,
            )
            summary["processed"] += 1
            if result["inserted"]:
                summary["inserted"] += 1
            else:
                summary["existing"] += 1

        return summary

    def _slug_from_path(self, detail_path: str | None) -> str | None:
        if not detail_path:
            return None

        parts = [part for part in detail_path.strip("/").split("/") if part]
        return parts[-1] if parts else None

    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
