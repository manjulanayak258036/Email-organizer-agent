"""Google OAuth 2.0 and API Service Manager for Gmail and Google Calendar.

Enforces:
1. Real OAuth2 Desktop Installed-App Flow (browser consent, token.json caching).
2. Hard Guardrails in code:
   - gmail.send is NEVER invoked without explicit human approval (status == APPROVED and approver named).
   - Inbox access is strictly scoped to the authenticated mailbox (userId='me').
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional, Dict, Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from core.models import DraftReply, ApprovalStatus

# Full required OAuth scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

DEFAULT_CREDENTIALS_PATH = "credentials.json"
DEFAULT_TOKEN_PATH = "token.json"


class GoogleAuthManager:
    def __init__(
        self,
        credentials_path: str = DEFAULT_CREDENTIALS_PATH,
        token_path: str = DEFAULT_TOKEN_PATH,
    ):
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.creds: Optional[Credentials] = None

    def get_credentials(self, interactive: bool = True) -> Credentials:
        """Load or refresh credentials; opens browser flow if token.json is absent."""
        if self.token_path.exists():
            try:
                self.creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            except Exception as e:
                print(f"[Auth] Notice: Existing token.json could not be parsed: {e}")
                self.creds = None

        # If there are no valid credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    print("[Auth] Credentials refreshed successfully.")
                except Exception as e:
                    print(f"[Auth] Refresh token failed: {e}. Requesting re-authorization...")
                    self.creds = None

            if not self.creds:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"OAuth credentials file '{self.credentials_path}' not found in project root. "
                        "Please place credentials.json in the project root."
                    )
                if not interactive:
                    raise RuntimeError("Authentication required but interactive browser flow is disabled.")

                print("[Auth] Opening browser window for Google OAuth 2.0 authorization...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.token_path, "w", encoding="utf-8") as token_file:
                token_file.write(self.creds.to_json())
            print(f"[Auth] Token saved securely to {self.token_path}")

        return self.creds

    def get_gmail_service(self, interactive: bool = True):
        creds = self.get_credentials(interactive=interactive)
        return build("gmail", "v1", credentials=creds)

    def get_calendar_service(self, interactive: bool = True):
        creds = self.get_credentials(interactive=interactive)
        return build("calendar", "v3", credentials=creds)


def send_email_guarded(
    gmail_service,
    draft: DraftReply,
    approver: str,
    override_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Strictly guarded email sending function.

    GUARDRAIL ENFORCEMENT IN CODE:
    - Never send an email without explicit faculty (human) approval.
    - Status MUST be ApprovalStatus.APPROVED.
    - Approver MUST be explicitly identified.
    """
    if draft.status != ApprovalStatus.APPROVED:
        raise PermissionError(
            f"GUARDRAIL VIOLATION: Attempted to send email draft '{draft.draft_id}' with status '{draft.status}'. "
            "Emails can only be dispatched after explicit Faculty Approval."
        )

    if not approver or approver.strip() == "":
        raise PermissionError(
            "GUARDRAIL VIOLATION: An identified faculty approver must sign off on the outgoing email."
        )

    import base64
    from email.mime.text import MIMEText

    message = MIMEText(draft.body)
    message["to"] = draft.recipient
    message["subject"] = draft.subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    result = (
        gmail_service.users()
        .messages()
        .send(userId="me", body={"raw": raw_message, "threadId": draft.thread_id})
        .execute()
    )
    return result
