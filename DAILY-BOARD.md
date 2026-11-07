# daily-board (بولتن روزانه) — project map for Claude sessions

Persian news dashboard on Iran–US–Israel tensions and the Strait of Hormuz. The engine runs on GitHub Actions and
publishes JSON to data branches; the app (`docs/`, GitHub Pages) reads them. Repo: `vagharia/daily-board`.
The owner writes in Persian and wants answers in Persian. Often he asks for analysis first ("فقط بررسی کن بدون
تغییر", "نظرت رو بگو"): then change nothing until he says so.

## Standing rules (never break)
- Never send, print or store the bot token. It lives only in the GitHub secret `TELEGRAM_BOT_TOKEN`; chat ids are sealed.
- Never take anything from Iranian messengers (Eitaa, Bale, Rubika or any other) and never access them.
- Anonymity: never put the owner's email anywhere. Commits are authored as `Claude <noreply@anthropic.com>`; data
  commits as `board-bot`.
- No update popup for changes without a new feature: bump the build silently (see Procedures). A popup only when he asks.
- Telegram-alert rules and bulletin rules are separate. Changing one must never change the other unless he asks.
- Telegram channels keep their own rules: one channel alone reporting a strike = red + "unconfirmed" in the bulletin.
- Leave as they are unless asked: the Vance-denial linking, the Fars prefix/teasers. Exclude Russia–Ukraine content.
- Sistan insurgent attacks (`classify.py` → `_domestic_attack`): the attack orange, never red; a casualty report or funeral yellow, unless 5+ killed.
- Store nothing from the owner's own X account; screenshots of X are not stored, nor anything about whose they were.
- Before a manual Telegram message to subscribers, the text is agreed with the owner.

## Where things are (engine/)
| Feature | File → place |
|---|---|
| Main loop, order of steps, migrations (`misc[...]`), lite files, story map for the panel | `run_news.py` → `main`, `news_round`, `lite` |
| Collecting feeds, Telegram pages, replies/admin comments, foreign (Arabic/French…) headlines dropped | `collect.py` → `collect_all`, `_tg_parse`, `follow_up_comment`, `not_english` |
| Severity / tiers (red ≥70, orange ≥45), yellow caps (`*_CAP`), Persian rules | `classify.py` (caps block in `classify()`), `classify_fa.py` → `score_fa` |
| Multi-item headlines ("A/ B", "A; B; C") → yellow, first item only; past ("weeks after"), no-deadline, "on the table" | `classify.py` → `multi_parts`, `PAST`, `_NO_DEADLINE_*`, `_TABLE_*` |
| Side fronts (Saudi–Houthi, Israel–Hezbollah in Lebanon): red only for a big turn (Saudi oil/energy hit, US sites in Saudi, wide airport damage, Red Sea ships under Hormuz-like rules (`_red_sea`); Lebanon only a war: invasion/offensive, ceasefire collapse, strikes across the country, heavy Hezbollah barrage or fire on Haifa/Tel Aviv, Hezbollah's own leader killed, the Lebanese state/army drawn in); orange ≤64 (`secondary`) only for attacks reaching Saudi soil; everything else yellow ≤40 (`minor` → flags `side_minor`): strikes inside Yemen, daily strikes anywhere in Lebanon (Beirut too), tallies («۱۰۵ بار»), casualty figures, threats/revenge, reactions, denials; index weighs them 25%, above 50 only the main front | `fronts.py` → `saudi_houthi`, `israel_lebanon`, `MINOR_CAP`, `_w` (whole Persian words: «عدن» ≠ «معدن», «صور» ≠ «صورت»); `classify.py` (`side_front`); `cluster.py` (`SECONDARY_CAP`, `MINOR_CAP`); `index.py` → `SIDE_W`, `MAIN_ONLY` |
| Controlled detonations (plural too, English translation as fallback) → yellow; advance notices («فردا … اجرا می‌شود»), strict → `scheduled`, orange ≤60, off the main front | `classify_fa.py` → `CONTROLLED`; `classify.py` → `CONTROLLED_TR`; `scheduled.py` → `notice`; `flash.py` → `drop_never_events` |
| Admin opinion/what-if on channels (به نظرم، اگر…، فرض کنید) | `classify.py` → `aside` |
| Executions/verdicts (اعدام، hanged, sentenced) → yellow ≤40, Sistan ones too; a spy for Israel/US executed → orange 54 only if the report tells of his part in the war (sites, coordinates, strikes, missiles, commanders…), else yellow | `classify.py` → `_judicial`, `SPY_WAR_SEV` |
| Protests/rallies outside the region → yellow (not when violent, not in Iran/Israel/Iraq/Gulf); verdicts, protests, "prevent escalation"/de-escalation talk stay yellow however many outlets (cluster cap) | `classify.py` → `_protest`, `_PREVENT_ESC`; `cluster.py` → `refresh` |
| Attack of an earlier year in a headline ("1983 bombing", «جنگ سال ۲۰۲۴»; not "since …") → past; "escalation"/«تشدید تنش» as a word 42 (yellow), not "de-escalation"; experts/analysts/researchers → analysis ≤44; "attacking X is a crime/…است" → statement ≤44 | `classify.py` → `past_year`, `EXPERTS`, `_JUDGED_EN`; `classify_fa.py` → `JUDGED`, `ANALYSIS` |
| English headline with nothing notable, scored only from its text → no event flag, yellow ≤44 unless the headline names the main front (Iran/US/Israel/Hormuz/Gulf/ships) → ≤52; strikes on air-defence systems/radars/launchers, "round of strikes", "Qeshm … hit" → orange kinetic (68/62) | `classify.py` → `score_en` (`_MAIN_EN`), `PATTERNS`; `classify_fa.py` (سامانه/پدافند) |
| Mediators visiting Tehran → orange | `classify.py` → `_mediator_visit` |
| Clustering, same-story rules, story-level caps, channel rules | `cluster.py` → `features`, `same_story`, `Clusterer`, scoring block after `ch_strike` |
| Same strike in other words (news only, same attacker + city, 12 h, no "new/again") | `cluster.py` → `strike_key`, `same_strike` |
| When it happened: a time label per event story (`c["ev"]` = from, to, how known: 0 first report −6 h, 1 first-hand report −12 h, 2 told in a headline); parts of the day in Tehran time (`_PART`: «بامداد» 00–05, «دیشب» 19–05, «صبح» 05–12…; Telegram keeps vessel.when); Bing-found reports and reports timed before the event set no label; a report placed at another time never joins; a told time can join an older story up to 48 h, and when several fit: time, then shared facts (spot, city, attacker, count, ship), then nearest time | `cluster.py` → `EV_ON`, `_ev_report`, `_part_of_day`, `_first_hand`, `Clusterer._ev_add`, `_ev_fits`, `_ev_late`, `_facts` |
| Qeshm, Kish, Abu Musa: places of their own; Qeshm and Abu Musa within the Hormuz area for matching | `lexicon.py` → `PLACES`; `cluster.py` → `REGION` |
| "Source not stated" vs relayed outlet (unknown outlets, «روزنامه آمریکایی X») | `citation.py` → `outlet_named`, `OTHER` |
| Ships/tankers: marks (distance + bearing from ports in Hormuz, Persian Gulf, Arabian Sea, Red Sea), sea areas, time (`when(fine=True)`: «بامداد امروز», "3 hours ago", local clock), kind of ship (tanker/super/LNG/container…), flag, owner, name, ship counts, Iranian statements | `vessel.py` (`REFS`, `AREAS`, `mark`, `area`, `when`, `kinds`, `flag`, `owner`, `name`, `ship_id`, `counts`, `statement`, `signature`) |
| Same ship/incident in the bulletin: kind/flag/owner/name must fit; same owner + kind + area joins | `cluster.py` → `same_story` (sid), `_ship_misfit`, `_own_matches` |
| Telegram: one alert per incident at sea, repeated Iranian claims (24 h; a new statement — 2+ Iranian agencies within an hour, or "two more" — only 6 h), update only for sinking/casualties/who/seizure (also from a report joining a story already announced, headline only, one per incident) | `alerts.py` → `_sea_pick`, `_claim_told`, `_fresh`, `_later`, `SEA_NEWS` |
| Deployments (count, kind, destination) | `deploy.py` |
| Evacuation orders (one story per order, 7 days; stale "effective <date>") | `evac.py` |
| Telegram red alerts, sea rules, lights, late-report rule | `alerts.py` → `run`, `_sea_pick`, `_late` |
| Main-front panel + instant Telegram alerts (flash), "not confirmed" mark | `flash.py` → `events`, `process`, `_news_ok`, `mark_denied` |
| Not of the moment: statements, relayed outlets, past times, videos, a channel retelling the news | `flash.py` → `told_later`, `_news_ok`, `news0` in `process` |
| Lights: deployment/ultimatum only from a headline (`tf`) | `index.py` → `compute_lights`; `classify.py` sets `item["tf"]` |
| Tension index, direct strikes, lights | `index.py` → `index_value`, `direct_strikes`, `pressure`, `compute_lights` |
| Citizen reports (witness), cities | `witness.py` |
| X posts (manual screenshots in `engine/xmanual/posts.json`) | `xposts.py` |
| Israel election (Knesset) | `election.py` → branch `election` |
| US midterms (AP feed) | `uselection.py` → branch `uselection` |

Workflows: `live.yml` (news engine; push on `engine/**` restarts it), `election.yml`, `uselection.yml`, `ticker.yml`,
`news.yml`, `assets.yml`. Files at the repo root and in `docs/` don't trigger the engine.

## App (docs/)
`app.js` sections (search the banner comments `// ---- name`): strings (fa/en dicts), stories, story tray,
Israel's election, the US midterms, main front (flash), sheet, map, X, Economist, refresh loop, what's new.
Styles in `app.css` (US story at the end). Map shapes: `docs/us-states.json`. Version: `APP_REL`, `APP_BUILD`
in `app.js`; `?v=N` in `index.html`; `SHELL` in `sw.js`; `docs/release.json` (`v` = popup, `build` = silent).

## Procedures
- **Silent build bump:** APP_BUILD +1, every `?v=` and `shell-vN` +1, release.json `build` +1; keep `v`.
- **Popup release:** also `v` +1 and `APP_REL` +1, with fa/en items in release.json.
- **Hand edit of data:** cancel live runs; `git archive origin/data` to a scratch folder; edit
  `state/clusters.json` (markers: `manual`, `ongoing`, `fixed`, `merged`; add ids to `state/alerts.json` `sent` so
  no alert goes); commit the tree as board-bot with a separate `GIT_INDEX_FILE`; push with
  `--force-with-lease=refs/heads/data:<tip>`; `gh workflow run live.yml --ref main`.
- **Check a change went live:** note the push time, wait for the first run of the new commit (`headSha`), then the
  first data publish after it, and check only the stories concerned in `origin/data:state/clusters.json`. Don't
  wait for a run to finish: live runs loop for a long time.
- **One-off Telegram notice:** restore `tools/notice.py`, `tools/notice.txt`, `.github/workflows/notice.yml` from
  commit 838fcd3, run with input `to` (owner/others/all), then delete them again.
- The shell can't reach outside sites; probe them with a temporary workflow and push results to a scratch branch.
  `gh` can't use GraphQL or delete branches here.
- Mirror copy: changed files are also copied to `/home/claude/daily-board` when that folder exists.
