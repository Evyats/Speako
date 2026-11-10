# Master plan

# Task tracking

## Isolated Windows installation
- Owner: Codex
- Status: Implementation complete; verified
- [x] Add repeatable local environment setup and Desktop shortcut creation.
- [x] Install dependencies and verify isolation, tests, and shortcut startup.
- [x] Document setup and review changes.
- Verification: 10 tests passed; pip check passed; all six runtime dependencies
  resolve inside .venv; tray/controller smoke test initialized and exited cleanly;
  Desktop shortcut launched successfully. Live transcription was not exercised.
