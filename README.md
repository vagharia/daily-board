# Daily Brief

A personal news brief that works as a mobile web app.

- `engine/` collects news from a fixed list of sources, scores and groups stories, translates them,
  and reads air, sea and market signals. GitHub Actions runs it every 30 minutes (news) and every
  5 minutes (prices) and writes JSON to the `data` branch.
- `docs/` is the app, served by GitHub Pages.

Optional alerts: save a Telegram bot token as the repository secret `TELEGRAM_BOT_TOKEN`, then send
`/start` to the bot.
