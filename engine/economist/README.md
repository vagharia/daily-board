# The weekly Economist tab

`issue.json` holds one issue of The Economist, summarised by hand. Only the articles that bear on the tab's five
categories go in:

| key     | tab                                                                      |
|---------|--------------------------------------------------------------------------|
| `pol`   | Politics & military; each article also gets a level: `red`, `orange` or `yellow` |
| `gold`  | Gold                                                                     |
| `oil`   | Oil                                                                      |
| `money` | Money & banking                                                          |
| `ai`    | AI                                                                       |

A category with nothing that week stays in the bar, dimmed. There is no "all articles" view.

## Each week

Replace the whole file with the new issue: last week's articles go, the new ones come in. Pushing the file starts a
live run, which publishes `economist.json` within a few minutes; preview pictures fill in over the next few rounds.

## Fields

- `issue`: the issue date, `YYYY-MM-DD`.
- `cats`: for each category, the article ids in display order. An article may sit in more than one category.
  In `pol`, articles are shown grouped red, orange, yellow.
- `articles`, each with:
  - `id`: short and unique within the issue.
  - `url`: the article's page on economist.com (the section feeds at `economist.com/<section>/rss.xml` list them).
  - `sec`: section key: `leaders`, `briefing`, `wtw` (The world this week), `us`, `americas`, `asia`, `china`, `mea`,
    `europe`, `britain`, `intl`, `business`, `finance`, `science`, `culture`.
  - `col` (optional): `{"fa": ..., "en": ...}`, the column's name, e.g. Buttonwood.
  - `page`: the page in the printed issue.
  - `tier`: politics articles only. Red is for the war with Iran, Hormuz and the Gulf's security; orange for regional
    politics that bears on it; yellow for wider politics.
  - `fa` and `en`: `t` the title, `s` the summary (one paragraph, or two separated by a blank line, in proportion to
    the article's length), `i` the likely effects.

## Rules

- Summaries are written in our own words; no passages are copied from the magazine.
- No pictures are taken from the printed magazine, and the magazine file itself never goes into this repository.
  Each card shows the article's own web preview picture, found by the engine (a reader service's copy of the page,
  with a Bing News thumbnail as a backup) and only linked. Each article is looked up once; if no picture turns up,
  the card shows its category icon instead and the engine does not try again.
- Articles about the war between Russia and Ukraine are left out.
