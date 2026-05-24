"""Forms backing the web UI auth flows."""

from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class SignupForm(forms.Form):
    username = forms.CharField(max_length=64, min_length=3)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)

    def clean_username(self) -> str:
        name = self.cleaned_data["username"]
        if User.objects.filter(username=name).exists():
            raise forms.ValidationError("Username already taken.")
        return name


class LoginForm(forms.Form):
    username = forms.CharField(max_length=64)
    password = forms.CharField(widget=forms.PasswordInput)


class TOTPVerifyForm(forms.Form):
    token = forms.CharField(max_length=8, min_length=6, label="6-digit code")


class TokenCreateForm(forms.Form):
    label = forms.CharField(max_length=128)
    totp = forms.CharField(
        max_length=8,
        min_length=6,
        required=False,
        label="6-digit code (if 2FA is enabled)",
    )


class DeviceCodeApproveForm(forms.Form):
    user_code = forms.CharField(max_length=16)
    totp = forms.CharField(
        max_length=8,
        min_length=6,
        required=False,
        label="6-digit code (if 2FA is enabled)",
    )
    action = forms.ChoiceField(
        choices=[("approve", "Approve"), ("deny", "Deny")],
        widget=forms.HiddenInput,
        initial="approve",
    )
