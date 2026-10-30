# Posts from screenshots of X

X has no free API, and most accounts' timelines can't be read from a server. So once a day the owner may send
screenshots of posts from the followed accounts (the list is `WHITELIST` in `engine/xposts.py`). Each post is typed
into `posts.json` and shows in the X tab like any other post for three days.

```json
{"h": "araghchi", "n": "Seyed Abbas Araghchi", "t": "2026-10-26T09:12:00Z", "seg": "geo",
 "text": "the post as written", "fa": "Persian translation", "en": "English translation",
 "url": "https://x.com/araghchi/status/… when the link is known, otherwise left out"}
```

- `t` is in UTC, worked out from the time shown in the screenshot and when it was sent.
- `seg` is `geo` (politics and military) or `econ` (oil, gold, markets); left out, it follows the account's own.
- Only posts from followed accounts, on the region's conflict or on oil, gold and markets; nothing about the war
  between Russia and Ukraine. A post another account wrote and a followed account shared counts too: it keeps its
  own author (`h`, `n`) and gets `role_fa` / `role_en` saying who that is and who shared it.
- Nothing about the account the screenshots were taken from (its name, picture, likes or replies) is ever written
  here, and the screenshots themselves are not stored.
- Each new batch replaces the file; posts already published stay in the tab for their three days.
