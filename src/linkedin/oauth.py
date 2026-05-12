"""
linkedin/oauth.py
-----------------
LinkedIn OAuth 2.0 flow for posting on your own behalf.
Permission needed: w_member_social (post), openid, profile

Setup steps (one-time):
1. Go to https://www.linkedin.com/developers/apps
2. Create a new app (name: "Personal Brand Automation")
3. Under "Auth", add redirect URI: http://localhost:8080/callback
4. Request permission: w_member_social
5. Copy Client ID and Client Secret to .env
6. Run: python main.py auth-linkedin
"""

import os
import json
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
import httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN_FILE = Path("data/linkedin_token.json")

LINKEDIN_AUTH_URL   = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL  = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_PROFILE_URL = "https://api.linkedin.com/v2/userinfo"
REDIRECT_URI        = "http://localhost:8080/callback"
SCOPES              = "openid profile email w_member_social"


class _CallbackHandler(BaseHTTPRequestHandler):
    """Minimal HTTP server to capture the OAuth callback."""
    auth_code = None

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if "code" in params:
            _CallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>LinkedIn auth complete. You can close this tab.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h2>Error: no code received.</h2>")

    def log_message(self, *args):
        pass  # Suppress request logs


def run_oauth_flow() -> dict:
    """
    Run the full OAuth flow:
    1. Open browser to LinkedIn auth page
    2. Listen for callback with auth code
    3. Exchange code for access token
    4. Fetch user profile (person URN)
    5. Save token to data/linkedin_token.json

    Returns: token dict with access_token and person_urn
    """
    client_id = os.environ["LINKEDIN_CLIENT_ID"]
    client_secret = os.environ["LINKEDIN_CLIENT_SECRET"]

    # Step 1: Build auth URL
    auth_params = {
        "response_type": "code",
        "client_id":     client_id,
        "redirect_uri":  REDIRECT_URI,
        "scope":         SCOPES,
        "state":         "personal_brand_automation",
    }
    auth_url = f"{LINKEDIN_AUTH_URL}?{urlencode(auth_params)}"

    print(f"\n[linkedin/oauth] Opening browser for LinkedIn authorization...")
    print(f"If it doesn't open, go to:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Step 2: Wait for callback
    server = HTTPServer(("localhost", 8080), _CallbackHandler)
    server.handle_request()  # Handles exactly one request then exits

    code = _CallbackHandler.auth_code
    if not code:
        raise RuntimeError("OAuth failed — no authorization code received.")

    # Step 3: Exchange code for token
    token_response = httpx.post(
        LINKEDIN_TOKEN_URL,
        data={
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  REDIRECT_URI,
            "client_id":     client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token_response.raise_for_status()
    token_data = token_response.json()
    access_token = token_data["access_token"]

    # Step 4: Get person URN
    profile_resp = httpx.get(
        LINKEDIN_PROFILE_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    profile_resp.raise_for_status()
    profile = profile_resp.json()
    person_urn = f"urn:li:person:{profile['sub']}"

    # Step 5: Save
    token_store = {
        "access_token": access_token,
        "person_urn":   person_urn,
        "name":         profile.get("name", ""),
        "expires_in":   token_data.get("expires_in", 5184000),  # ~60 days
        "saved_at":     __import__("datetime").datetime.utcnow().isoformat(),
    }
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_store, f, indent=2)

    print(f"\n✅ Authorized as: {profile.get('name')} ({person_urn})")
    print(f"Token saved to {TOKEN_FILE}")
    return token_store


def load_token() -> dict:
    """Load saved token. Raises if not found — run auth-linkedin first."""
    # Prefer environment variable (for GitHub Actions)
    env_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    env_urn   = os.environ.get("LINKEDIN_PERSON_URN")
    if env_token and env_urn:
        return {"access_token": env_token, "person_urn": env_urn}

    if not TOKEN_FILE.exists():
        raise FileNotFoundError(
            "LinkedIn token not found. Run: python main.py auth-linkedin"
        )
    with open(TOKEN_FILE) as f:
        return json.load(f)
