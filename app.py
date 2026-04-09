import base64
import os
import secrets
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for

load_dotenv()


class Config:
    CLIENT_ID = os.getenv("PINTEREST_CLIENT_ID", "")
    CLIENT_SECRET = os.getenv("PINTEREST_CLIENT_SECRET", "")
    REDIRECT_URI = os.getenv("PINTEREST_REDIRECT_URI", "http://localhost:5000/callback")
    SCOPES = os.getenv(
        "PINTEREST_SCOPES",
        "user_accounts:read,boards:read,pins:read,ads:read",
    )
    AUTH_URL = os.getenv("PINTEREST_AUTH_URL", "https://www.pinterest.com/oauth/")
    TOKEN_URL = os.getenv("PINTEREST_TOKEN_URL", "https://api.pinterest.com/v5/oauth/token")
    API_BASE_URL = os.getenv("PINTEREST_API_BASE_URL", "https://api.pinterest.com/v5")
    CONTINUOUS_REFRESH = os.getenv("PINTEREST_CONTINUOUS_REFRESH", "true").lower() == "true"
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))


app = Flask(__name__)
app.secret_key = Config.FLASK_SECRET_KEY


def require_config():
    missing = []
    if not Config.CLIENT_ID:
        missing.append("PINTEREST_CLIENT_ID")
    if not Config.CLIENT_SECRET:
        missing.append("PINTEREST_CLIENT_SECRET")
    return missing


def basic_auth_header() -> str:
    raw = f"{Config.CLIENT_ID}:{Config.CLIENT_SECRET}".encode("utf-8")
    return base64.b64encode(raw).decode("utf-8")


def exchange_token(payload: dict) -> dict:
    headers = {
        "Authorization": f"Basic {basic_auth_header()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    response = requests.post(Config.TOKEN_URL, data=payload, headers=headers, timeout=30)
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "data": safe_json(response),
    }


def safe_json(response):
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text}


def api_get(path: str, params: dict | None = None) -> dict:
    token = session.get("access_token")
    if not token:
        return {"ok": False, "status_code": 401, "data": {"message": "No access token in session."}}

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{Config.API_BASE_URL}{path}",
        headers=headers,
        params=params or {},
        timeout=30,
    )
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "data": safe_json(response),
    }


def mask_token(token: str | None) -> str | None:
    if not token:
        return None
    if len(token) <= 12:
        return token
    return f"{token[:6]}...{token[-6:]}"


@app.route("/")
def index():
    missing = require_config()
    results = session.get("results", {})
    return render_template(
        "index.html",
        missing=missing,
        scopes=Config.SCOPES,
        redirect_uri=Config.REDIRECT_URI,
        token_summary={
            "access_token": mask_token(session.get("access_token")),
            "refresh_token": mask_token(session.get("refresh_token")),
            "scope": session.get("scope"),
            "token_type": session.get("token_type"),
            "expires_in": session.get("expires_in"),
        },
        results=results,
    )


@app.route("/login")
def login():
    missing = require_config()
    if missing:
        session["results"] = {
            "config_error": {
                "ok": False,
                "status_code": 500,
                "data": {"message": f"Missing required environment variables: {', '.join(missing)}"},
            }
        }
        return redirect(url_for("index"))

    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    params = {
        "response_type": "code",
        "client_id": Config.CLIENT_ID,
        "redirect_uri": Config.REDIRECT_URI,
        "scope": Config.SCOPES,
        "state": state,
    }
    return redirect(f"{Config.AUTH_URL}?{urlencode(params)}")


@app.route("/callback")
def callback():
    error = request.args.get("error")
    code = request.args.get("code")
    returned_state = request.args.get("state")
    expected_state = session.get("oauth_state")

    if error:
        session["results"] = {
            "oauth_error": {
                "ok": False,
                "status_code": 400,
                "data": {
                    "error": error,
                    "error_description": request.args.get("error_description"),
                },
            }
        }
        return redirect(url_for("index"))

    if not code:
        session["results"] = {
            "callback_error": {
                "ok": False,
                "status_code": 400,
                "data": {"message": "Pinterest did not return an authorization code."},
            }
        }
        return redirect(url_for("index"))

    if not expected_state or returned_state != expected_state:
        session["results"] = {
            "state_error": {
                "ok": False,
                "status_code": 400,
                "data": {"message": "OAuth state mismatch. Start the login flow again."},
            }
        }
        return redirect(url_for("index"))

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": Config.REDIRECT_URI,
    }
    if Config.CONTINUOUS_REFRESH:
        payload["continuous_refresh"] = "true"

    token_result = exchange_token(payload)
    if token_result["ok"]:
        data = token_result["data"]
        session["access_token"] = data.get("access_token")
        session["refresh_token"] = data.get("refresh_token")
        session["scope"] = data.get("scope")
        session["token_type"] = data.get("token_type")
        session["expires_in"] = data.get("expires_in")

    session["results"] = {"token_exchange": token_result}
    session.pop("oauth_state", None)
    return redirect(url_for("index"))


@app.route("/refresh", methods=["POST"])
def refresh():
    refresh_token = session.get("refresh_token")
    if not refresh_token:
        session["results"] = {
            "refresh_error": {
                "ok": False,
                "status_code": 400,
                "data": {"message": "No refresh token found in session."},
            }
        }
        return redirect(url_for("index"))

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    if Config.CONTINUOUS_REFRESH:
        payload["continuous_refresh"] = "true"

    refresh_result = exchange_token(payload)
    if refresh_result["ok"]:
        data = refresh_result["data"]
        session["access_token"] = data.get("access_token", session.get("access_token"))
        session["refresh_token"] = data.get("refresh_token", session.get("refresh_token"))
        session["scope"] = data.get("scope", session.get("scope"))
        session["token_type"] = data.get("token_type", session.get("token_type"))
        session["expires_in"] = data.get("expires_in", session.get("expires_in"))

    session["results"] = {"refresh_token": refresh_result}
    return redirect(url_for("index"))


@app.route("/fetch-user", methods=["POST"])
def fetch_user():
    session["results"] = {"user_account": api_get("/user_account")}
    return redirect(url_for("index"))


@app.route("/fetch-ad-accounts", methods=["POST"])
def fetch_ad_accounts():
    session["results"] = {"ad_accounts": api_get("/ad_accounts")}
    return redirect(url_for("index"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
