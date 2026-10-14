from django.urls import path
from . import views

urlpatterns = [
    path("", views.contact_list, name="contact_list"),
    path("contacts/add/", views.contact_edit, name="contact_add"),
    path("contacts/<int:pk>/", views.contact_detail, name="contact_detail"),
    path("contacts/<int:pk>/edit/", views.contact_edit, name="contact_edit"),
    path("contacts/<int:pk>/delete/", views.contact_delete, name="contact_delete"),
    path("export/", views.export_contacts, name="export_contacts"),
    path("import/", views.import_contacts, name="import_contacts"),
    path("unisender/sync/", views.unisender_sync, name="unisender_sync"),
    path("hooks/unisender/<str:token>/", views.unisender_webhook, name="unisender_webhook"),
]
