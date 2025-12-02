from django import forms

from dataroom.models import Folder, FileCategory


class DataRoomForm(forms.ModelForm):
    """Form for creating/updating a Folder in the dataroom.

    The previous implementation referenced `question`/`answer` fields which
    belong to the `Question` model. For folder admin views we need the
    `name` and `description` fields from `Folder`.
    """

    class Meta:
        model = Folder
        fields = ["name", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Folder name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "cols": 40,
                    "rows": 5,
                    "class": "form-control description-box",
                    "placeholder": "Enter folder description (optional)...",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class FileCategoryForm(forms.ModelForm):
    class Meta:
        model = FileCategory
        fields = ["folder", "name", "description", "is_active"]
        widgets = {
            "folder": forms.Select(attrs={"class": "form-control"}),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Category name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "cols": 40,
                    "rows": 4,
                    "class": "form-control description-box",
                    "placeholder": "Enter category description (optional)...",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class FolderSelectionForm(forms.Form):
    folders = forms.ModelMultipleChoiceField(
        queryset=Folder.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )


class CategorySelectionForm(forms.Form):
    categories = forms.ModelMultipleChoiceField(
        queryset=FileCategory.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )


class LoginForm(forms.Form):
    email = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "email",
            }
        )
    )
    password = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password",
                "type": "password",
            }
        )
    )