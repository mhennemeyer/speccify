"""Server-rendered web views for auth, 2FA, tokens and device approval."""

from __future__ import annotations

import base64
import io

import qrcode
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from ..api import device_codes, two_factor
from ..api.models import ApiToken, DeviceCodeStatus
from ..api.tokens import mint_token
from ..api.views import device_code_cache_key
from .forms import (
    DeviceCodeApproveForm,
    LoginForm,
    SignupForm,
    TokenCreateForm,
    TOTPVerifyForm,
)

User = get_user_model()


@require_http_methods(["GET", "POST"])
def signup_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            login(request, user)
            return redirect("web-totp-setup")
    else:
        form = SignupForm()
    return render(request, "web/signup.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            if user is not None:
                login(request, user)
                next_url = request.GET.get("next") or "web-tokens"
                return redirect(next_url if next_url.startswith("/") else next_url)
            form.add_error(None, "Invalid credentials.")
    else:
        form = LoginForm()
    return render(request, "web/login.html", {"form": form})


@require_http_methods(["POST"])
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("web-login")


def _totp_provisioning_qr(device) -> str:
    """Return a base64-encoded PNG with the otpauth:// QR code."""

    img = qrcode.make(device.config_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


@login_required(login_url="/auth/login")
@require_http_methods(["GET", "POST"])
def totp_setup_view(request: HttpRequest) -> HttpResponse:
    device = two_factor.get_confirmed_device(request.user)
    if device is not None:
        return redirect("web-tokens")

    device = two_factor.get_or_create_unconfirmed_device(request.user)
    if request.method == "POST":
        form = TOTPVerifyForm(request.POST)
        if form.is_valid():
            if two_factor.verify_token(device, form.cleaned_data["token"]):
                request.session["last_2fa_verified_at"] = timezone.now().isoformat()
                messages.success(request, "Two-factor authentication enabled.")
                return redirect("web-tokens")
            form.add_error("token", "Invalid code, try again.")
    else:
        form = TOTPVerifyForm()
    return render(
        request,
        "web/totp_setup.html",
        {"form": form, "qr_png_b64": _totp_provisioning_qr(device)},
    )


def _verify_fresh_totp(user, raw_token: str) -> bool:
    """If ``user`` has a confirmed TOTP device, verify ``raw_token`` against it."""

    device = two_factor.get_confirmed_device(user)
    if device is None:
        return True  # 2FA not enabled yet → treat as fresh
    return two_factor.verify_token(device, raw_token)


@login_required(login_url="/auth/login")
@require_http_methods(["GET", "POST"])
def tokens_view(request: HttpRequest) -> HttpResponse:
    issued_cleartext: str | None = None
    if request.method == "POST":
        form = TokenCreateForm(request.POST)
        if form.is_valid():
            has_2fa = two_factor.get_confirmed_device(request.user) is not None
            ok = (
                True if not has_2fa else _verify_fresh_totp(request.user, form.cleaned_data["totp"])
            )
            if not ok:
                form.add_error("totp", "Invalid 2FA code.")
            else:
                minted = mint_token(
                    user=request.user,
                    label=form.cleaned_data["label"],
                    requires_2fa=has_2fa,
                    last_2fa_verified_at=timezone.now() if has_2fa else None,
                )
                issued_cleartext = minted.cleartext
                form = TokenCreateForm()  # reset
    else:
        form = TokenCreateForm()
    active_tokens = ApiToken.objects.filter(user=request.user, revoked_at__isnull=True).order_by(
        "-created_at"
    )
    return render(
        request,
        "web/tokens.html",
        {
            "form": form,
            "issued_cleartext": issued_cleartext,
            "active_tokens": active_tokens,
        },
    )


@login_required(login_url="/auth/login")
@require_http_methods(["POST"])
def token_revoke_view(request: HttpRequest, token_id: int) -> HttpResponse:
    token = ApiToken.objects.filter(id=token_id, user=request.user, revoked_at__isnull=True).first()
    if token is not None:
        token.revoked_at = timezone.now()
        token.save(update_fields=["revoked_at"])
        messages.success(request, f"Token '{token.label}' revoked.")
    return redirect("web-tokens")


@login_required(login_url="/auth/login")
@require_http_methods(["GET", "POST"])
def device_approve_view(request: HttpRequest) -> HttpResponse:
    """``GET/POST /auth/device`` — user enters ``user_code`` and approves the CLI."""

    if request.method == "POST":
        form = DeviceCodeApproveForm(request.POST)
        if form.is_valid():
            dc = device_codes.fetch_by_user_code(form.cleaned_data["user_code"])
            if dc is None:
                form.add_error("user_code", "Unknown or expired code.")
            elif dc.status != DeviceCodeStatus.PENDING:
                form.add_error("user_code", f"Code already {dc.status}.")
            elif form.cleaned_data["action"] == "deny":
                device_codes.deny(dc)
                messages.info(request, "Login request denied.")
                return redirect("web-tokens")
            else:
                has_2fa = two_factor.get_confirmed_device(request.user) is not None
                ok = (
                    True
                    if not has_2fa
                    else _verify_fresh_totp(request.user, form.cleaned_data["totp"])
                )
                if not ok:
                    form.add_error("totp", "Invalid 2FA code.")
                else:
                    minted = mint_token(
                        user=request.user,
                        label=f"cli@{form.cleaned_data['user_code']}",
                        requires_2fa=has_2fa,
                        last_2fa_verified_at=(timezone.now() if has_2fa else None),
                    )
                    cache.set(
                        device_code_cache_key(dc.device_code),
                        minted.cleartext,
                        timeout=600,
                    )
                    device_codes.approve(dc, user=request.user, api_token=minted.token)
                    messages.success(
                        request,
                        "CLI approved — return to your terminal.",
                    )
                    return redirect("web-tokens")
    else:
        form = DeviceCodeApproveForm(initial={"user_code": request.GET.get("user_code", "")})
    return render(request, "web/device_approve.html", {"form": form})
