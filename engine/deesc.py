"""De-escalation news graded by how far it has got and who confirms it, not by words such as "talks" or "deal".

Stage (from the headline only, and only with a definite verb):
  5  done            a ceasefire in force, an agreement signed, Hormuz reopened, the blockade or sanctions lifted,
                     prisoners exchanged
  4  agreed          the parties say they have agreed (a ceasefire from tomorrow, a deal reached)
  3  talks held      a formal round between the warring parties' senior people took place (a direct call between them
                     counts too)
  2  concrete offer  a proposal, plan or draft on a specific matter handed over or received
  1  contact         calls, meetings, "discussed de-escalation", readiness for talks
  0  words           hopes, analysis, "could", "close to a deal"; denials
Hedges ("may", "if", "could … or", "trying to", "calls for", "must") make it a contact at most; a denial makes it 0.

Confirmation:
  3  a named senior official of a warring party says it, or took part (the T3 list below)
  2  a named official of a mediator (Qatar, Oman, Pakistan, Egypt, Turkey)
  1  unnamed sources in a reliable outlet
  0  a Telegram channel or a weak source

Subject: a ceasefire or end of the war, Hormuz reopened, the blockade lifted, a nuclear deal, a prisoner exchange or a
withdrawal count in full; a humanitarian pause, airspace or flights reopened, mine clearing one stage less; anything
vaguer ("regional security", "ties", "reducing tension") at most stage 1. Only Iran against America or Israel can be
red; other fronts (Saudi Arabia and the Houthis, Lebanon, Gaza) stop at orange.
"""
import re

from .util import FA_MAP, fa_norm, first_sentences

# severity by stage and confirmation (T3, T2, T1, T0)
GRID = {5: (85, 75, 60, 40), 4: (78, 66, 55, 40), 3: (72, 62, 50, 40), 2: (60, 52, 46, 38), 1: (30,) * 4, 0: (22,) * 4}
OTHER_FRONT_CAP = 60.0

# ------------------------------------------------------------------ who (T3: the warring parties; T2: mediators)
T3_FA = (r"رهبر\s*انقلاب|رهبر\s*معظم|خامنه\s*ای|پزشکیان|رئیس\s*جمهور|رییس\s*جمهور|عراقچی|وزیر\s*(?:امور\s*)?خارجه\s*ایران"
         r"|قالیباف|رئیس\s*مجلس|دبیر\s*شورای\s*عالی\s*امنیت\s*ملی|بقائی|بقایی|سخنگوی\s*وزارت\s*(?:امور\s*)?خارجه"
         r"|سخنگوی\s*دولت|مهاجرانی|وزارت\s*امور\s*خارجه|ترامپ|ونس|روبیو|ویتکاف|هگست|کاخ\s*سفید|وزارت\s*خارجه\s*آمریکا"
         r"|نتانیاهو|کاتز|دفتر\s*نخست\s*وزیر")
T3_EN = (r"\b(?:khamenei|supreme leader|pezeshkian|iran(?:ian|'s)? president|araghchi|iran(?:ian|'s)? foreign"
         r" (?:minister|ministry)|ghalibaf|qalibaf|parliament speaker|baghaei|baqaei|trump|vance|rubio|witkoff|hegseth"
         r"|white house|state department|netanyahu|katz|prime minister'?s office)\b")
