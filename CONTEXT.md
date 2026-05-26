# Scholar Labs CLI

Scholar Labs CLI is an open-source command-line tool for searching Google Scholar Labs from a terminal. Its domain centers on translating a user's research question into Scholar Labs results while respecting the boundaries of an unofficial Google surface.

## Language

**Community User**:
A person who installs and runs the open-source CLI on their own machine, outside the maintainers' direct control.
_Avoid_: Internal user, trusted operator

**Authenticated Browser Session**:
A Google login state that already exists in a user's local browser profile and may allow access to Scholar Labs.
_Avoid_: Google account, OAuth session

**Primary Browser Profile**:
The user's regular browser profile where their existing Google login state is expected to live.
_Avoid_: Headless profile, tool profile

**Supported Browser Environment**:
The operating system and browser combination where CLI Login is expected to automatically read Scholar Labs Credentials from the Primary Browser Profile.
_Avoid_: Any browser, cross-platform support

**Scholar Labs Credentials**:
The short-lived request material needed to call the Scholar Labs session endpoint, currently represented by a browser cookie header and XSRF token.
_Avoid_: API key, OAuth token

**XSRF Discovery**:
The process of deriving the Scholar Labs XSRF token from a Scholar Labs page response using extracted browser cookies.
_Avoid_: Network capture, manual token copy

**Browser Credential Extraction**:
The CLI Login mechanism that reads Scholar Labs Credentials from the Primary Browser Profile instead of asking the Community User to copy them manually.
_Avoid_: OAuth login, browser automation

**Credential Source Record**:
Local metadata that records where Scholar Labs Credentials should be read from, without storing a full Google cookie header.
_Avoid_: Stored cookie, exported credentials

**Auth Config**:
The versioned local authentication file that records either a Credential Source Record or Manual Auth Fallback credentials.
_Avoid_: Legacy auth.json, unversioned credentials

**Legacy Auth Config**:
An old unversioned local authentication file that stores cookie and XSRF values directly.
_Avoid_: Auth Config, migration source

**Read-Only Profile Access**:
Access to the Primary Browser Profile that copies browser data to a temporary location before inspection and never modifies browser-owned files.
_Avoid_: Profile mutation, browser cleanup

**User-Guided Browser Recovery**:
A recovery flow where the CLI opens Scholar Labs in the user's browser and waits for the user to complete any required Google login or page initialization.
_Avoid_: Automated Google login, credential autofill

**Browser Auth Extension**:
An optional installation capability that enables Browser Credential Extraction while keeping the base CLI usable with Manual Credential Capture.
_Avoid_: Required dependency, core auth

**Interactive Auth Prompt**:
A terminal prompt that may start CLI Login only when the Community User is running the CLI interactively.
_Avoid_: Background login, CI login

**Search Command**:
The explicit CLI command that submits a research question to Scholar Labs.
_Avoid_: Root query argument, implicit search

**Root Command**:
The base `sls` command, which introduces available commands but does not submit a search query.
_Avoid_: Search shortcut

**Manual Credential Capture**:
The current flow where a user copies Scholar Labs credentials from browser developer tools into environment variables or a local config file.
_Avoid_: Login, OAuth

**Manual Auth Fallback**:
A supported authentication path for environments where Browser Credential Extraction is unavailable or fails.
_Avoid_: Primary login, deprecated auth

**CLI Login**:
An interactive command that helps a Community User reuse an Authenticated Browser Session and stores Scholar Labs Credentials locally for future CLI searches.
_Avoid_: Manual setup, OAuth login, account login

**Auth Maintenance Command**:
A secondary CLI command for inspecting, clearing, or manually configuring authentication state.
_Avoid_: Login shortcut, search command

## Example Dialogue

Developer: "Can we make login automatic?"

Domain expert: "For a Community User, automatic login must not imply Google OAuth. The CLI can reuse an Authenticated Browser Session if the user explicitly allows local extraction of Scholar Labs Credentials."

Developer: "How should the CLI find the XSRF token?"

Domain expert: "Use XSRF Discovery against Scholar Labs pages first. If that fails, use User-Guided Browser Recovery rather than browser network capture."

Developer: "So the current README steps are Manual Credential Capture?"

Domain expert: "Yes. It is acceptable as a fallback, but it should not be the primary experience for an open-source CLI."

Developer: "Should manual cookie setup remain supported?"

Domain expert: "Yes, as Manual Auth Fallback. It should remain documented and available, but not presented as the primary path."

Developer: "What should `sls login` mean?"

Domain expert: "It means CLI Login: the command should open or inspect a browser session and capture Scholar Labs Credentials without asking the user to copy request headers by hand."

Developer: "Where should status and logout commands live?"

Domain expert: "CLI Login should remain a top-level command, while status, logout, and manual setup belong under Auth Maintenance Commands."

Developer: "Should CLI Login use a separate browser profile?"

Domain expert: "No. By default it should use the Primary Browser Profile so the Community User can reuse their existing Google login state."

Developer: "Which browser environments are expected to work first?"

Domain expert: "The first Supported Browser Environment is macOS with Chrome or Chromium-family browsers. Other environments should remain explicit fallbacks until they are deliberately supported."

Developer: "How should CLI Login obtain credentials from that environment?"

Domain expert: "Use Browser Credential Extraction from the Chrome cookie database with macOS Keychain decryption, then validate the extracted credentials against Scholar Labs."

Developer: "Should CLI Login store the extracted Google cookie header?"

Domain expert: "No. It should store a Credential Source Record by default and re-extract current cookies from the Primary Browser Profile when needed."

Developer: "Should new authentication code accept the old unversioned config file shape?"

Domain expert: "No. Auth Config should be versioned from this point forward, and old unversioned credential files should be rejected with migration instructions."

Developer: "Should the CLI automatically migrate or back up old auth files?"

Domain expert: "No. A Legacy Auth Config may contain sensitive cookie material, so the CLI should report it with migration instructions rather than copying, renaming, or transforming it automatically."

Developer: "May the CLI read Chrome's cookie database while Chrome is running?"

Domain expert: "Yes, but only through Read-Only Profile Access: copy the cookie database to a temporary file, inspect that copy, and never modify the Primary Browser Profile."

Developer: "What if Browser Credential Extraction cannot access Scholar Labs?"

Domain expert: "Use User-Guided Browser Recovery: open Scholar Labs in the browser, wait for the Community User to complete login or initialization, then retry extraction."

Developer: "Should browser credential support be part of every installation?"

Domain expert: "No. Browser Credential Extraction should live in a Browser Auth Extension so the base CLI remains small and manual authentication remains available."

Developer: "May a search command start CLI Login?"

Domain expert: "Yes, but only through an Interactive Auth Prompt. Non-interactive commands should fail with instructions instead of opening a browser or waiting for input."

Developer: "Should the root command remain the search entry point?"

Domain expert: "No. Search should be an explicit Search Command, such as `sls search <query>`, and the root query argument should be deprecated."

Developer: "Should the old root query behavior remain temporarily?"

Domain expert: "No. The Root Command should stop accepting a query directly and should show command help instead."
