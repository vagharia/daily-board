"""'Strike', 'struck' and 'hit' in a sense that is not an attack, taken out before a headline is scored.

The war words are read by many patterns (classify.PATTERNS: "strikes? (on|in|near…)", "struck", "hit", "attacks? …
killed"…). An earthquake that "strikes near Bushehr", a truckers' strike, a deal "struck" in Doha or a court that
"strikes down" a law would read as an attack. `calm_en` rewrites only those senses into a neutral word, so nothing
of the war is lost:

Kept as they are, always (the strike of the war):
  - any strike with a weapon, an armed actor or a target of the war near it: air/missile/drone/rocket strikes,
    "pre-emptive strike", "strikes on/against …", "Israel strikes Iran", "lightning strike on …", a "strike group",
    "first-strike", "threatens to strike", "strike back";
  - a clause with a weapon word, an armed force, or an actor of the war striking in it ("Earthquake strikes Iran
    as Israeli jets hit Tehran", "Israel strikes Gaza as floods hit camps"): nature and labour senses in it are
    left untouched (WAR_NEAR).

Rewritten (never an attack):
  1. nature as the striker: an earthquake, a quake, a tremor, magnitude N, a storm, a cyclone, lightning, a flood,
     a drought, a heat wave, a disease or an outbreak "strikes/struck/hits/rocks/jolts" … ; "struck/hit by
     lightning/an earthquake/a storm/a flood/an illness…"; "lightning strike(s)" not followed by on/against.
  2. a labour strike: general/hunger/labour/sit-in/wildcat strike, "on strike", "go/went on strike", "strike by
     workers", "strikers", "(workers|truckers|teachers|…) strike", "stage a strike", "nationwide/N-day strike"
     (never with "on/against/near …" after it: a three-day strike on Gaza is an attack), "strike over pay/wages".
     Never when an actor of the war stands right before it with no worker word between ("Israeli three-day
     strike", "US strikes by B-2s"); verbs that also start or stop attacks (launch, hold off, call off, join,
     continue) are not read as labour.
  3. idioms: strike/struck a deal, an agreement, an accord, a bargain, a balance, a chord, a tone, a note, a pose,
     a compromise, a truce, a ceasefire (deesc.py reads a truce from its own text); strike(s)/struck down a law, a
     ban, a ruling…; a court "strikes down"; struck off/from a list or the record; "strikes fear"; "strike(s) a blow
     to" the economy, the talks…; "strike gold".
  4. markets and records: oil/gold/prices/stocks/the rial/inflation … "hit(s)" a record/high/low/N; "hits a
     record/high/low/snag/milestone/wall"; "hit by sanctions/tariffs/inflation/blackouts/…"; "hit the headlines/
     streets/road"; "hits back at critics/claims/reports".

`calm_fa`: «حمله» of the body or of animals (heart attack, panic attack, a dog's attack, locusts), never of the war.
"""
import re

from .util import fa_norm

I = re.I

# ------------------------------------------------------------------ a weapon or an armed actor in the same clause
# a word between an actor and "strike" that makes it nature's or workers' ("Iran earthquake strikes", "Iranian
# truckers strike"), not the actor's
_CALM_WORD = (r"(?:earthquakes?|quakes?|tremors?|temblors?|aftershocks?|storms?|sandstorms?|cyclones?|floods?"
              r"|lightning|droughts?|heat ?waves?|outbreaks?|workers?|truckers?|drivers?|teachers?|nurses?|doctors?"
              r"|miners?|dockers?|merchants?|shopkeepers?|bazaar\w*|traders?|retirees?|pensioners?|farmers?|bakers?"
              r"|unions?|labou?r|employees?|students?|lawyers?|oil|refinery|port|rail|transport|general|hunger"
              r"|nationwide|national|prices?|stocks?|markets?|rial|currency|inflation|economy|exports?|court)\b")
