from django import forms
from app.models import *

class MailForm(forms.ModelForm):
    class Meta:
        model = Mail
        exclude = ('status',)