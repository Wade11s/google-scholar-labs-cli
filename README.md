# scholar-labs-cli

Search Google Scholar Labs from your terminal.

## For Agents

```bash
# Install uv (if not present)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the CLI
uv tool install git+https://github.com/Wade11s/google-scholar-labs-cli.git

# Authenticate (interactive — requires existing Chrome login)
sls login

# Search
sls search "your research query"
```

## Quick Start

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install the CLI

```bash
uv tool install git+https://github.com/Wade11s/google-scholar-labs-cli.git
```

### 3. Authenticate

```bash
sls login
```

### 4. Search

```bash
sls search "large language model safety"
```

## Authentication

### Primary path: browser login

```bash
sls login
```

`sls login` reuses your existing Google login state from your primary Chrome/Chromium profile. It is not Google OAuth and it does not automate Google username/password entry.

The first supported automatic browser environment is macOS with Chrome or Chromium-family browsers. If the CLI cannot read or validate your browser session, it opens Scholar Labs and asks you to complete Google login or page initialization yourself, then retries.

Browser login stores a versioned credential source record, not a full Google Cookie header:

```json
{
  "version": 1,
  "method": "chrome-profile",
  "browser": "chrome",
  "profile": "Default",
  "profile_path": "/Users/you/Library/Application Support/Google/Chrome/Default",
  "validated_at": "2026-05-26T00:00:00+00:00"
}
```

### Manual fallback

Use manual auth when automatic browser extraction is not supported in your environment:

```bash
sls auth manual
```

This writes a versioned manual auth config:

```json
{
  "version": 1,
  "method": "manual",
  "cookie": "<your-cookie>",
  "xsrf_token": "<your-xsrf-token>",
  "validated_at": "2026-05-26T00:00:00+00:00"
}
```

### Environment variable override

Environment variables have the highest priority. They are useful for scripts, CI, and temporary overrides:

```bash
export SCHOLAR_COOKIE='your-google-cookie'
export SCHOLAR_XSRF_TOKEN='your-xsrf-token'
```

### Auth maintenance

```bash
sls auth status
sls auth logout
```

`sls auth status` never prints full cookies or full Scholar Labs credentials. `sls auth logout` only removes local CLI auth config; it does not log you out of Chrome or modify your browser profile.

### Legacy config

Old unversioned auth files are no longer supported:

```json
{"cookie": "your-cookie", "xsrf_token": "your-xsrf-token"}
```

If this file exists, run `sls login` or `sls auth manual` to create a new versioned auth config. The CLI does not automatically migrate, back up, or copy legacy cookie files.

## Usage

```bash
# Basic search
sls search "large language model safety"

# JSON output
sls search "transformer architecture" --json
```