IR_SIDE_FA = r"رهبر\s*انقلاب|رهبر\s*معظم|خامنه\s*ای|پزشکیان|عراقچی|قالیباف|بقائی|بقایی|مهاجرانی|ایران|تهران"
OTHER_SIDE_FA = r"ترامپ|ونس|روبیو|ویتکاف|هگست|کاخ\s*سفید|آمریکا|امریکا|واشنگتن|نتانیاهو|کاتز|اسرائیل|اسراییل"
IR_SIDE_EN = r"\b(?:khamenei|pezeshkian|araghchi|ghalibaf|qalibaf|baghaei|iran\w*|tehran)\b"
OTHER_SIDE_EN = r"\b(?:trump|vance|rubio|witkoff|hegseth|white house|u\.?s\.?|america\w*|washington|netanyahu|katz|israel\w*)\b"
T2_FA = (r"امیر\s*قطر|نخست\s*وزیر\s*قطر|وزیر\s*(?:امور\s*)?خارجه\s*قطر|آل\s*ثانی|وزیر\s*(?:امور\s*)?خارجه\s*عمان|بوسعیدی"
         r"|نخست\s*وزیر\s*پاکستان|شهباز\s*شریف|وزیر\s*(?:امور\s*)?خارجه\s*پاکستان|اسحاق\s*دار|عاصم\s*منیر"
         r"|وزیر\s*(?:امور\s*)?خارجه\s*مصر|عبدالعاطی|فیدان|اردوغان"
         r"|^(?:قطر|عمان|پاکستان|مصر|ترکیه|دوحه)\s*[:：]|^(?:دولت\s*)?(?:قطر|عمان|پاکستان|مصر)\s*(?:اعلام|تایید|گفت)")
T2_EN = (r"\b(?:emir of qatar|qatar'?s (?:emir|prime minister|foreign minister)|al thani|busaidi|sharif|ishaq dar|munir"
         r"|abdelatty|fidan|erdogan|(?:qatari|omani|pakistani|egyptian) (?:prime minister|foreign minister))\b"
         r"|^(?:qatar|oman|pakistan|egypt|turkey)\b[^.]{0,10}\b(?:says?|said|announces?|announced|confirms?|confirmed|presents?|presented|hands?|handed|submits?|submitted)\b")
UNNAMED_FA = r"منابع|منبع|مقام\s*(?:آگاه|مطلع)|به\s*نقل\s*از|گزارش\s*داد|گزارش\s*ها|ادعا"
UNNAMED_EN = r"\b(?:sources?|officials? (?:say|said)|according to|reportedly|report(?:s|ed)?|people familiar|claims?)\b"

# ------------------------------------------------------------------ what
CORE_FA = (r"آتش\s*بس|پایان\s*(?:دادن\s*به\s*)?جنگ|توقف\s*(?:جنگ|حملات|درگیری)|ترک\s*مخاصمه|صلح|بازگشایی\s*(?:تنگه\s*)?هرمز"
           r"|هرمز[^.؛]{0,25}(?:باز|بازگشایی)|(?:لغو|رفع|پایان)\s*محاصره|محاصره[^.؛]{0,15}(?:لغو|برداشته|رفع)"
           r"|توافق\s*هسته|برنامه\s*هسته|غنی\s*سازی|تبادل\s*زندان|آزادی\s*زندانی|زندانیان[^.؛]{0,15}آزاد|عقب\s*نشینی"
           r"|(?:لغو|رفع|تعلیق)\s*تحریم|تحریم\s*ها?[^.؛]{0,15}(?:لغو|برداشته|رفع|تعلیق)"
           r"|پیش\s*نویس\s*توافق|متن\s*توافق|توافق\s*(?:صلح|جامع|نهایی|موقت|پنج\s*روزه|چند\s*روزه)|طرح\s*صلح")
MINOR_FA = r"مکث|آتش\s*بس\s*انسانی|کریدور|کمک\s*های\s*بشردوستانه|حریم\s*هوایی|(?:ازسرگیری|از\s*سرگیری)\s*پرواز|مین\s*روبی"
CORE_EN = (r"\b(?:cease-?fire|truce|end (?:of |to )?the war|halt (?:to )?(?:the )?(?:strikes|attacks|fighting)|peace (?:deal|accord|agreement)"
           r"|reopen\w*[^.]{0,25}hormuz|hormuz[^.]{0,25}reopen\w*|(?:lift\w*|end\w*|eas\w*)[^.]{0,15}blockade|blockade[^.]{0,15}(?:lifted|ended|eased)"
           r"|nuclear (?:deal|agreement|accord)|enrichment|prisoner (?:swap|exchange)|prisoners? (?:freed|released)|withdraw\w*"
           r"|(?:lift\w*|eas\w*|suspend\w*|waiv\w*)[^.]{0,15}sanctions|sanctions[^.]{0,15}(?:lifted|eased|waived|suspended)"
           r"|draft (?:deal|agreement)|interim (?:deal|agreement)|peace (?:proposal|plan|talks|framework))\b")
