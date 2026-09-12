# HELIOS security model

🌐 [Русский](security-ru.md) · [Español](security-es.md) · **Audit:** [SECURITY-AUDIT.md](SECURITY-AUDIT.md)

HELIOS holds YouTube OAuth credentials and uploads to a production channel.

## Threat model

| # | Threat | Impact |
|---|--------|--------|
| T1 | Compromised operator host | Attacker uploads or publishes to channel |
| T2 | Malicious job injection | Arbitrary file read via `render_path` or shell via ffmpeg |
| T3 | Inbound HTTP abuse (v1.1) | Unauthorized job creation with stolen API key |
| T4 | LLM Director prompt injection | Bad metadata approved (not VO — charter forbids) |
| T5 | Path traversal in templates | Read files outside `asset_roots` |

**Non-goals:** engagement automation on YouTube.

## Controls (implemented)

| Layer | Control | Module |
|-------|---------|--------|
| Secrets | Env / `*_FILE` only; excluded from satellite rsync | `config.py`, `satellite-map.yaml` |
| Upload privacy | Default `private`; `helios approve` for public | `worker.py` |
| Template vars | Whitelist keys; NFKC sanitize; length cap | `security.py` |
| Asset paths | Resolve only under `asset_roots`; no `..` | `security.py` |
| Pre-rendered files | `validate_existing_file()` under roots | `queue.py`, `ingest.py` |
| ffmpeg args | `safe_subprocess_arg` — no shell, block `;|&$` | `security.py`, renderer |
| Idempotency | Duplicate `idempotency_key` → no re-upload | `queue.py` |
| Ingest | Invalid lines stay in queue; valid lines validated | `ingest.py` |
| Audit | Append-only `audit.jsonl` | `audit.py` |
| HTTP v0.1 | `GET /health` only — no body parsing | `health.py` |
| Director | Metadata only; fail-open on error; daily LLM cap | `director.py`, `llm.py` |
| Docker | non-root, read-only rootfs, cap_drop ALL | `Dockerfile`, `docker-compose.yml` |

## Operator checklist

- [ ] `chmod 600` on OAuth JSON files
- [ ] Set `HELIOS_API_KEY` before enabling POST routes (v1.1)
- [ ] Review private videos in Studio before `helios approve`
- [ ] Rotate OAuth token if host compromised
- [ ] Run `./scripts/publish_all_repos.sh --satellite helios` only after `verify_mirror_secrets.sh`

## Residual risks

| Risk | Mitigation plan |
|------|-----------------|
| Director fail-open approves bad metadata | Human Studio review before approve; tighten Director in v0.2 |
| Operator approves without watching | Process/policy; optional `--force-public` disabled in v0.1 |
| YouTube token on disk | File permissions; short-lived refresh; consider secret manager v0.2 |