WAR_NEAR = re.compile(
    r"\b(air ?strikes?|airstrikes?|missiles?|rockets?|drones?|uavs?|bomb\w*|shell(s|ed|ing)|artillery|warplanes?"
    r"|fighter jets?|jets|f-\d+s?|b-\d+s?|troops|soldiers|army|military|militar\w+|idf|irgc|revolutionary guards?"
    r"|hezbollah|houthis?|hamas|militants?|insurgents?|gunm[ae]n|navy|naval|warships?|centcom|pentagon"
    r"|pre-?emptive|retaliat\w*|intercept\w*|sirens?|explosions?|blasts?|raids?|offensive|invasion|war)\b"
    # an actor of the war striking in the same clause ("Israel strikes Gaza … as floods hit camps"): left as it is
    r"|\b(?:israel\w*|zionist|u\.?s\.?|us|america\w*|iran\w*|tehran|british|uk|saudi\w*|emirati|uae|coalition|nato"
    r"|russia\w*|turk\w*|pakistan\w*|iraq\w*|syria\w*|jordan\w*|egypt\w*|qatar\w*|kuwait\w*|bahrain\w*|oman\w*"
    r"|yemen\w*|leban\w*)['’]?s?\s+(?:(?!" + _CALM_WORD + r")\w+\s+)?(?:strikes?|struck|striking|hits?|hitting|attack\w*|bomb\w*"
    r"|pound\w*|shell\w*|target\w*)\b", I)

# ------------------------------------------------------------------ 1. nature
_NATURE = (r"(?:(?:magnitude|m)[\s-]?\d+(?:\.\d+)?(?:[\s-]+(?:magnitude|richter))?(?:\s+(?:earthquake|quake|tremor"
           r"|temblor))?|(?:strong|powerful|massive|deadly|major|moderate|minor|light|shallow|small|big|huge|severe"
           r"|heavy|violent|tropical|winter|summer|dust|sand|snow|ice|hail|rain|flash)?\s*"
           r"(?:earthquakes?|quakes?|tremors?|temblors?|aftershocks?|storms?|sandstorms?|dust ?storms?|snowstorms?"
           r"|hailstorms?|rainstorms?|thunderstorms?|cyclones?|typhoons?|hurricanes?|tornado(?:e?s)?"
           r"|floods?|flash floods?|floodwaters?|droughts?|heat ?waves?|cold (?:snap|wave)s?|frosts?|blizzards?"
           r"|tsunamis?|avalanches?|landslides?|mudslides?|wildfires?|bush ?fires?|forest fires?|famine|disease"
           r"|epidemics?|pandemic|outbreaks?|cholera|virus|covid(?:-19)?|flu|illness|tragedy|disaster))")
_NAT_VERB = r"(?:strikes?|struck|striking|hits?|hitting|rocks?|rocked|jolts?|jolted|shakes?|shook|batters?|battered)"
_NATURE_SUBJ = re.compile(r"\b" + _NATURE + r"(?:\s+(?:that|which|has|have|had))?\s+" + _NAT_VERB + r"\b", I)
_NATURE_BY = re.compile(r"\b(?:struck|hit|stricken|battered|rocked|jolted)\s+by\s+(?:a |an |the )?(?:\w+\s+){0,2}?"
                        r"(?:earthquakes?|quakes?|tremors?|temblors?|aftershocks?|storms?|sandstorms?|dust ?storms?"
                        r"|snowstorms?|cyclones?|typhoons?|hurricanes?|tornado(?:e?s)?|lightning|floods?|droughts?"
                        r"|heat ?waves?|cold (?:snap|wave)s?|frosts?|blizzards?|tsunamis?|avalanches?|landslides?"
                        r"|wildfires?|famine|disease|epidemics?|pandemic|outbreaks?|cholera|virus|covid(?:-19)?|flu"
                        r"|illness|cancer|heart attacks?|tragedy|grief)\b", I)
_LIGHTNING = re.compile(r"\blightning[\s-]+strikes?\b(?!\s+(?:on|against|at|in|inside|near|deep)\b)", I)

# ------------------------------------------------------------------ 2. labour
_WORKERS = (r"(?:workers?|truckers?|truck drivers?|drivers?|teachers?|nurses?|doctors?|physicians?|medics?|employees?"
            r"|unions?|labou?r|miners?|dockers?|dock ?workers?|port workers?|oil workers?|refinery workers?"
            r"|steel ?workers?|railway ?workers?|rail ?workers?|bus drivers?|taxi drivers?|cabin crews?"
            r"|air traffic controllers?|bakers?|farmers?|merchants?|shopkeepers?|bazaar(?:is?)?|traders?|retirees?"
            r"|pensioners?|students?|lawyers?|judges?|civil servants?|public sector)")
