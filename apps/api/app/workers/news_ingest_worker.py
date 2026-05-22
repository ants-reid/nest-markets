"""API-W05 — NewsIngestWorker: ingest recent news articles into the DB.

This is a scaffold implementation. When a real news client is configured it
will persist NewsArticle rows; until then it is a controlled no-op.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.clients.news.news_client import NewsClient, get_news_client
from app.db.models.news_article import NewsArticle
from app.workers.async_bridge import run_async
from app.workers.base_worker import BaseWorker, WorkerResult

_logger = logging.getLogger(__name__)


@dataclass
class NewsIngestResult:
    message: str
    ingested: int = 0
    skipped: int = 0


class NewsIngestWorker(BaseWorker):
    """Fetches news articles for all watched tickers and persists new rows."""

    worker_name = "news_ingest"

    def __init__(
        self,
        client: NewsClient | None = None,
        session: Session | None = None,
    ) -> None:
        self._client = client or get_news_client()
        self._session = session

    async def execute(self, session: Session) -> NewsIngestResult:
        """Fetch and persist news articles.

        Args:
            session: SQLAlchemy session (injected by the scheduler runner).

        Returns:
            NewsIngestResult describing what was done.
        """
        from app.db.models.asset import Asset
        from sqlalchemy import select

        assets = session.execute(
            select(Asset).where(Asset.is_active.is_(True))
        ).scalars().all()

        if not assets:
            return NewsIngestResult(message="no active assets — skipped", ingested=0)

        lookback = datetime.now(timezone.utc) - timedelta(days=1)
        ingested = 0
        skipped = 0

        for asset in assets:
            items = await self._client.get_articles(
                asset.ticker,
                from_date=lookback,
                limit=50,
            )
            for item in items:
                # Deduplicate on provider_article_id if present
                if item.provider_article_id:
                    existing = session.execute(
                        select(NewsArticle).where(
                            NewsArticle.provider_article_id == item.provider_article_id
                        )
                    ).scalar_one_or_none()
                    if existing:
                        skipped += 1
                        continue

                row = NewsArticle(
                    provider_article_id=item.provider_article_id,
                    published_at=item.published_at,
                    headline=item.headline,
                    summary=item.summary,
                    body_text=item.body_text,
                    source_name=item.source_name,
                    url=item.url,
                    authors_json=item.authors or None,
                    tickers_json=item.tickers or None,
                    sector_tags_json=item.sector_tags or None,
                    raw_json=item.raw,
                )
                session.add(row)
                ingested += 1

        if ingested:
            session.commit()

        return NewsIngestResult(
            message=f"news_ingest: {ingested} ingested, {skipped} skipped",
            ingested=ingested,
            skipped=skipped,
        )

    def run(self) -> WorkerResult:
        """Entry point used by scheduler (creates its own session)."""
        from app.db.session import SessionLocal

        session = SessionLocal()
        started_at = datetime.now(timezone.utc)
        try:
            result = run_async(lambda: self.execute(session))
            finished_at = datetime.now(timezone.utc)
            return WorkerResult(
                worker_name=self.worker_name,
                status="ok",
                started_at=started_at,
                finished_at=finished_at,
                message=result.message,
            )
        except Exception as exc:
            session.rollback()
            _logger.error("NewsIngestWorker failed: %s", exc)
            finished_at = datetime.now(timezone.utc)
            return WorkerResult(
                worker_name=self.worker_name,
                status="error",
                started_at=started_at,
                finished_at=finished_at,
                message=f"error: {exc}",
            )
        finally:
            session.close()
