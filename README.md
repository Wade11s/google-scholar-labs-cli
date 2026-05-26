# scholar-labs-cli

Search Google Scholar Labs from your terminal.

## Install

```bash
uv pip install -e .
```

## Configure Authentication

### Option 1: Environment variables

```bash
export SCHOLAR_COOKIE='your-google-cookie'
export SCHOLAR_XSRF_TOKEN='your-xsrf-token'
```

### Option 2: Config file

Create `~/.scholar-labs-cli/auth.json`:

```json
{"cookie": "your-cookie", "xsrf_token": "your-xsrf-token"}
```

### Getting credentials

You need two values from your browser: the **Cookie** (proves you're logged in to Google) and the **XSRF Token** (CSRF protection token from the page URL).

#### Step 1: Open Scholar Labs

Open Chrome and go to https://scholar.google.com/scholar_labs/search?hl=zh-CN

Make sure you're logged in to your Google account (you'll see your avatar in the top-right corner).

#### Step 2: Open DevTools

Press `F12` (or `Cmd+Option+I` on macOS) to open Chrome DevTools. Switch to the **Network** tab.

#### Step 3: Perform a search

Type any query into the search box (e.g., "test") and press Enter. You'll see network requests appear in the DevTools panel.

#### Step 4: Find the session_data request

In the Network tab, look for a request named **`session_data`** (use the filter box at the top to narrow results). Click on it.

The request URL will look like:

```
https://scholar.google.com/scholar_labs/search/session_data?hl=zh-CN&xsrf=AFPfF8cAAAA...
```

#### Step 5: Copy the XSRF Token

From the request URL, copy the value of the `xsrf` parameter (the long string after `xsrf=` until the end or `&`).

```
Example: AFPfF8cAAAAAahZqaz6mDsg73bA-8Xml7fBUGAA
```

This is your `SCHOLAR_XSRF_TOKEN`.

#### Step 6: Copy the Cookie

In the right panel showing the request details, scroll to **Request Headers**. Find the `Cookie` header. Copy its entire value — it's a long string containing multiple `key=value` pairs separated by `; `.

```
Example: APISID=6XCSAKbOGAdkoySP/...; SAPISID=...; SID=...; __Secure-3PSID=...
```

This is your `SCHOLAR_COOKIE`. Copy the whole thing — all the key=value pairs, exactly as shown.

#### Step 7: Configure

Set the environment variables:

```bash
export SCHOLAR_COOKIE='<paste-the-entire-cookie-string>'
export SCHOLAR_XSRF_TOKEN='<paste-the-xsrf-token>'
```

Or save them to `~/.scholar-labs-cli/auth.json`:

```json
{"cookie": "<paste-cookie-here>", "xsrf_token": "<paste-xsrf-here>"}
```

> **Note**: Google cookies expire periodically. If you start getting authentication errors, repeat these steps to get fresh credentials.

## Usage

```bash
# Basic search
sls "large language model safety"

# JSON output
sls "transformer architecture" --json
```