_LABOUR_ALWAYS = re.compile(
    r"\b(?:general|hunger|labou?r|sit-?in|wildcat|sympathy|solidarity|token)\s+strikes?\b"
    r"(?!\s+(?:on|against|at|inside|near|targeting)\b)"
    r"|\b" + _WORKERS + r"(?:['’]s?)?\s+(?:(?:go|goes|went|gone|going|are|is|were|was|remain|remains|stay|stays)\s+)?"
    r"on\s+strike\b"
    r"|\b(?:go|goes|went|gone|going|remain|remains|remained|stay|stays|stayed|are|is|were|was)\s+on\s+strike\b"
    r"|\bstrikes?\s+by\s+(?:\w+\s+){0,2}?" + _WORKERS + r"\b"
    r"|\b(?:stage|stages|staged|staging)\s+(?:a |an |the |their |its )?(?:\w+\s+)?strikes?\b"
    r"(?!\s+(?:on|against|at|in|inside|near|targeting)\b)"
    r"|\b" + _WORKERS + r"(?:['’]s?)?\s+(?:\w+\s+)?strikes?\b(?!\s+(?:on|against|at|inside|near|targeting)\b)"
    r"|\bstrik(?:e|es|ing)\s+(?:over|for)\s+(?:\w+\s+){0,2}?(?:pay|wages?|salar\w+|pensions?|bonus\w*|contracts?"
    r"|working conditions|unpaid)\b"
    r"|\bstrikers\b|\bstrike action\b|\bstrike (?:fund|ballot|vote|pay|committee|leaders?)\b"
    r"|\bbazaar\s+(?:\w+\s+)?strikes?\b|\bshops?\s+(?:shut|closed)\s+(?:\w+\s+){0,3}strikes?\b", I)
# "a three-day strike", "nationwide strike": labour unless a target follows (a three-day strike on Gaza)
_LABOUR_IF_NO_TARGET = re.compile(
    r"\b(?:nation-?wide|national|country-?wide|city-?wide|one-day|two-day|three-day|\d+-day|\d+-hour|24-hour"
    r"|48-hour|72-hour|day-long|week-long|month-long|weeks-long|months-long|days-long|transport|trucking|truckers?"
    r"|rail|teachers?|nurses?|doctors?|oil|refinery|port|dock|bazaar|shopkeepers?|merchants?|retirees?)['’]?\s+"
    r"strikes?\b(?!\s+(?:on|against|at|in|inside|near|targeting|hit|hits|kill\w*|by (?:israel\w*|the u\.?s\.?|us"
    r"|america\w*|iran\w*|irgc|idf)))", I)

# ------------------------------------------------------------------ 3. idioms
_ADJ = (r"(?:new|fresh|historic|landmark|major|big|huge|rare|tentative|preliminary|interim|final|framework|trade"
        r"|nuclear|peace|oil|gas|energy|arms|defen[cs]e|security|investment|business|economic|political|swap|prisoner"
        r"|fine|delicate|careful|conciliatory|defiant|tough|hard|harsh|soft|softer|firmer|optimistic|cautious|positive"
        r"|hopeful|sombre|somber|different|similar|measured|upbeat|warm|bullish|hawkish|dovish|right|\$?\d[\d.,]*\w*"
        r"|multi-?\w+|\w+-year|\w+-dollar|billion-dollar)")
