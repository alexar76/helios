# HELIOS — AIMarket 生态的广播层

> 🌐 [English](README.md) · [Русский](README-ru.md) · [Español](README-es.md) · [Français](README-fr.md) · **中文** · [术语表](https://github.com/alexar76/aicom/blob/main/docs/localization-glossary.md)


> **模板进 → 配音视频出 → 进入 YouTube 队列 — 默认 private，直到 approve。**  
> MIT · 自托管 · 仅发布 · 无互动机器人。

**落地页：** [alexar76.github.io/helios](https://alexar76.github.io/helios/) · **GitHub：** [alexar76/helios](https://github.com/alexar76/helios) · **YouTube：** [@My-AI-Factory](https://www.youtube.com/@My-AI-Factory)

| | |
|---|---|
| **角色** | 从 yaml 模板渲染 MP4 → 上传 YouTube（默认 private）→ 运营 approve → public |
| **Monitor** | [Alien Monitor](https://monitor.modelmarket.dev/) — 点击 **HELIOS** → 频道统计 |
| **集成** | [helios-integration.md](https://github.com/alexar76/aicom/blob/main/docs/ecosystem/helios-integration.md) |

## 为何需要 HELIOS

`alexar76` 生态持续变化：发布、预言机、课程、展示。PromoMaterials 手动流水线无法扩展。**HELIOS** 是独立广播卫星：任务队列、审计日志、发布前人工门控。

## Charter（强制规则）

1. **POST-only** — 只发自己的频道；不点赞、不评论、不关注。
2. **Template-only** — 视频仅来自已校验 yaml；口播文案固定在模板中。
3. **Private-first** — 上传始终 `private`；仅 `helios approve` 可公开。
4. **Human gate** — 运营在 Studio 审片后再 approve。
5. **Fail-soft** — HELIOS 宕机时 Factory 与 DIOSCURI 继续运行。

## 能力

| 能力 | 说明 |
|-------------|----------|
| 队列 | 幂等、日限额（~9/天）、防崩溃锁 |
| 渲染 | TTS（macOS `say`）+ ffmpeg + 字幕 |
| YouTube API | 可续传上传、SRT、播放列表 |
| Backfill | 上传 PromoMaterials 中已渲染分集 |
| Director | LLM 审元数据（DeepSeek）— **不写**口播 |
| Alien Monitor | 图节点上的缓存频道统计 |
| Audit | 仅追加的 `data/audit.jsonl` |

## 快速开始

```bash
cd helios
pip install -e ".[dev]"
cp helios.config.example.yaml helios.config.yaml
cp .env.example .env
helios auth
docker compose up -d --build
helios backfill-scan && helios backfill-enqueue -n 10
docker exec helios helios worker
helios approve job_backfill_e10
```

## 文档

见 `docs/setup*.md`、`usage*.md`、`architecture*.md`、`security*.md`、`runbook*.md`。

## 许可

MIT — [LICENSE](LICENSE).