MINOR_EN = (r"\b(?:humanitarian pause|corridor|aid deliveries|airspace reopen\w*|reopen\w*[^.]{0,15}airspace|flights? resum\w*"
            r"|resum\w*[^.]{0,15}flights?|mine[- ]?clearing|demining)\b")
OTHER_FRONT_FA = r"غزه|حماس(?![؀-ۿ])|لبنان|حزب\s*الله|یمن|حوثی|انصارالله|عربستان|سوریه|اوکراین|روسیه"
OTHER_FRONT_EN = r"\b(?:gaza|hamas|leban\w*|hezbollah|yemen\w*|houthis?|saudi\w*|syria\w*|ukrain\w*|russia\w*)\b"

# ------------------------------------------------------------------ how far
S5_FA = (r"(?:آتش\s*بس|توافق|تفاهم\s*نامه|ترک\s*مخاصمه)[^.؛]{0,35}(?:اجرایی\s*شد|برقرار\s*شد|آغاز\s*شد|اجرا\s*شد|به\s*اجرا\s*درآمد"
         r"|امضا\s*شد|امضا\s*کردند|امضا\s*کرد|لازم\s*الاجرا\s*شد|به\s*امضا\s*رسید)"
         r"|(?:تنگه\s*)?هرمز[^.؛]{0,20}(?:بازگشایی\s*شد|باز\s*شد)|بازگشایی\s*(?:تنگه\s*)?هرمز\s*(?:آغاز\s*شد|انجام\s*شد)"
         r"|محاصره[^.؛]{0,15}(?:لغو\s*شد|برداشته\s*شد|رفع\s*شد|پایان\s*یافت)|تحریم\s*ها?[^.؛]{0,20}(?:لغو\s*شد|برداشته\s*شد|رفع\s*شد|تعلیق\s*شد)"
         r"|(?:لغو|تعلیق)\s*(?:کرد|کردند)\s*[^.؛]{0,10}تحریم|تبادل\s*زندانیان\s*(?:انجام\s*شد|صورت\s*گرفت)|زندانیان[^.؛]{0,15}آزاد\s*شدند"
         r"|نیروها[^.؛]{0,20}عقب\s*نشینی\s*(?:کردند|کرد)")
S4_FA = (r"به\s*توافق\s*(?:رسیدند|رسید|دست\s*یافتند)|توافق\s*(?:شد|حاصل\s*شد|کردند)|(?:بر\s*سر|درباره)\s*آتش\s*بس\s*توافق"
         r"|آتش\s*بس[^.؛]{0,30}(?:اجرایی|آغاز|برقرار|اجرا)\s*(?:می\s*شود|خواهد\s*شد)|اعلام\s*آتش\s*بس|آتش\s*بس\s*(?:را\s*)?اعلام\s*(?:شد|کرد|کردند)"
         r"|موافقت\s*(?:کرد|کردند)[^.؛]{0,25}(?:آتش\s*بس|توافق|بازگشایی|لغو|تبادل|عقب\s*نشینی)")
