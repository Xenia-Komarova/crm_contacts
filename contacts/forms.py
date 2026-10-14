from django import forms
from .models import Contact, Industry, Source, ContactEmail

class ContactForm(forms.ModelForm):
    emails_text = forms.CharField(label="E-mail", required=False, widget=forms.Textarea(attrs={"rows": 3, "placeholder": "По одному адресу на строку"}), help_text="Каждый адрес с новой строки. E-mail должен быть уникальным во всей базе.")
    phones_text = forms.CharField(label="Телефоны", required=False, widget=forms.Textarea(attrs={"rows": 3, "placeholder": "По одному номеру на строку"}), help_text="Каждый номер с новой строки. Повторяющиеся телефоны разрешены.")
    class Meta:
        model = Contact
        fields = ["surname", "first_name", "patronymic", "company", "industry", "source", "position", "top_management", "gr", "comments"]
        widgets = {"comments": forms.Textarea(attrs={"rows": 5, "placeholder": "Адрес доставки, помощник, дополнительные сведения…"})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and not self.is_bound:
            self.fields["emails_text"].initial = "\n".join(self.instance.emails.values_list("address", flat=True))
            self.fields["phones_text"].initial = "\n".join(self.instance.phones.values_list("number", flat=True))
        self.fields["industry"].queryset = Industry.objects.all()
        self.fields["source"].queryset = Source.objects.all()
    @staticmethod
    def split_values(value):
        values = []
        for line in value.replace(",", "\n").replace(";", "\n").splitlines():
            item = line.strip()
            if item and item not in values:
                values.append(item)
        return values
    def clean_emails_text(self):
        values = [v.lower() for v in self.split_values(self.cleaned_data.get("emails_text", ""))]
        if len(values) != len(set(values)):
            raise forms.ValidationError("Один и тот же e-mail указан несколько раз.")
        for address in values:
            matches = ContactEmail.objects.filter(address__iexact=address)
            if self.instance.pk:
                matches = matches.exclude(contact=self.instance)
            if matches.exists():
                raise forms.ValidationError(f"Адрес {address} уже закреплён за другим контактом.")
        return values
    def clean_phones_text(self):
        return self.split_values(self.cleaned_data.get("phones_text", ""))
