import logging
import os
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, Optional

from bson import ObjectId

from models.db import complaints_collection, images_collection, notifications_collection, officers_collection, users_collection
from services.image_loader import load_image_bytes, guess_mime_type


logger = logging.getLogger(__name__)


class NotificationServiceError(Exception):
    pass


def _retry_interval_minutes() -> int:
    value = os.getenv("NOTIFICATION_RETRY_MINUTES", "5").strip()
    try:    
        return max(1, int(value))
    except Exception:
        return 5


def _accept_base_url() -> str:
    return os.getenv("ACCEPT_BASE_URL", "http://localhost:8000").rstrip("/")


def _smtp_settings() -> Dict[str, Any]:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL") or username

    if not host or not username or not password or not from_email:
        raise NotificationServiceError(
            "SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM_EMAIL are required"
        )

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "from_email": from_email,
    }


def _to_object_id(value: Any) -> Optional[ObjectId]:
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except Exception:
        return None


def _find_officer(officer_id: str) -> Optional[Dict[str, Any]]:
    oid = _to_object_id(officer_id)
    if oid:
        officer = officers_collection.find_one({"_id": oid})
        if officer:
            return officer
    return officers_collection.find_one({"_id": officer_id})


def _find_user(user_id: Any) -> Optional[Dict[str, Any]]:
    oid = _to_object_id(user_id)
    if oid:
        user = users_collection.find_one({"_id": oid})
        if user:
            return user
    return users_collection.find_one({"_id": user_id})


def _officer_email(officer_id: str) -> str:
    officer = _find_officer(officer_id)
    if not officer:
        raise NotificationServiceError(f"Officer not found for id={officer_id}")

    user = _find_user(officer.get("user_id"))
    if not user or not user.get("email"):
        raise NotificationServiceError(f"Officer user/email not found for officer_id={officer_id}")

    return user["email"]


def _compose_email(
    complaint: Dict[str, Any],
    to_email: str,
    image_path: Optional[str],
) -> EmailMessage:
    location = complaint.get("location", {})
    lat = location.get("lat")
    lon = location.get("lon")
    complaint_id = complaint.get("complaint_id")
    issue_type = complaint.get("issue_type")
    description = complaint.get("description")
    reported_by = complaint.get("reported_by")
    if not reported_by:
        reporter = _find_user(complaint.get("user_id"))
        reported_by = reporter.get("name") if reporter else None

    map_link = f"https://www.google.com/maps?q={lat},{lon}"
    accept_link = f"{_accept_base_url()}/complaint/{complaint_id}/accept"

    msg = EmailMessage()
    msg["Subject"] = f"New Complaint Assignment - {complaint_id}"
    msg["To"] = to_email
    msg["From"] = _smtp_settings()["from_email"]

    plain_text = (
        f"Complaint ID: {complaint_id}\n"
        f"Reported By: {reported_by or 'Unknown'}\n"
        f"Issue Type: {issue_type}\n"
        f"Description: {description}\n"
        f"Latitude: {lat}\n"
        f"Longitude: {lon}\n"
        f"Map Link: {map_link}\n"
        f"Accept Complaint: {accept_link}\n"
    )

    html = f"""
    <html>
      <body>
        <h3>New Complaint Assigned</h3>
        <p><b>Complaint ID:</b> {complaint_id}</p>
        <p><b>Reported By:</b> {reported_by or 'Unknown'}</p>
        <p><b>Issue Type:</b> {issue_type}</p>
        <p><b>Description:</b> {description}</p>
        <p><b>Latitude:</b> {lat}</p>
        <p><b>Longitude:</b> {lon}</p>
        <p><a href=\"{map_link}\">Click here to view location on map</a></p>
        <p>
          <a href=\"{accept_link}\" style=\"background:#1f6feb;color:#fff;padding:10px 16px;text-decoration:none;border-radius:6px;display:inline-block;\">Accept Complaint</a>
        </p>
      </body>
    </html>
    """.strip()

    msg.set_content(plain_text)
    msg.add_alternative(html, subtype="html")

    if image_path:
        try:
            data = load_image_bytes(image_path)
            subtype = (guess_mime_type(image_path).split("/")[-1] or "jpeg").replace("jpg", "jpeg")
            filename = Path(image_path).name or "complaint.jpg"
            msg.add_attachment(
                data,
                maintype="image",
                subtype=subtype,
                filename=filename,
            )
        except Exception as exc:
            logger.warning("Could not attach complaint image path=%s error=%s", image_path, exc)

    return msg


def _send_email_message(message: EmailMessage) -> None:
    smtp = _smtp_settings()
    with smtplib.SMTP(smtp["host"], smtp["port"], timeout=30) as server:
        server.starttls()
        server.login(smtp["username"], smtp["password"])
        server.send_message(message)


def _send_assignment_email(complaint: Dict[str, Any], officer_email: str, image_path: Optional[str]) -> None:
    message = _compose_email(complaint=complaint, to_email=officer_email, image_path=image_path)
    _send_email_message(message)


