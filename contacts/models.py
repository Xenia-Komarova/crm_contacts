from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

class Industry(models.Model):
    name = models.CharField("Отрасль", max_length=120, unique=True)
    class Meta:
        ordering = ["name"]
        verbose_name = "отрасль"
        verbose_name_plural = "отрасли"
    def __str__(self): return self.name

class Source(models.Model):
    name = models.CharField("Источник", max_length=120, unique=True)
    class Meta:
        ordering = ["name"]
        verbose_name = "источник"
        verbose_name_plural = "источники"
    def __str__(self): return self.name

class Contact(models.Model):
    surname = models.CharField("Фамилия", max_length=120, blank=True)
    first_name = models.CharField("Имя", max_length=120, blank=True)
    patronymic = models.CharField("Отчество", max_length=120, blank=True)
    company = models.CharField("Компания", max_length=240, blank=True, db_index=True)
    industry = models.ForeignKey(Industry, verbose_name="Отрасль", null=True, blank=True, on_delete=models.SET_NULL)
    source = models.ForeignKey(Source, verbose_name="Источник", null=True, blank=True, on_delete=models.SET_NULL)
    position = models.CharField("Должность", max_length=240, blank=True)
    top_management = models.BooleanField("Топ-менеджмент", default=False, db_index=True)
    gr = models.BooleanField("GR", default=False, db_index=True)
    comments = models.TextField("Комментарий", blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Изменён", auto_now=True)
    class Meta:
        ordering = ["surname", "first_name", "company"]
        verbose_name = "контакт"
        verbose_name_plural = "контакты"
    def __str__(self):
        name = " ".join(x for x in (self.surname, self.first_name, self.patronymic) if x)
        return name or self.company or f"Контакт #{self.pk}"

class ContactEmail(models.Model):
    class Status(models.TextChoices):
        UNKNOWN = "unknown", "Неизвестен"
        PENDING = "pending", "Ожидает подтверждения"
        ACTIVE = "active", "Активен"
        UNSUBSCRIBED = "unsubscribed", "Отписан"
        DISABLED = "disabled", "Отключён"
        BLOCKED = "blocked", "Заблокирован"
        BOUNCED = "bounced", "Недоставляемый"
    contact = models.ForeignKey(Contact, related_name="emails", on_delete=models.CASCADE)
    address = models.EmailField("E-mail", max_length=254, unique=True)
    mailing_status = models.CharField("Статус подписки", max_length=24, choices=Status.choices, default=Status.UNKNOWN)
    delivery_status = models.CharField("Статус доставки UniSender", max_length=40, blank=True)
    unisender_person_id = models.CharField("ID в UniSender", max_length=40, blank=True)
    synced_at = models.DateTimeField("Синхронизирован", null=True, blank=True)
    sync_error = models.TextField("Ошибка синхронизации", blank=True)
    class Meta:
        ordering = ["address"]
        constraints = [models.UniqueConstraint(Lower("address"), name="contact_email_case_insensitive_unique")]
        verbose_name = "e-mail"
        verbose_name_plural = "e-mail"
    def save(self, *args, **kwargs):
        self.address = self.address.strip().lower()
        super().save(*args, **kwargs)
    def __str__(self): return self.address

class ContactPhone(models.Model):
    contact = models.ForeignKey(Contact, related_name="phones", on_delete=models.CASCADE)
    number = models.CharField("Телефон", max_length=40)
    class Meta:
        ordering = ["number"]
        verbose_name = "телефон"
        verbose_name_plural = "телефоны"
    def save(self, *args, **kwargs):
        self.number = self.number.strip()
        super().save(*args, **kwargs)
    def __str__(self): return self.number

class ChangeLog(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Создан"
        UPDATED = "updated", "Изменён"
        DELETED = "deleted", "Удалён"
    contact = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.SET_NULL, related_name="history")
    contact_label = models.CharField(max_length=400, blank=True)
    action = models.CharField(max_length=32, choices=Action.choices)
    details = models.TextField(blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "запись истории"
        verbose_name_plural = "история изменений"

class UniSenderEvent(models.Model):
    event_name = models.CharField(max_length=40)
    email = models.EmailField(blank=True)
    status = models.CharField(max_length=60, blank=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
