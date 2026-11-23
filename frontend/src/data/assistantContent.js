/** Reviewed, scripted content for the health assistant (English and Kiswahili). Carried over from ReproCare v0.8. */
export const ui = {
  en: {
    title: "Ask the assistant",
    intro:
      "General information about reproductive and sexual health, and help finding your way around ReproCare.",
    what: "What would you like to know?",
    try: "Try one of these, or type your own question.",
    placeholder: "Ask a general question, for example about contraception",
    privacy: "Do not share names, phone numbers or personal health details.",
    newChat: "New conversation",
    find: "Find",
    near: "near you",
    demo: "General information only, not medical advice.",
    urgentT: "This may need urgent care",
    urgentB:
      "What you describe can be a sign of a medical emergency. Call 999 or 112, or go to the nearest emergency department now. If you can, ask someone to go with you.",
    urgentS: "The assistant will not continue routine answers on this topic.",
    personal:
      "That question depends on your own health and history, so it needs a health worker who can assess you. I can share general information, or help you find a facility that offers the right service.",
    unknown:
      "I do not have reviewed information on that yet. I can answer general questions about antenatal care, fertility consultations, contraception, STI testing and cervical screening, or help you find outreach programmes, laboratories and specialists.",
    writing: "Assistant is writing",
    boundaries: "What it will not do",
    b1: "Diagnose, prescribe, or assess your personal risk",
    b2: "Replace a health worker who knows your history",
    b3: "Keep chatting if you describe emergency symptoms",
    mode: "Answers are selected from ReproCare’s guides in English and Kiswahili. Questions stay in this browser tab.",
  },
  sw: {
    title: "Uliza msaidizi",
    intro:
      "Taarifa za jumla kuhusu afya ya uzazi na ngono, na msaada wa kutumia ReproCare.",
    what: "Ungependa kujua nini?",
    try: "Jaribu mojawapo ya haya, au andika swali lako.",
    placeholder: "Uliza swali la jumla, kwa mfano kuhusu uzazi wa mpango",
    privacy:
      "Usishiriki majina, nambari za simu au taarifa zako binafsi za afya.",
    newChat: "Mazungumzo mapya",
    find: "Tafuta",
    near: "karibu nawe",
    demo: "Taarifa za jumla tu, si ushauri wa matibabu.",
    urgentT: "Huenda hii ikahitaji huduma ya dharura",
    urgentB:
      "Unachoeleza kinaweza kuwa dalili ya dharura ya kiafya. Piga 999 au 112, au nenda kwenye idara ya dharura iliyo karibu sasa hivi. Ikiwezekana, mwombe mtu aende nawe.",
    urgentS: "Msaidizi hataendelea na majibu ya kawaida kuhusu mada hii.",
    personal:
      "Swali hilo linategemea afya na historia yako binafsi, kwa hivyo linahitaji mhudumu wa afya anayeweza kukuchunguza. Ninaweza kukupa taarifa za jumla, au kukusaidia kupata kituo kinachotoa huduma inayofaa.",
    unknown:
      "Bado sina taarifa zilizokaguliwa kuhusu hilo. Ninaweza kujibu maswali ya jumla kuhusu kliniki ya wajawazito, ushauri wa uzazi, uzazi wa mpango, kupima magonjwa ya zinaa na uchunguzi wa saratani ya shingo ya kizazi.",
    writing: "Msaidizi anaandika",
    boundaries: "Mambo ambayo hatafanya",
    b1: "Kutambua ugonjwa, kuagiza dawa au kupima hatari yako binafsi",
    b2: "Kuchukua nafasi ya mhudumu wa afya anayejua historia yako",
    b3: "Kuendelea na mazungumzo ukieleza dalili za dharura",
    mode: "Majibu yanachaguliwa kutoka miongozo ya ReproCare kwa Kiingereza na Kiswahili. Maswali yanabaki katika kichupo hiki cha kivinjari.",
  },
};

export const suggestedQuestions = {
  en: [
    "What happens at a first antenatal visit?",
    "What should I expect during my first fertility consultation?",
    "What contraception options are there?",
    "How does STI testing work?",
    "Where can I find a free screening event?",
  ],
  sw: [
    "Nini hufanyika katika ziara ya kwanza ya kliniki ya wajawazito?",
    "Nitarajie nini katika ushauri wangu wa kwanza wa uzazi?",
    "Kuna njia gani za uzazi wa mpango?",
    "Kupima magonjwa ya zinaa hufanyikaje?",
    "Ninaweza kupata wapi uchunguzi wa bure?",
  ],
};