S3_FA = (r"(?:مذاکرات|دور\s*\S+\s*(?:از\s*)?مذاکرات|نشست|دیدار|گفتگو|گفت\s*وگو|تماس\s*تلفنی)[^.؛]{0,45}"
         r"(?:برگزار\s*شد|انجام\s*شد|پایان\s*یافت|آغاز\s*شد|دیدار\s*کردند|دیدار\s*کرد|گفتگو\s*کردند|گفت\s*وگو\s*کردند|گفتگو\s*کرد|گفت\s*وگو\s*کرد)"
         r"|(?:دیدار|گفتگو|گفت\s*وگو)\s*(?:کردند|کرد)")
S2_FA = (r"(?:پیشنهاد|طرح|پیش\s*نویس|متن|بسته|برنامه)[^.؛]{0,45}(?:ارائه\s*(?:کرد|کردند|شد|داد)|تحویل|دریافت\s*(?:کرد|کردند|شد)"
         r"|داد|دادند|فرستاد|ارسال\s*(?:کرد|شد))|(?:ارائه|تحویل)\s*(?:پیشنهاد|طرح|پیش\s*نویس)")
S1_FA = r"مذاکر|گفتگو|گفت\s*وگو|دیدار|رایزنی|نشست|میانجی|پیشنهاد|طرح|توافق|تماس|کاهش\s*تنش|دیپلماسی"
S5_EN = (r"\b(?:cease-?fire|truce|agreement|deal|accord)\b[^.]{0,35}(?<!will )(?<!to )\b(?:takes effect|took effect|has taken effect"
         r"|comes into (?:force|effect)|came into (?:force|effect)|(?:is|now) in force|is holding|holds|was signed|signed|began|started"
         r"|went into effect|goes into effect)\b|\bsign(?:s|ed)\b[^.]{0,25}\b(?:agreement|deal|accord|cease-?fire)\b"
         r"|\bhormuz\b[^.]{0,25}\breopen(?:s|ed)\b|\breopen(?:s|ed)\b[^.]{0,20}\bhormuz\b|\bblockade\b[^.]{0,15}\b(?:lifted|ended)\b"
         r"|\b(?:lifts?|lifted|eases?|eased|suspends?|suspended|waives?|waived)\b[^.]{0,20}\bsanctions\b|\bsanctions\b[^.]{0,15}\b(?:lifted|eased|waived|suspended)\b"
         r"|\bprisoner (?:swap|exchange)\b[^.]{0,20}\b(?:completed|carried out|takes place|took place)\b|\bprisoners? (?:freed|released)\b")
S4_EN = (r"\b(?:agree|agreed|agrees|reach|reached|reaches|strike|struck)\b[^.]{0,25}\b(?:cease-?fire|truce|deal|agreement|accord)\b"
         r"|\b(?:cease-?fire|truce)\b[^.]{0,30}\b(?:announced|to take effect|will take effect|from (?:tomorrow|midnight|monday|tuesday"
         r"|wednesday|thursday|friday|saturday|sunday))\b|\bannounces?\b[^.]{0,20}\b(?:cease-?fire|truce)\b"
         r"|\b(?:cease-?fire|truce)\b[^.]{0,30}\b(?:will|to) (?:start|begin|take effect|come into (?:force|effect))\b")
S3_EN = (r"\b(?:talks|negotiations|round of talks|meeting)\b[^.]{0,40}\b(?:held|took place|concluded|ended|began|opened|wrapped up)\b"
         r"|\b(?:met|meet|meets|held talks|hold talks|holds talks|spoke|speaks|phoned)\b(?!\s+(?:\w+\s+){0,2}(?:conditions|demands|terms"
         r"|deadline|requirements|goals|needs|obligations|expectations|criteria))")
S2_EN = (r"\b(?:proposal|plan|draft|offer|framework|text|package)\b[^.]{0,40}\b(?:presented|submitted|handed|delivered|sent|received"
         r"|tabled|put forward)\b|\b(?:presents?|submits?|hands?|delivers?|sends?|receives?|tables?|puts? forward)\b[^.]{0,30}"
         r"\b(?:proposal|plan|draft|offer|framework)\b")
