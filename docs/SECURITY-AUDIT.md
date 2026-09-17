# HELIOS — security audit report

**Date:** 2026-07-07  
**Scope:** `helios/` satellite v0.1  
**Auditor:** automated + manual code review

## Executive summary

HELIOS v0.1 is **suitable for operator-controlled deployment** with the documented charter constraints. No critical vulnerabilities found after hardening `render_path` validation. Residual risks are operational (human approve gate, Director fail-open).

## File size audit (no god files)

| File | Lines | Verdict |
|------|-------|---------|
| `queue.py` | ~250 | OK — single responsibility |
| `cli.py` | ~220 | OK — thin command router |
| `worker.py` | ~210 | OK |
| `config.py` | ~195 | OK |
| All others | <120 | OK |

**Threshold:** no file >400 lines. **Pass.**

## Findings

### FIXED — High: unrestricted `render_path` on ingest/enqueue

**Before:** Jobs could reference arbitrary filesystem paths.  
**After:** `validate_existing_file()` ensures paths resolve under `asset_roots` / `promo_materials_dir`.  
**Tests:** `test_security.py::test_validate_existing_file_*`

### FIXED — Medium: missing idempotency key validation

**After:** `validate_idempotency_key()` — alphanumeric + `:/._-` only, max 256 chars.

### FIXED — Medium: unvalidated `source` field

**After:** `validate_source()` — lowercase identifier pattern.

### ACCEPTED — Low: Director fail-open on LLM error

**Rationale:** Availability over blocking uploads; human Studio review is mandatory before public.  
**Recommendation:** Add `director.strict=1` in v0.2 to fail-closed.

### ACCEPTED — Low: TTS passes VO through subprocess argv

**Mitigation:** `safe_subprocess_arg` blocks shell metacharacters; VO comes from trusted yaml templates only (not user input in v0.1).

### INFO: HTTP surface minimal

v0.1 exposes only `GET /health` with no request body parsing — injection surface inert by construction (same pattern as DIOSCURI).

## Checklist results

| Check | Status |
|-------|--------|
| Secrets in git | PASS — `.gitignore` + `satellite-map.yaml` exclude_paths |
| OAuth files in mirror | PASS — excluded |
| Path sandbox | PASS — after fix |
| Shell injection | PASS — list argv, no `shell=True` |
| Idempotent uploads | PASS |
| Audit trail | PASS |
| Docker hardening | PASS |
| Unit test coverage | PASS — see `tests/` |

## Recommendations (v0.2)

1. `POST /v1/jobs` with Bearer `HELIOS_API_KEY` + request schema validation
2. Director fail-closed mode (config flag)
3. Hash-chained audit like DIOSCURI
4. `edge-tts` as optional Docker dependency
