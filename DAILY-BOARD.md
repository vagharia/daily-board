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
| Side fronts: red only for a big turn (Saudi oil/energy hit, US sites in Saudi, wide airport damage, Red Sea ships under Hormuz rules; Lebanon only a war: invasion, ceasefire collapse, heavy barrage, Lebanese state drawn in); orange ≤64 only for attacks on Saudi soil; the rest yellow ≤40 (`minor`: strikes in Yemen, daily Lebanon strikes, tallies, threats, reactions); Persian place names as whole words (`_w`); «فلسطین اشغالی»/«سرزمین‌های اشغالی» = Israel (main front); a Houthi hit on an Israeli place (Eilat…) with casualties is not a Yemen toll (`_local_region`) | `fronts.py`; `classify.py` (`side_front`); `cluster.py` (`MINOR_CAP`); `index.py` → `SIDE_W` |
| Controlled detonations (plural too, English translation as fallback) → yellow; advance notices («فردا … اجرا می‌شود»), strict → `scheduled`, orange ≤60, off the main front | `classify_fa.py` → `CONTROLLED`; `classify.py` → `CONTROLLED_TR`; `scheduled.py` → `notice`; `flash.py` → `drop_never_events` |
| Admin opinion/what-if on channels (به نظرم، اگر…، فرض کنید) | `classify.py` → `aside` |
| Executions/verdicts → yellow; spy executed → orange only if the text tells his part in the war; protests abroad and pro-government rallies (hardliners, Basij; no violence) → yellow; a crowd's call for revenge scores nothing (a leader's still does) | `classify.py` → `_judicial`, `_protest`, `_supporters_rally`, `crowd_revenge`; `classify_fa.py` → `_CROWD_REVENGE` |
| Human-interest (births, babies; nobody hurt) → yellow; "triple threat" is no threat; "first days/weeks of the war" is past only with "finally"/"months later" and no strike in the headline; a weak headline naming only the Leader in a home quarrel → yellow | `classify.py` → `_HUMAN_EN`, `early_war_past`, `_QUARREL_EN`; `classify_fa.py` → `_EARLY_WAR` |
| Past-year attack in headline, "escalation"/«تشدید تنش» alone, de-escalation talk, experts, "attacking X is a crime" → yellow | `classify.py` → `past_year`, `_PREVENT_ESC`, `EXPERTS`, `_JUDGED_EN`; `classify_fa.py` → `JUDGED` |
| English report scored only from its text: no event, yellow unless headline names the main front; strikes on air-defence systems → orange | `classify.py` → `score_en` (`_MAIN_EN`) |
| Road traffic (crashes, road tolls, car/road safety; no war words) → dropped, in Iran too; natural disasters outside Iran and the Middle East (floods in Colorado, a quake in Japan; not "election landslide", «پس‌لرزه») → dropped. Other accidents and nature (collision, mine collapse, hospital/market fire, gas poisoning, flood, quake; no aircraft, ships or war words) → yellow ≤38, not military; across the border with Iran only as "near Iran border": accident/toll dropped, clashes (Pakistan's Balochistan…) yellow ≤40 | `mishap.py` → `road`, `far_nature`, `mishap`, `border_only`, `border_drop`; `relevance.py` → `is_relevant`; `classify.py` (`MISHAP_CAP`, `BORDER_CAP`) |
| Trump's own words on the future of the war with Iran (threats, warnings, deadlines; attacks/war/its end with will, if, soon, a decision — not talks going well, midterms, fuel, what was done; «ترامپ: …», "Trump says …", Trump at the start of the clause; at least half the story's news reports) → red in the bulletin only (`c["trump"]`; app shows sev ≥70); severity, index and Telegram alerts unchanged. "Attacks … unlikely / no plans to" and «… را بمباران می‌کنیم/خواهیم کرد» are no strike | `classify.py` → `trump_on_iran`, `_THREAT_*`, `_WAR_*`, `_WILL_*`, `_UNLIKELY_EN`; `classify_fa.py` → `FUTURE_ACT`; `cluster.py` (`refresh`); `alerts.py` (skips `trump`); `run_news.py` → `shown_sev` |
| Mediators visiting Tehran → orange | `classify.py` → `_mediator_visit` |
| US military at sea on the main front (CENTCOM: ship disabled/fired on for the blockade, «از کار انداخت», precision munitions, boats harassing, escorts, mine clearing) → orange 60, no event flag (alerts and panel unchanged); not sanctions, rewards, task forces, podcasts | `classify.py` → `us_sea_op`, `US_SEA_SEV` |
| Clustering, same-story rules, story-level caps, channel rules | `cluster.py` → `features`, `same_story`, `Clusterer`, scoring block after `ch_strike` |
| Same strike in other words (news only, same attacker + city, 12 h, no "new/again") | `cluster.py` → `strike_key`, `same_strike` |
| Gulf Arab front only (no Iran/US/Israel named): one attack on one city (Riyadh = «پایتخت عربستان», Najran, Eastern Province, Dubai, Doha…; Jordan and Iraq too, not Lebanon/Syria) = one story, 2 h (or 1 h after the latest report, up to 4 h from the start of its latest run of reports); sirens/civil-defence alerts a story of their own; several outlets → orange ≤64 on Saudi soil | `fronts.py` → `gulf_mark`; `cluster.py` → `gulf_key`, `same_gulf`, `_gulf_matches`, `GULF_WINDOW`, `GULF_GAP`, `_run_start` |
| Named targets (Aramco tower = Riyadh financial district/KAFD, King Khalid airport, Abqaiq, Ras Tanura, Jizan refinery, Dubai airport, Ras Laffan, Erbil airport…; give their city when the headline names none) → one story for 24 h (up to 120 reports); later reports (damage, debris, video, ministry, responsibility) of an attack in an Arab country → 12 h | `fronts.py` → `_TARGETS`, `gulf_targets`, `_AFTER_*`; `cluster.py` → `TARGET_KEEP`, `AFTER_SPAN`, `gulf_when` |
| The Houthis' statement of operations (count, several targets: «۴ عملیات…», "claim attack on King Khalid airport") = one story for 16 h unless counts differ; a slice naming one target may join that target's attack story; never fighting inside Yemen («مزدوران») | `fronts.py` → `gulf_claim`; `cluster.py` → `CLAIM_SPAN`, `gulf_fit`, `gulf_apart` |
| Telegram posts join a news story (never another channel's): strike key / Gulf mark / close headline (≥0.4) up to 6 h after its latest report (2 h for a "strike now" post not relaying an outlet) | `cluster.py` → `_chan_win`, `_chan_late`, `_chan_near`, `CHAN_KEEP`, `CHAN_FRESH`, `CHAN_SCORE` |
| Telegram: one alert per attack on the Arab front (same target 24 h while still told or aftermath only; same city 2 h, or while told and nothing "as it happens", or aftermath 6 h; same statement 16 h; sirens 2 h); new target/city/"another"/event time apart → sent; people hurt → 🔄 update; held stories stay out of `sent` (`state.arab`) | `alerts.py` → `_arab_print`, `_arab_same`, `_arab_pick`, `ARAB_*` |
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
