import logging
import threading
import time

from services.notification_service import process_pending_notifications_for_retry


logger = logging.getLogger(__name__)
_stop_event = threading.Event()
_worker_thread = None


def _retry_interval_seconds() -> int:
    return 5 * 60


def _worker() -> None:
    logger.info("Notification scheduler worker started")
    while not _stop_event.is_set():
        try:
            process_pending_notifications_for_retry()
        except Exception as exc:
            logger.exception("Notification retry worker error=%s", exc)

        _stop_event.wait(_retry_interval_seconds())

    logger.info("Notification scheduler worker stopped")


def start_notification_scheduler() -> None:
    global _worker_thread

    if _worker_thread and _worker_thread.is_alive():
        return

    _stop_event.clear()
    _worker_thread = threading.Thread(target=_worker, name="notification-retry-worker", daemon=True)
    _worker_thread.start()
    logger.info("Notification scheduler started (interval=5 minutes)")


def stop_notification_scheduler() -> None:
    global _worker_thread

    _stop_event.set()
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=2)
    _worker_thread = None
    logger.info("Notification scheduler stopped")
