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
Map only: what and where, plus the intent that must not drift. Thresholds, windows and word lists live in the code
(comments, docstrings); read them there and don't copy them here.

| Feature | File → place |
|---|---|
| Main loop, order of steps, migrations (`misc[...]`), lite files, story map for the panel | `run_news.py` → `main`, `news_round`, `lite` |
| Collecting feeds, Telegram pages, replies/admin comments; foreign (Arabic/French…) headlines dropped | `collect.py` → `collect_all`, `_tg_parse`, `follow_up_comment`, `not_english` |
| Severity / tiers (red ≥70, orange ≥45), yellow caps (`*_CAP`), Persian rules | `classify.py` (caps block in `classify()`), `classify_fa.py` → `score_fa` |
| Toned down to yellow: multi-item headlines (first item only), past, no-deadline, "on the table" | `classify.py` → `multi_parts`, `PAST`, `_NO_DEADLINE_*`, `_TABLE_*` |
| Side fronts (Saudi, Gulf, Yemen, Lebanon, Red Sea): red only for a big turn, orange only for attacks on Saudi soil, the rest yellow; «فلسطین اشغالی» = Israel (main front) | `fronts.py`; `classify.py` (`side_front`, `_local_region`); `cluster.py` (`MINOR_CAP`); `index.py` → `SIDE_W` |
| Controlled detonations → yellow; advance notices → `scheduled`, off the main front | `classify_fa.py` → `CONTROLLED`; `classify.py` → `CONTROLLED_TR`; `scheduled.py` → `notice`; `flash.py` → `drop_never_events` |
| Admin opinion/what-if on channels | `classify.py` → `aside` |
| Yellow: executions/verdicts (a spy orange only with his part in the war), protests abroad, pro-government rallies; a crowd's call for revenge scores nothing | `classify.py` → `_judicial`, `_protest`, `_supporters_rally`, `crowd_revenge`; `classify_fa.py` → `_CROWD_REVENGE` |
| Yellow: schools/education at home (not an attack on a school) | `classify.py` → `_school`, `SCHOOL_CAP` |
| Yellow: human-interest, "first days of the war" told later, a home quarrel naming the Leader | `classify.py` → `_HUMAN_EN`, `early_war_past`, `_QUARREL_EN`; `classify_fa.py` → `_EARLY_WAR` |
| Yellow: past-year attacks, "escalation" alone, de-escalation talk, experts, "attacking X is a crime" | `classify.py` → `past_year`, `_PREVENT_ESC`, `EXPERTS`, `_JUDGED_EN`; `classify_fa.py` → `JUDGED` |
| An attack told with the verb: actor of the war → struck/hit/bombed… → a place or target ("US strikes Iran's Qeshm Island", «حمله اسرائیل به جنوب لبنان», «… را هدف قرار داد», «هدف حمله … قرار گرفت»); never the noun ("Iran strikes unlikely"), a modal/plan/threat, sanctions or words, a judgement, a side clause ("… as Houthis target Riyadh") | `attack_verb.py` → `actor_strikes_en`, `actor_strikes_fa`, `NOUN_NEXT`, `NOUN_BEFORE`, `SOFT_EN`, `NOT_BEFORE_FA`, `JUDGED_FA`; `classify.py` → `score_en` (`VERB_ATTACK`); `classify_fa.py` → `score_fa`; first run: old red stories marked sent (`run_news.py`, `misc["verb_attack"]`) |
| "Strike/struck/hit" not of the war (an earthquake/storm strikes, labour strikes, strike a deal, struck down a law, prices hit a record; Persian heart/animal «حمله») rewritten before scoring; never when a weapon, armed force or an actor striking is in the same clause | `strike_sense.py` → `calm_en`, `calm_fa`, `WAR_NEAR`; used in `classify.py` → `score_en`, `classify_fa.py` → `score_fa`, `mishap.py`, `cluster.py` → `tokens` |
| English report scored only from its text | `classify.py` → `score_en` (`_MAIN_EN`) |
| Road traffic and far-away disasters dropped; other accidents/nature yellow, not military; flights stopped by an earthquake/weather: no airspace flag or lamp; across the border only "near Iran border" | `mishap.py` → `road`, `far_nature`, `mishap`, `air_nature`, `border_only`, `border_drop`; `relevance.py` → `is_relevant`; `classify.py` (`MISHAP_CAP`, `BORDER_CAP`) |
| Trump's own words: on the future of the war → red, on the conflict otherwise → at least orange. Bulletin display only (`c["trump"]`): severity, index and Telegram alerts unchanged | `classify.py` → `trump_level`, `_trump_speaks` (market reports left out: `_market_report`) and the `_MATTER_*`… lists; `classify_fa.py` → `FUTURE_ACT`; `cluster.py` (`refresh`); `alerts.py` (skips `trump`); `run_news.py` → `shown_sev` |
| Mediators visiting Tehran → orange | `classify.py` → `_mediator_visit` |
| Cyber attacks/hacks: never a strike, orange at most (at least orange in the war itself); red only Iran vs Israel/US against something military or vital, told as done | `classify.py` → `cyber`, `CYBER_*`; `cluster.py` (`refresh`: `cyber_war`) |
| US military at sea on the main front (CENTCOM) → orange, no event flag (alerts and panel unchanged) | `classify.py` → `us_sea_op`, `US_SEA_SEV` |
| Clustering, same-story rules (synonyms `SYN`/`SAME`; a channel post with no headline: `LONG_POST`), story-level caps, channel rules | `cluster.py` → `tokens`, `features`, `same_story`, `Clusterer`, scoring block after `ch_strike` |
| Same strike in other words | `cluster.py` → `strike_key` (`_passive`: "Iran's Sirik attacked" names the side struck), `same_strike` |
| One attack on one city of Iran, one story (main front): reports of the same city close together, a province-only report with its one story, a channel post with the news (never another channel's); kept apart: another city, another kind of target or street, "another/again" told as it happens, a channel or "moments ago" after a quiet spell; Tehran left out, big cities a shorter window | `city_strike.py` → `mark`, `same`, `PROVINCES`, `BIG`; `cluster.py` → `iran_mark`, `iran_when`, `IR_*`, `_iran_matches`, `_iran_conflict`, `_iran_apart`, `_iran_pair`; headline from a report naming the city and the attack as done: `_told_done`, `_pick` |
| Arab front stories: one attack on one city, named targets (city given when missing), aftermath reports, the Houthis' statements of operations, sirens | `fronts.py` → `gulf_mark`, `_TARGETS` (oil and gas sites; long pipelines with no one city: `_ROUTES`), `gulf_targets`, `_AFTER_*`, `gulf_claim` (the Houthis' own forces are no target: `_OWN_FORCES_*`); `cluster.py` → `gulf_key`, `same_gulf`, `_gulf_matches`, `gulf_when`, `gulf_fit`, `gulf_apart`, `_run_start`, `GULF_*`, `TARGET_KEEP`, `AFTER_SPAN`, `CLAIM_SPAN` |
| Telegram posts joining a news story (never another channel's) | `cluster.py` → `_chan_win`, `_chan_late`, `_chan_near`, `CHAN_*` |
| When it happened: time label per event story (`c["ev"]`), parts of the day in Tehran time, joining by told time | `cluster.py` → `EV_ON`, `_ev_report`, `_PART`, `_part_of_day`, `_first_hand`, `Clusterer._ev_add`, `_ev_fits`, `_ev_late`, `_ev_back`, `_facts` |
| An earlier day named as the day of the event → told time, joins the target's story, no Telegram alert | `vessel.py` → `past_day`; `cluster.py` → `_ev_report`, `_ev_back`; `alerts.py` → `_dated`; `flash.py` → `told_later` |
| Qeshm, Kish, Abu Musa: places of their own, Hormuz area, Iran's soil in the index | `lexicon.py` → `PLACES`; `cluster.py` → `REGION`; `index.py` → `IR_LAND` |
| "Source not stated" vs relayed outlet | `citation.py` → `outlet_named`, `OTHER` |
| Ships/tankers: marks, sea areas, time, kind, flag, owner, name, counts, Iranian statements | `vessel.py` (`REFS`, `AREAS`, `mark`, `area`, `when`, `kinds`, `flag`, `owner`, `name`, `ship_id`, `counts`, `statement`, `signature`) |
| Same ship/incident in the bulletin | `cluster.py` → `same_story` (sid), `_ship_misfit`, `_own_matches` |
| Telegram alerts: red stories, late-report rule; at sea one alert per incident (updates only for sinking/casualties/who/seizure); Arab front one per attack (people hurt → 🔄 update; held stories in `state.arab`) | `alerts.py` → `run`, `_late`, `_sea_pick`, `_claim_told`, `_fresh`, `_later`, `SEA_NEWS`, `_arab_print`, `_arab_same`, `_arab_pick`, `ARAB_*` |
| Deployments; evacuation orders (one story per order). The evacuation lamp lights only for an order to leave a country told in a headline (`tf` + `evac.mark`: who orders, which country); people taken off a ship, a platform, out of a fire or flood (a rescue) are never `evac`; forces taken out never | `deploy.py`; `evac.py` → `mark`, `rescue`; `index.py` → `compute_lights`; `classify.py` (pullback block); `pullback.py` (`_SIDE_EN`: a pullback only in an "after …" clause is not the news); `tests/test_evac.py` |
| Forces/base/people taken out of a place: forces out of the Middle East → red, no lamp (`pullback_me`; counts in the index like an evacuation); elsewhere (Europe…) never an evacuation, no lamp: orange, red only when the headline names a threat from Iran. Sent to the Middle East (or on a mission) = a deployment, untouched; moved on elsewhere (UK → Europe) = still a pullback. A base counts only as the place left. One story per event whatever the verb (label: whose, country, base, round); one alert per event within 12 h | `pullback.py` → `read`, `place`, `mark`, `fits`; `classify.py` → `PULL_*`; `cluster.py` → `_pull_matches`, `PULL_KEEP`; `alerts.py` → `_told_event`, `SAME_EVENT` |
| Main-front panel + instant Telegram alerts (flash), "not confirmed", not of the moment (statements, relayed, past, videos, retelling) | `flash.py` → `events`, `process`, `_news_ok`, `told_later`, `mark_denied` |
| Announced cause of a blast (film shoot, fireworks, drill, controlled detonation, mine, accident): bulletin yellow (`controlled`, not for accidents); panel lines of that place within a few hours labelled «علت اعلامی» instead of confirmed, and one ℹ️ Telegram update per announced incident | `cause.py` → `which`, `find`, `NAMES`; `classify.py` (after `CONTROLLED_TR`); `flash.py` → `explain`, `WHY_SPAN`; app: `fr-why` |
| Main-front places beyond Iran's cities (panel and its alerts only; the bulletin doesn't read them) | `front_places.py` → `IRAN`, `ABROAD`; `flash.py` → `_IRAN`, `_places` |
| Tension index, direct strikes (one strike counted once), lights (deployment/ultimatum only from a headline, `tf`) | `index.py` → `index_value`, `direct_strikes`, `distinct`, `_live`, `_sea_war`, `pressure`, `compute_lights`; `classify.py` sets `item["tf"]` |
| Citizen reports (witness): `places_in` reads front_places too, `cities_in` (bulletin) only witness.CITIES | `witness.py` → `parse`, `places_in`, `place_name` |
| X posts (manual screenshots in `engine/xmanual/posts.json`) | `xposts.py` |

Workflows: `live.yml` (news engine; push on `engine/**` restarts it), `ticker.yml`, `news.yml`,
`assets.yml`. Files at the repo root and in `docs/` don't trigger the engine.

## App (docs/)
`app.js` sections (search the banner comments `// ---- name`): strings (fa/en dicts), stories, story tray,
main front (flash), sheet, map, X, Economist, refresh loop, what's new.
Styles in `app.css`. Version: `APP_REL`, `APP_BUILD`
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
