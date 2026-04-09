"""Email service using Resend API."""

from __future__ import annotations

import os

import resend


def _configure():
    resend.api_key = os.environ.get("RESEND_API_KEY", "")


def send_verification_code(to_email: str, code: str, purpose: str = "signup") -> bool:
    """Send a 6-digit verification code via Resend.

    Returns True on success, False on failure.
    """
    _configure()
    sender = os.environ.get("RESEND_EMAIL", "noreply@echofy.com")

    if purpose == "delete":
        subject = "Echofy — Account Deletion Verification"
        html = (
            f"<div style='font-family:sans-serif;max-width:480px;margin:0 auto;'>"
            f"<h2 style='color:#e87c7c;'>Account Deletion Request</h2>"
            f"<p>You requested to delete your Echofy account. Enter this code to confirm:</p>"
            f"<div style='font-size:32px;font-weight:700;letter-spacing:8px;text-align:center;"
            f"background:#111;color:#fff;padding:20px;border-radius:8px;margin:24px 0;'>{code}</div>"
            f"<p style='color:#888;font-size:14px;'>This code expires in <strong>3 minutes</strong>. "
            f"If you did not request this, you can safely ignore this email.</p>"
            f"</div>"
        )
    else:
        subject = "Echofy — Verify Your Email"
        html = (
            f"<div style='font-family:sans-serif;max-width:480px;margin:0 auto;'>"
            f"<h2 style='color:#4a7fd4;'>Welcome to Echofy!</h2>"
            f"<p>Enter this code to verify your email and complete your account:</p>"
            f"<div style='font-size:32px;font-weight:700;letter-spacing:8px;text-align:center;"
            f"background:#111;color:#fff;padding:20px;border-radius:8px;margin:24px 0;'>{code}</div>"
            f"<p style='color:#888;font-size:14px;'>This code expires in <strong>3 minutes</strong>. "
            f"If you did not sign up for Echofy, you can safely ignore this email.</p>"
            f"</div>"
        )

    try:
        resend.Emails.send({
            "from": f"Echofy <{sender}>",
            "to": [to_email],
            "subject": subject,
            "html": html,
        })
        return True
    except Exception as exc:
        print(f"[email_service] Failed to send email to {to_email}: {exc}")
        return False
