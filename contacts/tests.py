from django.test import TestCase
from django.db import IntegrityError
from .models import Contact, ContactEmail, ContactPhone, Industry
from .services import process_webhook

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