_IDIOM = re.compile(
    r"\b(?:strike|strikes|striking|struck)\s+(?:a |an |the |its |their |another )?(?:" + _ADJ + r"\s+){0,2}"
    r"(?:deals?|agreements?|accords?|bargains?|balance|chords?|tone|note|pose|compromises?|pacts?|partnerships?"
    r"|alliances?|settlements?|gold|it rich|lucky)\b"
    r"|\b(?:strike|strikes|striking|struck)\s+(?:a|an)\s+(?:" + _ADJ + r"\s+){0,2}(?:truce|cease-?fire)\b"
    r"|\b(?:strike|strikes|striking|struck)\s+down\s+(?:a |an |the |its |his |her |their )?(?:\w+\s+)"
    r"{0,3}?(?:laws?|bans?|rulings?|rules|executive orders?|bills?|measures?|polic(?:y|ies)|regulations?|statutes?"
    r"|provisions?|tariffs?|mandates?|sentences?|convictions?|verdicts?|amendments?)\b"
    r"|\b(?:court|courts|judges?|justices?|supreme court|tribunal|panel|parliament|senate)\b[^.;:]{0,40}?\b"
    r"(?:strikes?|struck)\s+down\b"
    r"|\b(?:struck|strikes?|striking)\s+(?:off|from)\s+(?:the |a )?(?:\w+\s+)?(?:list|register|record|roll|ballot"
    r"|registry|agenda)\b"
    r"|\b(?:strike|strikes|striking|struck)\s+(?:fear|terror|panic)\s+in(?:to)?\b"
    r"|\b(?:strike|strikes|striking|struck)\s+(?:a |another )?(?:\w+\s+)?blow\s+(?:to|for)\s+(?:\w+\s+){0,3}?"
    r"(?:econom\w*|talks|negotiations|diplomacy|hopes?|efforts?|plans?|deal|government|campaign|currency|rial"
    r"|markets?|ties|relations|reputation|credibility|image|chances?|prospects?|industry|exports?|sales?|revenue\w*"
    r"|budget|morale|confidence|reform\w*|freedoms?|rights?|democracy|press|media|opposition)\b"
    r"|\bstrikes? (?:price|rate|zone)s?\b|\bthree strikes\b|\blucky strike\b", I)

# ------------------------------------------------------------------ 4. markets and records
_MARKET = (r"(?:oil|crude|brent|wti|gold|silver|prices?|stocks?|shares?|markets?|bonds?|yields?|rial|toman|dollar"
           r"|euro|currency|inflation|bitcoin|index|indices|tedpix|bourse|exports?|imports?|sales?|output|production"
           r"|demand|unemployment|debt|deficit|rates?|premiums?|insurance costs?|freight rates?|fares?)")
_RECORD = re.compile(
    r"\b" + _MARKET + r"\s+(?:\w+\s+)?(?:hits?|hitting|strikes?)\s+(?:a |an |the )?(?:new |fresh |record |all-time "
    r"|multi-?\w+ |\d+-\w+ |\w+-year |\w+-month |\w+-week |seven-year |its |their )*(?:records?|highs?|lows?|peaks?"
    r"|bottom|ceiling|floor|levels?|marks?|\$?\d[\d.,]*\w*|\w+-(?:year|month|week) (?:highs?|lows?))\b"
    r"|\b(?:hits?|hitting)\s+(?:a |an |the )?(?:new |fresh |all-time |record |multi-?\w+ |\w+-year |\w+-month )*"
    r"(?:records?|highs?|lows?|peaks?|snags?|milestones?|roadblocks?|walls?|bumps?|jackpot|headlines|streets|road"
    r"|shelves|stores|screens|theaters|theatres|airwaves|campaign trail|ground running|pause button|reset button)\b"
    r"|\b(?:hit|hits|hard[\s-]hit|badly hit|worst[\s-]hit)\s+by\s+(?:\w+\s+){0,2}?(?:sanctions?|tariffs?|inflation"
    r"|recession|price (?:rises?|hikes?)|costs?|blackouts?|power cuts?|outages?|shortages?|water shortages?|droughts?"
    r"|heat|protests?|strikes? by workers|layoffs?|job cuts?|devaluation|lockdowns?|the pandemic|scandals?"
    r"|criticism|fines?|lawsuits?|claims|allegations|downturn|slump|slowdown|crisis|budget cuts?)\b"
    r"|\b(?:hits?|hitting|hit)\s+back\s+at\s+(?:\w+\s+){0,2}?(?:critics?|claims?|reports?|remarks?|comments?"
    r"|accusations?|allegations?|criticism|statements?|rumou?rs?|media|press|journalists?|opponents?|rivals?)\b"
    r"|\bhit-and-run\b|\b(?:box[- ]office|chart|smash|surprise|viral) hits?\b|\bhit (?:songs?|singles?|shows?|series"
    r"|films?|movies?|albums?|records?|tv)\b", I)

_PARTS = re.compile(r"[^.;:!?|]+[.;:!?|]?")


def _clause_has_war(clause, span):
    """A weapon or an armed actor in the clause, outside the words being rewritten."""
    rest = clause[:span[0]] + " " + clause[span[1]:]
    return bool(WAR_NEAR.search(rest))


