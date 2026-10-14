from django.contrib import admin
from .models import Contact, ContactEmail, ContactPhone, Industry, Source, ChangeLog, UniSenderEvent

class EmailInline(admin.TabularInline):
    model = ContactEmail
    extra = 0

class PhoneInline(admin.TabularInline):
    model = ContactPhone
    extra = 0

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("surname", "first_name", "company", "position", "top_management", "gr")
    list_filter = ("top_management", "gr", "industry")
    search_fields = ("surname", "first_name", "patronymic", "company", "position", "emails__address")
    inlines = (EmailInline, PhoneInline)

admin.site.register(Industry)
admin.site.register(Source)
admin.site.register(ChangeLog)
admin.site.register(UniSenderEvent)
