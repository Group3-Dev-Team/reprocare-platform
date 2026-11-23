export const kenyaWeeklyReports =
  "https://afro.who.int/countries/kenya/publication/kenya-health-emergencies-weekly-situation-reports-2026";

export const healthUpdates = [
  {
    id: "who-kenya-2026-week-46",
    topic: "Mpox and Ebola",
    title: "Kenya health emergencies weekly situation report",
    location: "Kenya",
    source: "WHO Kenya",
    type: "Situation report",
    status: "Weekly situation report",
    dataThrough: "2026-11-15",
    checkedOn: "2026-11-21",
    reviewBy: "2026-11-28",
    summary:
      "The report covers the Ebola response in Nairobi and updates on mpox and other health events across Kenya for 9–15 November. The weekly reports page provides subsequent updates.",
    url: "https://afro.who.int/sites/default/files/2026-11/Week%2047%20Situation%20Report.pdf",
  },
  {
    id: "who-kenya-ebola-2026-11-11",
    topic: "Ebola",
    title: "Kenya reports the discharge of its last Ebola patient",
    location: "Nairobi, Kenya",
    source: "WHO Regional Office for Africa",
    type: "News release",
    status: "Monitoring period: not yet declared over",
    publishedOn: "2026-11-11",
    checkedOn: "2026-11-21",
    // Kenya can be declared free of this outbreak only after 42 days without a new confirmed case.
    reviewBy: "2026-12-23",
    summary:
      "WHO reported that the last patient was discharged on 11 November, starting a 42-day monitoring period. The outbreak is declared over only if no new case is confirmed in that time. Consult the newer situation reports for the latest status.",
    url: "https://www.afro.who.int/countries/kenya/news/kenyas-last-ebola-patient-goes-home-42-day-countdown-begins",
  },
];

export function healthUpdatesForDate(today) {
  return healthUpdates
    .filter((item) => (item.publishedOn || item.dataThrough) <= today)
    .map((item) => ({ ...item, archived: today >= item.reviewBy }));
}

// General prevention guidance. These are reference fact sheets, not reports of current outbreaks in Kenya.
export const preventionGuidance = [
  {
    id: "cholera",
    topic: "Cholera",
    source: "WHO",
    url: "https://www.who.int/news-room/fact-sheets/detail/cholera",
    summary:
      "How cholera spreads through unsafe water and food, warning signs of dehydration and when to seek care.",
  },
  {
    id: "mpox",
    topic: "Mpox",
    source: "WHO",
    url: "https://www.who.int/news-room/fact-sheets/detail/mpox",
    summary:
      "Symptoms, how mpox spreads through close contact, vaccination for people at higher risk and care at home.",
  },
  {
    id: "covid-19",
    topic: "COVID-19",
    source: "WHO",
    url: "https://www.who.int/news-room/fact-sheets/detail/coronavirus-disease-(covid-19)",
    summary:
      "Symptoms, vaccination and ways to lower the risk of infection, including during pregnancy.",
  },
  {
    id: "ebola",
    topic: "Ebola disease",
    source: "WHO",
    url: "https://www.who.int/news-room/fact-sheets/detail/ebola-disease",
    summary:
      "How Ebola disease spreads, early symptoms and why prompt care at a health facility matters.",
  },
];
