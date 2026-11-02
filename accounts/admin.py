from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import User


class UserAdminCreationForm(forms.ModelForm):
    """
    Form for creating new users in Django Admin with email and name.
    """

    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        help_text="Enter a secure password.",
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm Password",
        required=True,
        help_text="Re-enter the password for confirmation.",
    )

    class Meta:
        model = User
        fields = ("email", "name")

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("The two password fields did not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UserAdminChangeForm(forms.ModelForm):
    """
    Form for editing existing users in Django Admin.
    """

    password = ReadOnlyPasswordHashField(
        help_text=(
            "Raw passwords are not stored. Use "
            '<a href="../password/">this form</a> to change the password.'
        )
    )

    class Meta:
        model = User
        fields = (
            "email",
            "name",
            "password",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin interface for the custom User model.
    Configured for email-based authentication.
    """

    form = UserAdminChangeForm
    add_form = UserAdminCreationForm

    list_display = ("email", "name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active", "is_superuser")
    search_fields = ("email", "name")
    ordering = ("-date_joined",)
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("name",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important Dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "password", "password_confirm"),
            },
        ),
    )
