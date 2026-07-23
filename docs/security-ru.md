# HELIOS — модель безопасности

🌐 [English](security.md) · [Español](security-es.md) · **Аудит:** [SECURITY-AUDIT.md](SECURITY-AUDIT.md)

## Модель угроз

| # | Угроза | Влияние |
|---|--------|---------|
| T1 | Компрометация хоста оператора | Upload/publish на канал |
| T2 | Вредоносный job | Чтение файлов через `render_path`, injection в ffmpeg |
| T3 | HTTP abuse (v1.1) | Создание jobs с украденным API key |
| T4 | Prompt injection в Director | Плохие метаданные (не VO) |
| T5 | Path traversal | Чтение вне `asset_roots` |

## Контроли

| Слой | Контроль |
|------|----------|
| Секреты | Только env; исключены из rsync |
| Privacy | `private` по умолчанию |
| Vars | Whitelist + sanitize |
| Пути | `asset_roots` + `validate_existing_file` |
| ffmpeg | Без shell, блок метасимволов |
| Audit | `audit.jsonl` append-only |
| HTTP | Только `GET /health` (v0.1) |
| Docker | non-root, cap_drop ALL |

## Чеклист оператора

- [ ] `chmod 600` на OAuth JSON
- [ ] Ревью в Studio перед `helios approve`
- [ ] Ротация токена при компрометации