export const scripted = [
  {
    id: "antenatal",
    match: [
      "antenatal",
      "pregnan",
      "prenatal",
      "anc",
      "first visit",
      "mimba",
      "mjamzito",
      "ujauzito",
      "wajawazito",
    ],
    question: {
      en: "What happens at a first antenatal visit?",
      sw: "Nini hufanyika katika ziara ya kwanza ya kliniki ya wajawazito?",
    },
    paragraphs: {
      en: [
        "A first antenatal visit is usually a longer appointment where a health worker checks your general health and plans the rest of your pregnancy care. Going early, ideally before 12 weeks, is commonly recommended.",
      ],
      sw: [
        "Ziara ya kwanza ya kliniki ya wajawazito kwa kawaida huchukua muda mrefu zaidi. Mhudumu wa afya hukagua afya yako kwa jumla na kupanga huduma yako katika kipindi chote cha ujauzito. Inapendekezwa kwenda mapema, ikiwezekana kabla ya wiki 12.",
      ],
    },
    bullets: {
      en: [
        "Questions about your health, past pregnancies and your last period",
        "Blood pressure and weight checks",
        "Blood tests often offered for anaemia, blood group, HIV, syphilis and hepatitis B",
        "A urine test",
        "Advice on iron and folic acid, and when to return",
      ],
      sw: [
        "Maswali kuhusu afya yako, mimba zilizopita na hedhi yako ya mwisho",
        "Kupimwa shinikizo la damu na uzito",
        "Vipimo vya damu kwa kawaida hutolewa kwa upungufu wa damu, kundi la damu, VVU, kaswende na homa ya ini B",
        "Kipimo cha mkojo",
        "Ushauri kuhusu madini ya chuma na asidi ya foliki, na lini urudi",
      ],
    },
    uncertainty: {
      en: "Schedules and included tests differ between facilities. Ask the facility what their first visit covers.",
      sw: "Ratiba na vipimo hutofautiana kati ya vituo. Uliza kituo kinachohusika ziara ya kwanza inajumuisha nini.",
    },
    sources: [
      {
        title: "Your first antenatal visit: what to expect",
        publisher: "ReproCare health library",
        articleId: "first-antenatal-visit",
      },
      {
        title: "WHO antenatal care recommendations (2016)",
        publisher: "World Health Organization",
      },
    ],
    serviceId: "antenatal",
  },
  {
    id: "fertility",
    match: [
      "fertility",
      "conceive",
      "infertil",
      "trying for a baby",
      "ivf",
      "ushauri wa uzazi",
      "ushauri wangu wa kwanza wa uzazi",
      "kupata mtoto",
      "kushika mimba",
    ],
    question: {
      en: "What should I expect during my first fertility consultation?",
      sw: "Nitarajie nini katika ushauri wangu wa kwanza wa uzazi?",
    },
    paragraphs: {
      en: [
        "A first fertility consultation is mostly about understanding your history and deciding which tests make sense. Both partners are often assessed, because fertility concerns can involve either person.",
      ],
      sw: [
        "Ushauri wa kwanza kuhusu uzazi unalenga kuelewa historia yako na kuamua vipimo vinavyofaa. Mara nyingi wenzi wote wawili hufanyiwa tathmini, kwa sababu changamoto za uzazi zinaweza kumhusu yeyote kati yao.",
      ],
    },
    bullets: {
      en: [
        "A detailed history: cycle pattern, previous pregnancies, illnesses, medicines and lifestyle",
        "Possible tests: blood hormone tests, an ultrasound, and a semen analysis for a male partner",
        "A plan for next steps and an estimate of costs",
        "It is commonly advised to seek assessment after 12 months of trying, or after 6 months if the woman is 35 or older",
      ],
      sw: [
        "Historia ya kina: mzunguko wa hedhi, mimba zilizopita, magonjwa, dawa na mtindo wa maisha",
        "Vipimo vinavyowezekana: vipimo vya homoni kwenye damu, ultrasound, na uchunguzi wa mbegu za kiume kwa mwenzi wa kiume",
        "Mpango wa hatua zinazofuata na makadirio ya gharama",
        "Kwa kawaida hushauriwa kutafuta tathmini baada ya miezi 12 ya kujaribu, au miezi 6 ikiwa mwanamke ana umri wa miaka 35 au zaidi",
      ],
    },
    uncertainty: {
      en: "The right tests depend on your individual history, which only a clinician can assess.",
      sw: "Vipimo vinavyofaa hutegemea historia yako binafsi, ambayo ni mhudumu wa afya pekee anayeweza kuitathmini.",
    },
    sources: [
      {
        title: "Preparing for a fertility consultation",
        publisher: "ReproCare health library",
        articleId: "fertility-consultation",
      },
      {
        title: "Infertility: key facts",
        publisher: "World Health Organization",
      },
    ],
    serviceId: "fertility",
    nav: [
      {
        label: {
          en: "See fertility specialists",
          sw: "Tazama wataalamu wa uzazi",
        },
        href: "/find-care/specialists",
      },
    ],
  },
  {
    id: "contraception",
    match: [
      "contracept",
      "family planning",
      "implant",
      "iud",
      "coil",
      "pill",
      "injection",
      "condom",
      "uzazi wa mpango",
      "kondomu",
      "kitanzi",
      "sindano",
    ],
    question: {
      en: "What contraception options are there?",
      sw: "Kuna njia gani za uzazi wa mpango?",
    },
    paragraphs: {
      en: [
        "There are several types of contraception, and counselling helps match a method to your health and preferences.",
      ],
      sw: [
        "Kuna aina kadhaa za uzazi wa mpango, na ushauri husaidia kuchagua njia inayofaa afya na mapendeleo yako.",
      ],
    },
    bullets: {
      en: [
        "Short-acting: pills, injections and condoms",
        "Long-acting reversible: implants and intrauterine devices (IUDs), which last for years and can be removed",
        "Permanent: tubal ligation or vasectomy",
        "Emergency contraception after unprotected sex, which works best the sooner it is used",
        "Condoms are the only method that also reduces the risk of STIs",
      ],
      sw: [
        "Za muda mfupi: vidonge, sindano na kondomu",
        "Za muda mrefu zinazoweza kuondolewa: vipandikizi (implant) na kitanzi (IUD), vinavyodumu kwa miaka na vinaweza kuondolewa",
        "Za kudumu: kufunga kizazi kwa mwanamke au mwanamume (vasectomy)",
        "Uzazi wa mpango wa dharura baada ya ngono isiyo salama, unaofanya kazi vizuri zaidi ukitumiwa mapema",
        "Kondomu ndiyo njia pekee inayosaidia pia kupunguza hatari ya magonjwa ya zinaa",
      ],
    },
    uncertainty: {
      en: "Which method suits you depends on your health history. A family planning provider can go through this privately.",
      sw: "Njia inayokufaa inategemea historia yako ya afya. Mhudumu wa uzazi wa mpango anaweza kukueleza faraghani.",
    },
    sources: [
      {
        title: "Comparing contraception options",
        publisher: "ReproCare health library",
        articleId: "contraception-options",
      },
      {
        title: "Medical eligibility criteria for contraceptive use",
        publisher: "World Health Organization",
      },
    ],
    serviceId: "contraception",
  },
  {
    id: "sti",
    match: [
      "sti",
      "std",
      "sexually transmitted",
      "syphilis",
      "chlamydia",
      "gonorr",
      "hiv test",
      "testing",
      "zinaa",
      "kupima",
      "vvu",
    ],
    question: {
      en: "How does STI testing work?",
      sw: "Kupima magonjwa ya zinaa hufanyikaje?",
    },
    paragraphs: {
      en: [
        "Many STIs cause no symptoms, so testing is the reliable way to know. Most tests are quick and confidential.",
      ],
      sw: [
        "Magonjwa mengi ya zinaa hayaonyeshi dalili, kwa hivyo kupima ndiyo njia ya uhakika ya kujua. Vipimo vingi ni vya haraka na vya siri.",
      ],
    },
    bullets: {
      en: [
        "Urine samples or swabs are commonly used for chlamydia and gonorrhoea",
        "Blood or finger-prick tests are commonly used for HIV, syphilis and hepatitis B",
        "Some tests may need repeating if done very soon after a possible exposure",
        "For a possible HIV exposure in the last 72 hours, ask a facility urgently about PEP",
      ],
      sw: [
        "Sampuli ya mkojo au usufi hutumika kwa kawaida kupima klamidia na kisonono",
        "Vipimo vya damu au kuchomwa kidole hutumika kwa VVU, kaswende na homa ya ini B",
        "Baadhi ya vipimo huhitaji kurudiwa ikiwa vimefanywa mapema sana baada ya hatari",
        "Ikiwa ulikuwa katika hatari ya kuambukizwa VVU ndani ya saa 72 zilizopita, uliza kituo cha afya haraka kuhusu PEP",
      ],
    },
    uncertainty: {
      en: "Which tests you need depends on your situation. A health worker can advise privately.",
      sw: "Vipimo unavyohitaji vinategemea hali yako. Mhudumu wa afya anaweza kukushauri faraghani.",
    },
    sources: [
      {
        title: "STI testing: how it works and what to ask",
        publisher: "ReproCare health library",
        articleId: "sti-testing",
      },
      {
        title: "WHO STI management guidelines (2021)",
        publisher: "World Health Organization",
      },
    ],
    serviceId: "sti",
    nav: [
      {
        label: {
          en: "Compare laboratory tests",
          sw: "Linganisha vipimo vya maabara",
        },
        href: "/find-care/laboratories",
      },
    ],
  },
  {
    id: "cervical",
    match: ["cervical", "pap", "via", "hpv", "shingo ya kizazi"],
    question: {
      en: "What is cervical screening?",
      sw: "Uchunguzi wa saratani ya shingo ya kizazi ni nini?",
    },
    paragraphs: {
      en: [
        "Cervical screening looks for changes in the cervix before they become cancer. It is a check for people without symptoms, not a test for symptoms.",
      ],
      sw: [
        "Uchunguzi wa shingo ya kizazi hutafuta mabadiliko kwenye shingo ya kizazi kabla hayajawa saratani. Ni kipimo kwa watu wasio na dalili.",
      ],
    },
    bullets: {
      en: [
        "Common methods include VIA (visual inspection), Pap smear and HPV testing",
        "How often you are screened depends on the method and your age",
        "Abnormal results usually lead to follow-up or simple treatment, not a cancer diagnosis",
      ],
      sw: [
        "Njia za kawaida ni VIA (ukaguzi wa macho), Pap smear na kipimo cha HPV",
        "Mara ngapi unachunguzwa inategemea njia na umri wako",
        "Matokeo yasiyo ya kawaida kwa kawaida husababisha ufuatiliaji au matibabu rahisi, si utambuzi wa saratani",
      ],
    },
    uncertainty: {
      en: "Ask the facility which method they use and when to come back.",
      sw: "Uliza kituo kinatumia njia gani na lini urudi.",
    },
    sources: [
      {
        title: "Cervical screening explained",
        publisher: "ReproCare health library",
        articleId: "cervical-screening",
      },
      {
        title:
          "Guideline for screening and treatment of cervical pre-cancer lesions",
        publisher: "World Health Organization",
      },
    ],
    serviceId: "cervical",
    nav: [
      {
        label: {
          en: "Find free screening outreach",
          sw: "Tafuta uchunguzi wa bure",
        },
        href: "/health-community/programmes",
      },
    ],
  },
  {
    id: "navigate",
    match: [
      "free",
      "outreach",
      "campaign",
      "event",
      "bure",
      "kampeni",
      "insurance",
      "bima",
      "lab",
      "maabara",
      "programme",
      "program",
    ],
    question: {
      en: "Where can I find a free screening event?",
      sw: "Ninaweza kupata wapi uchunguzi wa bure?",
    },
    paragraphs: {
      en: [
        "ReproCare has separate sections for each kind of help. Here is where to look:",
      ],
      sw: [
        "ReproCare ina sehemu tofauti kwa kila aina ya msaada. Hapa ndipo pa kutazama:",
      ],
    },
    bullets: {
      en: [
        "Outreach lists free and subsidised screenings, testing days and education sessions from organisers",
        "Laboratories compares provider-supplied test details and prices",
        "Insurance shows facilities that report accepting your insurer",
      ],
      sw: [
        "Kampeni za jamii zinaonyesha uchunguzi wa bure na wa bei nafuu, siku za kupima na vipindi vya elimu kutoka kwa waandaaji",
        "Maabara inalinganisha maelezo ya vipimo na bei yaliyotolewa na watoa huduma",
        "Bima inaonyesha vituo vinavyosema vinakubali bima yako",
      ],
    },
    sources: [],
    nav: [
      {
        label: { en: "Open Outreach", sw: "Fungua kampeni za jamii" },
        href: "/health-community/programmes",
      },
      {
        label: { en: "Open Laboratories", sw: "Fungua maabara" },
        href: "/find-care/laboratories",
      },
      {
        label: { en: "Open Insurance", sw: "Fungua bima" },
        href: "/find-care/insurance",
      },
    ],
  },
];

export const urgentTerms = [
  "heavy bleeding",
  "bleeding a lot",
  "severe pain",
  "severe abdominal",
  "fits",
  "convulsion",
  "seizure",
  "unconscious",
  "fainted",
  "cannot breathe",
  "can't breathe",
  "blurred vision",
  "baby not moving",
  "baby stopped moving",
  "high fever",
  "emergency",
  "kutokwa damu nyingi",
  "damu nyingi",
  "maumivu makali",
  "degedege",
  "kuzirai",
  "mtoto haichezi",
  "dharura",
];
export const personalTerms = [
  "do i have",
  "should i take",
  "what dose",
  "how much should i take",
  "diagnose",
  "is it normal that i",
  "my results",
  "am i pregnant",
  "prescribe",
  "nina ugonjwa",
  "nitumie dawa gani",
  "je nina mimba",
  "matokeo yangu",
];
