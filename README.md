# Pinterest OAuth Local Demo

## Goal

This Flask application demonstrates Pinterest's OAuth authorization-code flow locally, allowing developers to test authentication and API access to Pinterest's v5 API endpoints.

## Functionality

The app provides barebones functionality for OAuth testing:

- **Login**: Redirects users to Pinterest's OAuth consent screen to authorize the app.
- **Callback Handling**: Processes the redirect from Pinterest, exchanges the authorization code for access and refresh tokens.
- **Token Storage**: Stores tokens securely in the Flask session for local testing.
- **API Calls**: Allows fetching user account information (`GET /v5/user_account`) and ad accounts (`GET /v5/ad_accounts`).
- **Token Refresh**: Provides the ability to refresh access tokens using the stored refresh token.
- **Logout**: Clears the session and logs out the user.

## Setup

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with the following required variables:

   ```
   FLASK_SECRET_KEY==8f3f4d5a6b7c8d9e0f11223344556677aabbccddeeff00112233445566778899

   PINTEREST_CLIENT_ID="FROM PINTEREST DEVELOPER WEBSITE"
   PINTEREST_CLIENT_SECRET="FROM PINTEREST DEVELOPER WEBSITE"
   PINTEREST_REDIRECT_URI=http://localhost:5000/callback

   # Comma-separated scopes. Adjust to match what your app has been approved for.
   PINTEREST_SCOPES=user_accounts:read,boards:read,pins:read,ads:read

   # Pinterest's current auth and API endpoints.
   PINTEREST_AUTH_URL=https://www.pinterest.com/oauth/
   PINTEREST_TOKEN_URL=https://api.pinterest.com/v5/oauth/token
   PINTEREST_API_BASE_URL=https://api.pinterest.com/v5

   # Pinterest's docs describe a continuous refresh token flow. Keep this on unless
   # your app setup requires something else.
   PINTEREST_CONTINUOUS_REFRESH=true
   ```

4. In your Pinterest app settings, register the exact redirect URI:

   ```
   http://localhost:5000/callback
   ```

   Pinterest requires an exact match, so keep the scheme, host, port, path, and trailing slash exactly the same.

5. Run the app:

   ```powershell
   python app.py
   ```

   The app will be available at `http://localhost:5000`.

5. Run the Flask app.

```powershell
python app.py
```

6. Open `http://localhost:5000` and click `Connect Pinterest`.

## Notes on tokens

- The callback receives a one-time authorization `code`.
- The server exchanges that code for an OAuth `access_token`.
- If your app is using Pinterest's refreshable flow, the response can also include a `refresh_token`.
- The UI masks tokens on screen, but they are stored in the session for the duration of the browser session.

## Notes on ads access

OAuth does not guarantee ads data by itself. To get meaningful ads and analytics access, the authenticated user usually needs:

- A Pinterest business account
- Access to at least one Pinterest ads account
- The correct ads scopes approved for the app

If `Fetch /ad_accounts` returns empty data or a permission error, that usually means one of those pieces is missing.

## Important assumptions

This implementation uses the current Pinterest endpoints and token model reflected in their official developer docs:

- Authorization page: `https://www.pinterest.com/oauth/`
- Token exchange: `https://api.pinterest.com/v5/oauth/token`
- API base: `https://api.pinterest.com/v5`

Pinterest has changed token guidance over time, so if your app was created under an older setup you may need to adjust the refresh behavior in `.env`.


