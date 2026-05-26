# Browser Profile Auth

Scholar Labs CLI will make `sls login` default to extracting Scholar Labs credentials from the user's Primary Browser Profile, starting with macOS Chrome/Chromium. This is a deliberate open-source trade-off: it optimizes away Manual Credential Capture while keeping the behavior explicit, local, and scoped to read-only browser data access rather than claiming Google OAuth support.

## Considered Options

- **Manual Credential Capture only**: simplest to maintain, but too tedious to be the primary open-source experience.
- **CLI-owned browser profile**: clearer isolation, but requires users to log into Google again and misses the main value of reusing an existing browser session.
- **Primary Browser Profile extraction**: best user experience, but requires careful platform scoping, clear consent, and conservative local storage.

## Consequences

The first Supported Browser Environment is macOS with Chrome/Chromium-family browsers. Browser Credential Extraction must use Read-Only Profile Access, must not modify browser-owned files, and must not store a full Google cookie header by default. The CLI should store a Credential Source Record, re-extract current cookies when needed, and use User-Guided Browser Recovery when the existing browser session cannot access Scholar Labs.

Auth Config is versioned from this decision forward. Legacy unversioned auth files are rejected with migration instructions instead of being automatically migrated, backed up, or copied. XSRF Discovery should use Scholar Labs page responses before considering heavier browser network capture approaches.