S1_EN = (r"\b(?:talks?|negotiat\w+|meet\w*|met|discuss\w*|mediat\w+|proposal|plan|deal|agreement|calls?|phoned|phone|spoke"
         r"|speaks|de-?escalat\w*|diplomac\w*)\b")

HEDGE_FA = (r"ممکن|احتمال|در\s*صورت|اگر|در\s*تلاش|تلاش\s*برای|خواستار|آماده|آمادگی|امیدوار|نزدیک\s*است|شاید|بررسی\s*(?:می|کرد)"
            r"|به\s*زودی|می\s*تواند|می\s*توان|باید|مشروط|ادعا|شرایط|شرط|یا\s")
HEDGE_EN = (r"\b(?:may|might|could|if|would|trying|seeks?|seeking|urges?|calls? for|ready|hopes?|hopeful|close to|nearing|soon"
            r"|considering|weighs?|possible|potential|expected to|likely|plans? to|must|should|need to|or)\b")
FUTURE_EN = r"\b(?:will|set to|to (?:meet|hold|sign|resume|discuss|start|begin)|next (?:week|month)|tomorrow|later)\b"
FUTURE_FA = r"خواهد|خواهند|قرار\s*است|فردا|هفته\s*آینده|آینده|می\s*کند|می\s*کنند|برگزار\s*می\s*شود"
DENY_FA = r"تکذیب|صحت\s*ندارد|کذب|شایعه|هیچ\s*(?:مذاکره|توافق|آتش\s*بس|دیدار|گفتگو)|وجود\s*ندارد|نفی\s*کرد|خبری\s*نیست"
DENY_EN = r"\b(?:den(?:y|ies|ied)|no talks|no deal|no cease-?fire|not true|false|fake|rumou?rs?)\b"
REJECT_FA = r"(?:رد\s*(?:کرد|کردند|شد)|نپذیرفت|نپذیرفتند|غیر\s*قابل\s*قبول)"
REJECT_EN = r"\b(?:rejects?|rejected|refuses?|refused|turns? down|turned down|dismiss(?:es|ed)?)\b"
BROKEN_FA = r"نقض|شکست|فروپاشی|پایان\s*آتش\s*بس|آتش\s*بس[^.؛]{0,15}(?:شکست|پایان\s*یافت|نقض)"
BROKEN_EN = r"\b(?:violat\w*|breach\w*|collaps\w*|broke down|breaks down|shatter\w*|ends? (?:the )?(?:cease-?fire|truce))\b"


def _rx(p, flags=0):
    return re.compile(p, flags)


_C = {k: _rx(v.translate(FA_MAP)) for k, v in {                # the text is normalised (ئ -> ی, ZWNJ -> space); so are these
    "t3": T3_FA, "t2": T2_FA, "un": UNNAMED_FA, "core": CORE_FA, "minor": MINOR_FA, "s5": S5_FA, "s4": S4_FA,
    "s3": S3_FA, "s2": S2_FA, "s1": S1_FA, "hedge": HEDGE_FA, "future": FUTURE_FA, "deny": DENY_FA, "reject": REJECT_FA, "broken": BROKEN_FA,
    "ir": IR_SIDE_FA, "us": OTHER_SIDE_FA, "other": OTHER_FRONT_FA}.items()}
_E = {k: _rx(v, re.I) for k, v in {
    "t3": T3_EN, "t2": T2_EN, "un": UNNAMED_EN, "core": CORE_EN, "minor": MINOR_EN, "s5": S5_EN, "s4": S4_EN,
    "s3": S3_EN, "s2": S2_EN, "s1": S1_EN, "hedge": HEDGE_EN, "future": FUTURE_EN, "deny": DENY_EN, "reject": REJECT_EN, "broken": BROKEN_EN,
    "ir": IR_SIDE_EN, "us": OTHER_SIDE_EN, "other": OTHER_FRONT_EN}.items()}


