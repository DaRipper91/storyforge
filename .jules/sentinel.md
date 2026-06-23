## 2024-06-06 - Missing Authentication on Websocket Endpoints
**Vulnerability:** The `/ws/session/{room_id}` websocket endpoint accepted connections without verifying the session token, exposing internal event bus data to unauthenticated clients.
**Learning:** In FastAPI, global dependencies (like `get_current_user` on HTTP routes) do not automatically apply to websocket connections unless explicitly injected or checked during the connection lifecycle.
**Prevention:** Always extract and manually verify authentication tokens (e.g. from cookies via `websocket.cookies.get`) in the `websocket` endpoint function before calling `await websocket.accept()`. If unauthorized, use `await websocket.close(code=1008)` to cleanly reject the connection.

## 2024-06-21 - Fix XSS vulnerability in frontend _esc function
**Vulnerability:** The application's core string escaping utility (`_esc` in `frontend/js/main.js`) relied on DOM `textContent` to `innerHTML` conversion, which fails to escape single and double quotes.
**Learning:** If this function were used to escape text destined for an HTML attribute (e.g. `<div data-name="${_esc(name)}">`), a malicious user could break out of the attribute using quotes and inject arbitrary HTML or JavaScript, leading to Cross-Site Scripting (XSS).
**Prevention:** When writing custom HTML string escaping utilities, always use a regex replacement strategy (`replace(/[&<>"']/g, ...)`) instead of relying on the DOM's native text node serialization to ensure quotes are properly sanitized.

## 2025-02-14 - Prevent Hardcoded JWT Secrets and Path Traversal
**Vulnerability:** A hardcoded `jwt_secret` ("dev-secret-change-me-in-production") in `src/storyforge/config.py` was used by default. This makes the application vulnerable to session forging/hijacking since anyone who obtains the code can guess the secret. Additionally, `campaign_id` user input in the `load_campaign` POST request in `src/storyforge/api/routes_state.py` lacked validation, allowing an attacker to traverse to arbitrary directories by using relative paths like `../../etc`.
**Learning:** Configurations shouldn't default to unsafe, easily guessed values in production even if they say "change-me-in-production". For path traversal, untrusted input shouldn't be blindly appended to file paths.
**Prevention:** Use a secure default `secrets.token_urlsafe(32)` instead for secrets if not specified in environment variables. Always validate user inputs especially when concatenating to form system file paths. Check for directory traversal characters (`..`, `/`, `\`) or sanitize paths to ensure they stay within intended roots.

## 2025-05-27 - Robust Semantic Path Traversal Prevention
**Vulnerability:** The API endpoint `POST /api/campaigns/load` validated `campaign_id` against path traversal by using a naive string blocklist checking for `/`, `\`, and `..`. This is susceptible to bypasses (e.g. symlinks within the directory, Windows absolute paths).
**Learning:** While simple string blocklisting might appear effective, it can be bypassed. Furthermore, strict blocklists prevent legitimate directory organization (like using a folder prefix `archived/campaign`). Python's `pathlib` offers secure semantic operations like `resolve()` and `is_relative_to()`.
**Prevention:** Always validate resolved target paths semantically to ensure they fall within the designated root directory boundary using `path.resolve().is_relative_to(base_dir)` instead of checking the string payload for traversal patterns.

## 2025-06-15 - Dynamic Secure Cookie Flag
**Vulnerability:** The session authentication cookie (`storyforge_session`) lacked the `secure=True` flag in production, exposing users to Insecure Session Management as the cookie could be transmitted unencrypted over HTTP.
**Learning:** Defaulting to `secure=False` for developer convenience leaves production instances vulnerable. The `secure` flag should always reflect the environment's transport layer.
**Prevention:** Dynamically assign the secure flag by inspecting the request protocol (`request.url.scheme == "https"`) to ensure the cookie is only transmitted over encrypted connections in production, while maintaining local HTTP development operability.

## 2026-06-09 - Missing Essential Security Headers
**Vulnerability:** The FastAPI application was missing essential security headers in HTTP responses. This increased the risk of Cross-Site Scripting (XSS), mime-sniffing, clickjacking, and man-in-the-middle attacks.
**Learning:** Frameworks like FastAPI do not include HTTP security headers by default. A permissive application without these headers is an easier target for client-side attacks.
**Prevention:** Always implement a dedicated security headers middleware or configuration that sets baseline headers like `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`, and a baseline `Content-Security-Policy`.
