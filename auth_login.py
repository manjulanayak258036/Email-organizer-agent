"""Interactive Google OAuth2 Login Script.

Run this script to authenticate your Google account via browser consent flow.
It reads `credentials.json` from the root directory, launches the OAuth2 local server flow,
authorizes the required Gmail & Calendar scopes, and saves `token.json`.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.auth import GoogleAuthManager


def main():
    print("=" * 70)
    print("GOOGLE OAUTH 2.0 DESKTOP AUTHENTICATION")
    print("=" * 70)

    auth = GoogleAuthManager(
        credentials_path=str(ROOT / "credentials.json"),
        token_path=str(ROOT / "token.json"),
    )

    try:
        print("[1/2] Launching browser consent window for Google OAuth 2.0...")
        print("      Scopes requested:")
        print("        - gmail.readonly")
        print("        - gmail.modify")
        print("        - gmail.send")
        print("        - calendar.readonly")
        print("        - calendar.events")
        print("      Please select your Google Account and grant access.")
        
        creds = auth.get_credentials(interactive=True)
        print("\n[2/2] Testing live Gmail connection with authorized credentials...")
        service = auth.get_gmail_service(interactive=False)
        profile = service.users().getProfile(userId="me").execute()

        print("\n" + "=" * 70)
        print("AUTHENTICATION SUCCESSFUL!")
        print(f"  Authenticated Email: {profile.get('emailAddress')}")
        print(f"  Total Messages in Mailbox: {profile.get('messagesTotal')}")
        print(f"  Total Threads in Mailbox:  {profile.get('threadsTotal')}")
        print(f"  Token saved to: {ROOT / 'token.json'} (gitignored)")
        print("=" * 70)
    except Exception as e:
        print(f"\n[Error] Authentication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
