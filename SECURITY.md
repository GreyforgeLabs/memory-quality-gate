# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest  | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly.

**Do NOT open a public issue.**

Instead, use one of these methods:

1. **GitHub Security Advisories** (preferred): Use the "Report a vulnerability" button on the Security tab of this repository.
2. **Email**: Contact the maintainers through [greyforge.tech](https://greyforge.tech).

## Security Notes

- `memory-quality-gate` does not execute shell commands or call external services.
- The CLI only reads local files explicitly passed with `--file` or `--existing-file`.
  Do not expose raw path arguments to untrusted users in web, bot, or CI wrappers.
- The CLI applies default input caps of 1,000,000 UTF-8 bytes for candidate text
  and 5,000,000 UTF-8 bytes for `--existing-file`; operators can override them
  with `--max-input-bytes` and `--max-existing-bytes`.
- JSON output includes candidate text unless `--redact-text` is used. Treat
  candidate text as untrusted and potentially sensitive when writing logs.
- A passing score means "probably useful to remember," not "safe to trust."
  Downstream memory systems still need authentication, authorization, privacy
  filtering, prompt-injection defenses, and scope isolation.
- The project is designed to run without runtime dependencies.

## What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

## Response Timeline

- **Acknowledgment**: Within 48 hours
- **Assessment**: Within 7 days
- **Fix or mitigation**: Depends on severity, but we aim for 30 days for critical issues

## Disclosure

We follow coordinated disclosure. Please allow us reasonable time to address the issue before making it public.

---

Built by [Greyforge](https://greyforge.tech)