def grade(lang, title, summary="", rel=0.6, channel=False):
    """None, or a dict with the stage, the confirmation, the severity and the flags a de-escalation story gets."""
    X = _C if lang == "fa" else _E
    t = fa_norm(title or "") if lang == "fa" else (title or "")
    s = fa_norm(first_sentences(summary or "", 220)) if lang == "fa" else first_sentences(summary or "", 220)
    if not X["s1"].search(t) and not X["core"].search(t):
        return None
    if X["broken"].search(t):
        return None                                  # a ceasefire broken or talks collapsed: escalation, other rules
    core, minor = bool(X["core"].search(t)), bool(X["minor"].search(t))
    if X["s5"].search(t):
        stage = 5
    elif X["s4"].search(t):
        stage = 4
    elif X["s3"].search(t):
        stage = 3
    elif X["s2"].search(t):
        stage = 2
    else:
        stage = 1
    m_stage = next((X[k].search(t) for k in ("s5", "s4", "s3", "s2") if X[k].search(t)), None)
    rest = t[:m_stage.start()] + " " + t[m_stage.end():] if m_stage else t     # "will take effect" is the stage itself
    deny = bool(X["deny"].search(t))
    reject = bool(X["reject"].search(t)) and (core or X["s2"].search(t) or re.search(r"پیشنهاد|طرح|proposal|plan|offer", t, re.I))
    if deny:
        stage = 0
    elif X["hedge"].search(rest):
        stage = min(stage, 1)                        # "could reach a deal", "must meet our conditions": not an event
    elif X["future"].search(rest):
        # something still to come: an agreed ceasefire starting tomorrow stays agreed (4); talks or an offer to come
        # are only a contact
        stage = 4 if stage >= 4 else min(stage, 1)
    both = bool(X["ir"].search(t)) and bool(X["us"].search(t))         # in the headline itself
    direct = both and not (X["other"].search(t) and not X["ir"].search(t))
    if stage >= 2 and not core:
        if minor:
            stage -= 1
        elif not (stage == 3 and direct):            # talks between the warring parties need no named subject
            stage = 1
    elif minor and not core:
        stage = max(0, stage - 1)
    # who confirms
    if channel:
        conf = 0
    elif X["t3"].search(t) and not X["un"].search(t[:60]):
        conf = 3
    elif X["t2"].search(t) and not X["un"].search(t[:60]):
        conf = 2
    elif rel >= 0.8:
        conf = 1
    else:
        conf = 0
    if stage == 3 and conf == 3 and not direct:
        conf = 2                                     # an Iranian minister meeting a third country: a contact
        stage = 1 if not core else stage
    sev = float(GRID[stage][3 - conf])
    if stage == 2 and conf == 1 and not core:
        sev = 40.0
    if not direct and sev > OTHER_FRONT_CAP:
        sev = OTHER_FRONT_CAP
    flags = set()
    if stage >= 2:
        flags.add("deesc")
    if stage >= 3 and conf == 3 and direct:
        flags.add("deesc_sure")                      # the green "de-escalation" tag
    if stage >= 4 and conf == 3 and direct:
        flags.add("deesc_event")                     # may be red
    is_cease = bool(re.search(r"آتش\s*بس|ترک\s*مخاصمه|cease-?fire|truce", t, re.I))
    if stage == 5 and conf == 3 and direct and is_cease:
        flags.add("ceasefire_on")                    # the index treats the war as paused (index.py)
    if stage in (3, 4) and conf == 3 and direct:
        flags.add("talks_held")
    if deny and conf == 3 and (is_cease or core or re.search(r"مذاکر|توافق|talks|deal|agreement", t, re.I)):
        flags.add("deesc_denial")
    if reject and conf == 3 and direct:
        flags.add("talks_fail")                      # an official no to a proposal pushes the other way
        sev = max(sev, 58.0)
    return {"stage": stage, "conf": conf, "direct": direct, "core": core, "sev": sev, "flags": flags}
