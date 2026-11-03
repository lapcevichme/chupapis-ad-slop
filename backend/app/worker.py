import asyncio
import logging
import signal
from contextlib import suppress
from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.database import Database
from app.infra.notifications import build_notifier
from app.service.outbox import OutboxDispatcher, build_handlers

logger = logging.getLogger("app.worker")

_CLEANUP_EVERY = timedelta(hours=1)
_KEEP_DEAD_SESSIONS = timedelta(days=7)


async def cleanup_sessions(db: Database) -> int:
    async with db.unit_of_work() as uow:
        return await uow.sessions.delete_stale(before=datetime.now(UTC) - _KEEP_DEAD_SESSIONS)


async def run_worker(settings: Settings) -> None:
    """
    Separate process (`python -m app.worker`), same image as the API.
    Safe to run several copies: events are claimed with SKIP LOCKED.
    """
    db = Database(settings)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    async with httpx.AsyncClient(timeout=10) as http:
        dispatcher = OutboxDispatcher(
            db,
            build_handlers(build_notifier(settings, http)),
            batch_size=settings.outbox_batch_size,
            max_attempts=settings.outbox_max_attempts,
        )
        next_cleanup = datetime.now(UTC)
        logger.info("worker started")
        while not stop.is_set():
            processed = 0
            try:
                processed = await dispatcher.run_once()
                if datetime.now(UTC) >= next_cleanup:
                    removed = await cleanup_sessions(db)
                    logger.info("removed %s stale sessions", removed)
                    next_cleanup = datetime.now(UTC) + _CLEANUP_EVERY
            except Exception:  # a DB blip must not kill the worker; log and keep polling
                logger.exception("worker iteration failed")
            if processed == 0:
                with suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=settings.outbox_poll_interval_sec)

    await db.dispose()
    logger.info("worker stopped")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    asyncio.run(run_worker(settings))


if __name__ == "__main__":
    main()
