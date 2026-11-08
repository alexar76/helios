# Changelog

Notable changes to `helios-broadcast`. Earlier releases: the git history.

## 0.2.2 — 2026-11-08

### Fixed
- **A video an operator withdrew is not published again.** The worker could read its backlog before an operator hid
  a video, and then publish it anyway. Publication now takes a per-job lock that the worker and the operator CLI
  share, and re-reads the job before it acts; withdrawn videos have their own status, `unpublished`. At startup,
  jobs waiting for approval whose history is uncertain are not published automatically. Making a scheduled video
  private also cancels its scheduled release.
- Rendering needs `edge-tts>=7.3.1`: the Edge read-aloud service answers 7.2.8 with 403 (2026-11-05). `pillow>=13.0.0`.