def _mark_notification_sent(notification_id: ObjectId, increment_retry: bool) -> None:
    update_data: Dict[str, Any] = {
        "last_sent_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_error": None,
        "status": "PENDING",
    }
    if increment_retry:
        notifications_collection.update_one(
            {"_id": notification_id},
            {"$set": update_data, "$inc": {"retry_count": 1}},
        )
    else:
        notifications_collection.update_one(
            {"_id": notification_id},
            {"$set": update_data},
        )


def _mark_notification_error(notification_id: ObjectId, error: str, increment_retry: bool) -> None:
    update_data: Dict[str, Any] = {
        "updated_at": datetime.utcnow(),
        "last_error": error,
        "status": "PENDING",
    }
    if increment_retry:
        notifications_collection.update_one(
            {"_id": notification_id},
            {"$set": update_data, "$inc": {"retry_count": 1}},
        )
    else:
        notifications_collection.update_one(
            {"_id": notification_id},
            {"$set": update_data},
        )


def create_assignment_notification_and_send(complaint: Dict[str, Any], image_path: Optional[str]) -> Optional[Dict[str, Any]]:
    complaint_id = complaint.get("complaint_id")
    officer_id = complaint.get("officer_id")

    if not complaint_id or not officer_id:
        logger.info("Notification skipped complaint_id=%s officer_id=%s", complaint_id, officer_id)
        return None

    existing = notifications_collection.find_one(
        {
            "complaint_id": complaint_id,
            "officer_id": officer_id,
            "status": {"$in": ["PENDING", "ACCEPTED"]},
        }
    )
    if existing and existing.get("status") == "ACCEPTED":
        return existing

    now = datetime.utcnow()
    if not existing:
        notification = {
            "complaint_id": complaint_id,
            "officer_id": officer_id,
            "channel": "EMAIL",
            "status": "PENDING",
            "retry_count": 0,
            "last_sent_at": None,
            "last_error": None,
            "created_at": now,
            "updated_at": now,
        }
        insert_result = notifications_collection.insert_one(notification)
        notification["_id"] = insert_result.inserted_id
    else:
        notification = existing

    if notification.get("last_sent_at"):
        elapsed = now - notification["last_sent_at"]
        if elapsed < timedelta(minutes=_retry_interval_minutes()):
            logger.info("Notification send skipped due to cooldown complaint_id=%s", complaint_id)
            return notification

    try:
        officer_email = _officer_email(officer_id)
        _send_assignment_email(complaint=complaint, officer_email=officer_email, image_path=image_path)
        _mark_notification_sent(notification["_id"], increment_retry=False)
        logger.info("Assignment email sent complaint_id=%s officer_email=%s", complaint_id, officer_email)
    except Exception as exc:
        logger.exception("Assignment email send failed complaint_id=%s error=%s", complaint_id, exc)
        _mark_notification_error(notification["_id"], str(exc), increment_retry=False)

    return notifications_collection.find_one({"_id": notification["_id"]})


def mark_notification_accepted(complaint_id: str) -> None:
    notifications_collection.update_many(
        {"complaint_id": complaint_id, "status": "PENDING"},
        {
            "$set": {
                "status": "ACCEPTED",
                "accepted_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        },
    )


def process_pending_notifications_for_retry() -> None:
    now = datetime.utcnow()
    retry_delta = timedelta(minutes=_retry_interval_minutes())

    for notification in notifications_collection.find({"status": "PENDING", "channel": "EMAIL"}):
        complaint_id = notification.get("complaint_id")
        if not complaint_id:
            continue

        complaint = complaints_collection.find_one({"complaint_id": complaint_id})
        if not complaint:
            continue

        if complaint.get("status") != "PENDING":
            notifications_collection.update_one(
                {"_id": notification["_id"]},
                {
                    "$set": {
                        "status": "STOPPED",
                        "updated_at": now,
                    }
                },
            )
            continue

        last_sent_at = notification.get("last_sent_at")
        if last_sent_at and (now - last_sent_at) < retry_delta:
            continue

        officer_id = notification.get("officer_id")
        if not officer_id:
            continue

        try:
            officer_email = _officer_email(str(officer_id))
            image_doc = images_collection.find_one(
                {"complaint_id": complaint_id, "type": "BEFORE"},
                sort=[("created_at", -1)],
            )
            image_path = image_doc.get("image_url") if image_doc else None
            _send_assignment_email(complaint=complaint, officer_email=officer_email, image_path=image_path)
            _mark_notification_sent(notification["_id"], increment_retry=True)
            logger.info("Retry email sent complaint_id=%s officer_email=%s", complaint_id, officer_email)
        except Exception as exc:
            logger.exception("Retry email failed complaint_id=%s error=%s", complaint_id, exc)
            _mark_notification_error(notification["_id"], str(exc), increment_retry=True)
