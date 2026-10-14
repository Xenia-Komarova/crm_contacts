from django.test import TestCase
from django.db import IntegrityError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import override_settings
from unittest.mock import patch
from .models import Contact, ContactEmail, ContactPhone, Industry
from .services import process_webhook
from .views import parse_upload

class ContactDataTests(TestCase):
    def test_email_is_unique_case_insensitively(self):
        one = Contact.objects.create(first_name="Анна")
        two = Contact.objects.create(first_name="Ольга")
        ContactEmail.objects.create(contact=one, address="Anna@example.com")
        with self.assertRaises(IntegrityError):
            ContactEmail.objects.create(contact=two, address="anna@example.com")

    def test_multiple_emails_and_reused_phones_are_supported(self):
        a = Contact.objects.create(first_name="Иван", top_management=True, gr=True)
        b = Contact.objects.create(first_name="Пётр")
        ContactEmail.objects.create(contact=a, address="a@example.com")
        ContactEmail.objects.create(contact=a, address="b@example.com")
        ContactPhone.objects.create(contact=a, number="+7 999 000-00-00")
        ContactPhone.objects.create(contact=b, number="+7 999 000-00-00")
        self.assertEqual(a.emails.count(), 2)
        self.assertTrue(a.top_management and a.gr)
        self.assertEqual(ContactPhone.objects.filter(number="+7 999 000-00-00").count(), 2)

    def test_webhook_updates_email_subscription_and_delivery_status(self):
        contact = Contact.objects.create(first_name="Мария")
        email = ContactEmail.objects.create(contact=contact, address="maria@example.com")
        count = process_webhook({"events_by_user": [{"Events": [
            {"event_name": "unsubscribe", "event_data": {"email": "maria@example.com"}},
            {"event_name": "email_status", "event_data": {"email": "maria@example.com", "status": "ok_delivered"}},
        ]}]})
        email.refresh_from_db()
        self.assertEqual(count, 2)
        self.assertEqual(email.mailing_status, ContactEmail.Status.UNSUBSCRIBED)
        self.assertEqual(email.delivery_status, "ok_delivered")

    def test_unisender_export_columns_are_parsed(self):
        data = "email;email_status;contact_status;phone;Name;LastName;Company;Position;tags\nanna@example.com;active;active;+79990000000;Анна;Иванова;Байкал;Директор;GR;\n".encode("utf-8-sig")
        upload = SimpleUploadedFile("export.csv", data)
        row = parse_upload(upload)[0]
        self.assertEqual(row["emails"], ["anna@example.com"])
        self.assertEqual(row["email_status"], "active")
        self.assertEqual(row["first_name"], "Анна")
        self.assertEqual(row["surname"], "Иванова")
        self.assertEqual(row["phones"], ["+79990000000"])
        self.assertEqual(row["tags"], "GR")

    def test_unisender_import_marks_record_synced_and_keeps_status(self):
        user = get_user_model().objects.create_user(username="importer", password="test-password")
        client = self.client
        client.force_login(user)
        session = client.session
        session["import_source"] = "unisender"
        session["import_rows"] = [{"emails": ["sync@example.com"], "email_status": "unsubscribed", "contact_status": "active",
                                   "surname": "Петрова", "first_name": "Елена", "company": "Компания", "position": "Директор",
                                   "phones": ["+79990000001"], "top": False, "gr": False, "tags": "", "industry": "", "source": "", "comments": ""}]
        session.save()
        response = client.post(reverse("import_contacts"), {"action": "commit", "mode": "update"})
        self.assertEqual(response.status_code, 302)
        email = ContactEmail.objects.get(address="sync@example.com")
        self.assertEqual(email.mailing_status, ContactEmail.Status.UNSUBSCRIBED)
        self.assertIsNotNone(email.synced_at)
        self.assertEqual(email.contact.first_name, "Елена")

    @override_settings(UNISENDER_API_KEY="test-api-key", UNISENDER_LIST_ID="42")
    @patch("contacts.views.unisender_call", return_value={"task_uuid": "export-task-1"})
    def test_unisender_import_starts_async_export(self, api_call):
        user = get_user_model().objects.create_user(username="api-importer", password="test-password")
        self.client.force_login(user)
        page = self.client.get(reverse("import_unisender"))
        self.assertEqual(page.status_code, 200)
        response = self.client.post(reverse("import_unisender"), {"action": "start"})
        self.assertRedirects(response, reverse("import_unisender"))
        api_call.assert_called_once()
        self.assertEqual(api_call.call_args.args[0], "async/exportContacts")
        self.assertEqual(api_call.call_args.args[1]["list_id"], "42")
        self.assertEqual(self.client.session["unisender_export_task"], "export-task-1")