_ACTOR_BEFORE = re.compile(r"\b(?:israel\w*|zionist|u\.?s\.?|us|american?s?|america|iran\w*|irgc|idf|british|uk"
                           r"|french|saudi|emirati|uae|coalition|allied|nato|russian?|houthis?|hezbollah|hamas"
                           r"|pakistani?|turkish|iraqi?|syrian?|jordanian?|egyptian?|qatari?|kuwaiti?|bahraini?"
                           r"|omani?|yemeni?|lebanese|retaliatory|deadly|fresh|new|overnight|latest|joint|precision"
                           r"|targeted|limited|massive|heavy|surgical)['’]?s?\s*$", I)


_ACTOR_RX = re.compile(_ACTOR_BEFORE.pattern[:-len(r"['’]?s?\s*$")] + r"['’]?s?\b", I)
_CALM_RX = re.compile(r"\b" + _CALM_WORD, I)


_VERB = re.compile(r"\b(?:strik(?:e|es|ing|ers?)|struck|stricken|hit(?:s|ting)?|rock(?:s|ed)?|jolt(?:s|ed)?"
                   r"|shak(?:e|es)|shook|batter(?:s|ed)?)\b", I)


def _neutral(text, word):
    """Only the strike/hit verb replaced; every other word (earthquake, oil prices, truckers) stays for the rules."""
    return _VERB.sub(word, text)


def _sub(rx, clause, word, guard, actor=False):
    def rep(m):
        if guard and _clause_has_war(clause, m.span()):
            return m.group(0)
        if actor:
            # the words before the strike word: an actor of the war there and no worker or nature word between
            # ("Israeli three-day strike" stays; "Iranian truckers strike", "Israeli general strike" are rewritten)
            k = re.search(r"(?i)strik", m.group(0))
            before = clause[:m.start() + (k.start() if k else 0)]
            words = " ".join(before.split()[-4:])
            if (_ACTOR_BEFORE.search(before) or _ACTOR_RX.search(words)) and not _CALM_RX.search(words):
                return m.group(0)
        return _neutral(m.group(0), word)
    return rx.sub(rep, clause)


def calm_en(text):
    """The text with non-military senses of strike/struck/hit replaced by neutral words (see the module doc)."""
    if not text or not re.search(r"(?i)\b(strik\w*|struck|hit\w*|stricken|rock\w*|jolt\w*|shak\w*|shook|batter\w*)",
                                 text):
        return text or ""
    out = []
    for clause in _PARTS.findall(text):
        # idioms and records never speak of an attack, whatever else the clause names
        clause = _sub(_IDIOM, clause, "settles", False)
        clause = _sub(_RECORD, clause, "reaches", False)
        # nature and labour: only with no weapon or armed actor in the same clause
        clause = _sub(_NATURE_BY, clause, "affected", True)
        clause = _sub(_NATURE_SUBJ, clause, "affects", True)
        clause = _sub(_LIGHTNING, clause, "flash", True)
        clause = _sub(_LABOUR_ALWAYS, clause, "walkout", True, actor=True)
        clause = _sub(_LABOUR_IF_NO_TARGET, clause, "walkout", True, actor=True)
        out.append(clause)
    return re.sub(r"[ \t]{2,}", " ", "".join(out)).strip()


# ------------------------------------------------------------------ Persian
_BODY_FA = re.compile(fa_norm(
    r"حمل(?:ه|ات)\s*(?:ی\s*)?(?:قلبی|عصبی|آسم|آسمی|صرع|پانیک|هراس|میگرن|کلیوی|مغزی|ویروسی|حساسیتی|آلرژی)"
    r"(?![\u0600-\u06FF])|حمل(?:ه|ات)\s*(?:ی\s*)?(?:سگ|سگ\s*های|سگها|گرگ|خرس|پلنگ|کوسه|زنبور|زنبورها|مار|ملخ|ملخ\s*ها|ملخها|موش|حیوان"
    r"|حیوانات|آفات|آفت)") + r"(?![\u0600-\u06FF])")


def calm_fa(text):
    """Persian text with «حمله» of the body or of animals replaced by a neutral word."""
    if not text or "حمل" not in text:
        return text or ""
    return _BODY_FA.sub(" عارضه ", text)
