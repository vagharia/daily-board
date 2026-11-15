"""America's military bases in the Middle East and around it: the one list the rules read.

key -> (Persian, English, Persian forms, English forms, country, Gulf city key or None).
country: a code of fronts' Gulf rules (bh, qa, kw, ae, sa, om, iq, jo) or sy, tr, dj, io for Syria, Turkey, Djibouti
and Diego Garcia. Gulf city key: the city key of fronts._GULF_EN the base lies in or by ("bahrain" for all of
Bahrain, "qatar" for Qatar, "kuwait" for Kuwait), None for a base far from those cities (Ain al-Asad in Anbar).

Used by abroad_strike.py (one attack on one place abroad, one story) and, for the bases the panel didn't know yet,
by front_places.ABROAD (the main-front panel). Names that are also common words are taken only in a longer form
(«کمپ پاتریوت», not «پاتریوت», the missile)."""


def _b(fa, en, faf, enf, ctry, city):
    return (fa, en, [fa, *faf], [en.lower(), *enf], ctry, city)


BASES = {
    # ---- Bahrain: the whole country is one place (fronts: "bahrain"); a base in it is a target of its own
    "fifth_fleet": _b("مقر ناوگان پنجم آمریکا", "the US Fifth Fleet base",
                      ["ناوگان پنجم", "مقر ناوگان پنجم", "پایگاه ناوگان پنجم", "پایگاه دریایی آمریکا در بحرین",
                       "پایگاه دریایی آمریکا در منامه", "الجفیر", "جفیر"],
                      ["fifth fleet", "5th fleet", "naval support activity bahrain", "nsa bahrain", "juffair",
                       "us naval base in bahrain", "us navy base in bahrain"], "bh", "bahrain"),
    "isa_ab": _b("پایگاه عیسی", "Isa air base", ["پایگاه هوایی شیخ عیسی", "پایگاه شیخ عیسی", "پایگاه هوایی عیسی"],
                 ["isa air base", "shaikh isa air base", "sheikh isa air base", "isa airbase"], "bh", "bahrain"),
    "riffa": _b("پایگاه الرفاع", "Riffa base", ["پایگاه بالگردی الرفاع", "پایگاه رفاع", "الرفاع", "رفاع"],
                ["riffa", "al-riffa", "al riffa", "ar-rifa", "rifa air base"], "bh", "bahrain"),
    # ---- Qatar
    "al_udeid": _b("پایگاه العدید", "Al Udeid base", ["العدید", "پایگاه هوایی العدید"],
                   ["al udeid", "al-udeid", "udeid"], "qa", "qatar"),
    "as_sayliyah": _b("کمپ السیلیه", "Camp As Sayliyah", ["السیلیه", "پایگاه السیلیه"],
                      ["camp as sayliyah", "as-sayliyah", "as sayliyah", "al-sayliyah"], "qa", "qatar"),
    # ---- the Emirates
    "al_dhafra": _b("پایگاه الظفره", "Al Dhafra base", ["الظفره", "پایگاه هوایی الظفره"],
                    ["al dhafra", "al-dhafra"], "ae", "abu_dhabi"),
    # ---- Kuwait
    "arifjan": _b("کمپ عریفجان", "Camp Arifjan", ["اردوگاه عریفجان", "عریفجان", "پایگاه عریفجان"], ["arifjan"],
                  "kw", "kuwait"),
    "ali_al_salem": _b("پایگاه علی السالم", "Ali Al Salem air base", ["علی السالم", "پایگاه هوایی علی السالم"],
                       ["ali al salem", "ali al-salem"], "kw", "kuwait"),
    "buehring": _b("کمپ بیورینگ", "Camp Buehring", ["بیورینگ", "پایگاه بیورینگ"], ["buehring"], "kw", "kuwait"),
    "camp_patriot": _b("کمپ پاتریوت", "Camp Patriot", ["اردوگاه پاتریوت"], ["camp patriot"], "kw", "kuwait"),
    "ahmad_al_jaber": _b("پایگاه احمد الجابر", "Ahmad al-Jaber air base", ["احمد الجابر"],
                         ["ahmad al-jaber", "ahmed al jaber", "ahmad al jaber", "ahmed al-jaber"], "kw", "kuwait"),
    # ---- Saudi Arabia
    "prince_sultan": _b("پایگاه شاهزاده سلطان", "Prince Sultan air base",
                        ["پایگاه پرنس سلطان", "پایگاه الخرج", "پایگاه هوایی شاهزاده سلطان", "پایگاه هوایی الخرج"],
                        ["prince sultan air base", "prince sultan airbase", "al-kharj air base", "al kharj air base"],
                        "sa", None),
    "eskan": _b("اسکان ویلج", "Eskan Village", ["پایگاه اسکان"], ["eskan village"], "sa", "riyadh"),
    # ---- Oman
    "thumrait": _b("پایگاه ثمریت", "Thumrait air base", ["ثمریت"], ["thumrait"], "om", None),
    "masirah": _b("پایگاه مصیره", "Masirah air base", ["جزیره مصیره", "مصیره"], ["masirah"], "om", None),
    "musannah": _b("پایگاه المصنعه", "Al Musannah air base", ["المصنعه"], ["musannah", "al-musannah"], "om", "muscat"),
    # ---- Jordan
    "muwaffaq": _b("پایگاه موفق السلطی", "Muwaffaq Salti air base", ["موفق السلطی", "پایگاه الازرق"],
                   ["muwaffaq salti", "muwaffaq al-salti", "azraq air base"], "jo", None),
    "tower22": _b("برج ۲۲", "Tower 22", ["برج 22"], ["tower 22"], "jo", None),
    # ---- Iraq
    "ain_asad": _b("پایگاه عین الاسد", "Ain al-Asad base", ["عین الاسد", "پایگاه هوایی عین الاسد"],
                   ["ain al-asad", "ain al asad", "al-asad air base", "al asad air base", "ain al-assad"], "iq", None),
    "harir": _b("پایگاه حریر", "Harir base", ["پایگاه هوایی حریر"], ["harir air base", "harir base"], "iq", "erbil"),
    "erbil_ab": _b("پایگاه هوایی اربیل", "Erbil air base", ["پایگاه آمریکا در اربیل", "پایگاه آمریکایی اربیل"],
                   ["erbil air base", "erbil airbase", "us base in erbil"], "iq", "erbil"),
    "victory": _b("پایگاه ویکتوری", "Victory base", ["ویکتوری"], ["camp victory", "victory base"], "iq", "baghdad"),
    "union3": _b("پایگاه یونیون ۳", "Union III base", ["یونیون 3", "یونیون ۳", "یونیون سه"],
                 ["union iii", "union 3", "camp union"], "iq", "baghdad"),
    "balad": _b("پایگاه بلد", "Balad air base", ["پایگاه هوایی بلد"], ["balad air base", "balad airbase"], "iq", None),
    # ---- Syria
    "tanf": _b("پایگاه التنف", "al-Tanf base", ["التنف"], ["al-tanf", "al tanf", "tanf"], "sy", None),
    "conoco": _b("پایگاه کونیکو", "Conoco base", ["میدان گازی کونیکو", "کونیکو"], ["conoco gas field", "conoco base"],
                 "sy", None),
    "omar_field": _b("میدان نفتی العمر", "al-Omar oil field", ["پایگاه العمر"],
                     ["al-omar oil field", "omar oil field", "al-omar base"], "sy", None),
    "shaddadi": _b("پایگاه الشدادی", "al-Shaddadi base", ["الشدادی"], ["shaddadi"], "sy", None),
    "rmeilan": _b("پایگاه رمیلان", "Rmeilan base", ["رمیلان"], ["rmeilan", "rumeilan"], "sy", None),
    "kharab_jir": _b("پایگاه خراب الجیر", "Kharab al-Jir base", ["خراب الجیر"], ["kharab al-jir", "kharab al jir"],
                     "sy", None),
    "qasrak": _b("پایگاه قسرک", "Qasrak base", ["قسرک"], ["qasrak"], "sy", None),
    "green_village": _b("پایگاه القریه الخضراء", "Green Village base", ["القریه الخضراء", "روستای سبز"],
                        ["green village"], "sy", None),
    # ---- Turkey, the Horn of Africa, the Indian Ocean
    "incirlik": _b("پایگاه اینجرلیک", "Incirlik air base", ["اینجرلیک"], ["incirlik"], "tr", None),
    "kurecik": _b("رادار کورجیک", "Kurecik radar", ["کورجیک", "پایگاه کورجیک"], ["kurecik", "kürecik"], "tr", None),
    "lemonnier": _b("کمپ لمونیه", "Camp Lemonnier", ["لمونیه"], ["lemonnier"], "dj", None),
    "diego_garcia": _b("دیگو گارسیا", "Diego Garcia", ["دیه گو گارسیا", "دیگوگارسیا"], ["diego garcia"], "io", None),
}
