from django import forms
from django.core.validators import FileExtensionValidator


class ComplianceTaskImportForm(forms.Form):
    excel_file = forms.FileField(
        label="Compliance Tasks Excel (.xlsx)",
        help_text="Only the 'Compliance Tasks Master' sheet is processed.",
        validators=[FileExtensionValidator(["xlsx"])],
    )

