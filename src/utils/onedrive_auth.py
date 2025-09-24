import os
import requests
import webbrowser
import json

def get_personal_onedrive_token():
    client_id = os.getenv("ONEDRIVE_CLIENT_ID")
    client_secret = os.getenv("ONEDRIVE_CLIENT_SECRET")
    redirect_uri = os.getenv("ONEDRIVE_REDIRECT_URI", "http://localhost:8000/callback")
    scope = "Files.Read offline_access"
    auth_url = (
        f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize"
        f"?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}"
    )
    print("Opening browser for Microsoft login...")
    webbrowser.open(auth_url)
    print("After login, paste the 'code' parameter from the redirect URL here:")
    auth_code = input("Authorization code: ")
    token_url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code": auth_code,
        "scope": scope,
        "client_secret": client_secret,
    }
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    tokens = response.json()
    # Optionally save token for reuse
    with open(".onedrive_token.json", "w") as f:
        json.dump(tokens, f)
    print("Access token saved to .onedrive_token.json")
    return tokens["access_token"]
