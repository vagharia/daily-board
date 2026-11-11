# The weekly Economist tab

`issue.json` holds one issue of The Economist, summarised by hand. Only the articles that bear on the tab's
categories go in, in the magazine's own order; the rest are left out. Each article carries one or more category tags
(an article can be both military and politics, or both AI and banking), shown above its title:

| key      | tag                                                       |
|----------|-----------------------------------------------------------|
| `mil`    | Military                                                  |
| `pol`    | Politics                                                  |
| `oil`    | Oil & energy                                              |
| `commod` | Commodities: gold, copper and other metals                |
| `money`  | Money & banking (markets, central banks, inflation)       |
| `ai`     | AI                                                        |
| `cyber`  | Cyber                                                     |

The tab opens on all articles; the category bar filters them (any of the chosen categories). A category with nothing
that week stays in the bar, dimmed. There are no red/orange/yellow levels in this tab.

## Each week

Replace the whole file with the new issue: last week's articles go, the new ones come in. Pushing the file starts a
live run, which publishes `economist.json` within a few minutes; preview pictures fill in over the next few rounds.

## Fields

- `issue`: the issue date, `YYYY-MM-DD`.
- `articles`, in the magazine's order, each with:
  - `id`: short and unique within the issue.
  - `url`: the article's page on economist.com.
  - `sec`: section key: `leaders`, `briefing`, `wtw` (The world this week), `inv` (By Invitation), `us`, `americas`,
    `asia`, `china`, `mea`, `europe`, `britain`, `intl`, `business`, `finance`, `science`, `culture`.
  - `col` (optional): `{"fa": ..., "en": ...}`, the column's name, e.g. Buttonwood.
  - `page` (optional): the page in the printed issue.
  - `tags`: the category keys above, most fitting first (its icon stands in for a missing picture).
  - `fa` and `en`: `t` the title, `s` the summary (up to two long or three medium paragraphs, separated by a blank
    line, in fluent prose), `i` the likely effects or a short analysis.

## Rules

- Summaries are written in our own words; no passages are copied from the magazine.
- No pictures are taken from the printed magazine, and the magazine file itself never goes into this repository.
  Each card shows the article's own web preview picture, found by the engine (a reader service's copy of the page)
  and only linked; never a picture from a news search, which can be about something else. Each article is looked
  up once; if no picture turns up, the card shows its category icon instead and the engine does not try again.
- When the new issue is in, list the articles without a picture for the owner, who may make pictures for them. A
  picture made for an article goes in `docs/econ/` and its path in the article's `"pic"` field (e.g.
  `"pic": "econ/2026-10-31-gulf.jpg"`); `"nopic": true` hides an own picture that doesn't fit the article.
- Articles about the war between Russia and Ukraine are left out.
