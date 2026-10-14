import json
import urllib.parse
import urllib.request
from django.conf import settings
from django.utils import timezone
from .models import ContactEmail, UniSenderEvent

class UniSenderError(Exception):
    pass

def unisender_call(method, params):
    if not settings.UNISENDER_API_KEY:
        raise UniSenderError("Не задан UNISENDER_API_KEY")
    data = {"format": "json", "api_key": settings.UNISENDER_API_KEY, **params}
    request = urllib.request.Request(
        f"https://api.unisender.com/ru/api/{method}?{urllib.parse.urlencode(data, doseq=True)}",
        headers={"User-Agent": "ContactsCRM/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise UniSenderError(str(exc)) from exc
    if "error" in result:
        raise UniSenderError(str(result["error"]))
    return result.get("result", {})

def push_email_to_unisender(email_obj):
    """Push a newly added address. Double opt-in is requested by default."""
    if not settings.UNISENDER_API_KEY or not settings.UNISENDER_LIST_ID:
        return False
    contact = email_obj.contact
    fields = {
        "fields[email]": email_obj.address,
        f"fields[{settings.UNISENDER_FIELD_FIRST_NAME}]": contact.first_name,
        f"fields[{settings.UNISENDER_FIELD_LAST_NAME}]": contact.surname,
        f"fields[{settings.UNISENDER_FIELD_COMPANY}]": contact.company,
        f"fields[{settings.UNISENDER_FIELD_POSITION}]": contact.position,
    }
    try:
        result = unisender_call("subscribe", {"list_ids": settings.UNISENDER_LIST_ID, "double_optin": 0, **fields})
        email_obj.unisender_person_id = str(result.get("person_id", ""))
        email_obj.mailing_status = ContactEmail.Status.PENDING
        email_obj.synced_at = timezone.now()
        email_obj.sync_error = ""
        email_obj.save(update_fields=["unisender_person_id", "mailing_status", "synced_at", "sync_error"])
        return True
    except UniSenderError as exc:
        email_obj.sync_error = str(exc)
        email_obj.save(update_fields=["sync_error"])
        return False

def process_webhook(payload):
    """Apply UniSender delivery and subscription events to matching email records."""
    event_items = []
    if isinstance(payload.get("events_by_user"), list):
        for account in payload["events_by_user"]:
            event_items.extend(account.get("Events", []))
    elif isinstance(payload.get("Events"), list):
        event_items.extend(payload["Events"])
    elif payload.get("event_name"):
        event_items.append(payload)
    changed = 0
    for item in event_items:
        name = item.get("event_name", "")
        data = item.get("event_data", {})
        address = str(data.get("email", "")).strip().lower()
        status = str(data.get("status", ""))
        UniSenderEvent.objects.create(event_name=name, email=address, status=status, payload=item)
        if not address:
            continue
        try:
            email_obj = ContactEmail.objects.get(address__iexact=address)
        except ContactEmail.DoesNotExist:
            continue
        if name == "email_status":
            email_obj.delivery_status = status
            email_obj.synced_at = timezone.now()
            email_obj.save(update_fields=["delivery_status", "synced_at"])
            changed += 1
        elif name == "unsubscribe":
            email_obj.mailing_status = ContactEmail.Status.UNSUBSCRIBED
            email_obj.synced_at = timezone.now()
            email_obj.save(update_fields=["mailing_status", "synced_at"])
            changed += 1
        elif name in ("subscribe", "subscribe_primary"):
            email_obj.mailing_status = ContactEmail.Status.ACTIVE
            email_obj.synced_at = timezone.now()
            email_obj.save(update_fields=["mailing_status", "synced_at"])
            changed += 1
    return changed
