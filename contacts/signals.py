from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Contact, ChangeLog

@receiver(post_save, sender=Contact)
def log_contact_save(sender, instance, created, **kwargs):
    ChangeLog.objects.create(contact=instance, contact_label=str(instance), action="created" if created else "updated")

@receiver(pre_delete, sender=Contact)
def log_contact_delete(sender, instance, **kwargs):
    ChangeLog.objects.create(contact=None, contact_label=str(instance), action="deleted")
