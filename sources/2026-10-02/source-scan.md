# Source scan — 2 October 2026

Checked at 2026-10-02 10:09 UTC (13:09 Israel time). This receipt owns source-scan.json and source-scan.md only; canonical data edits belong to the ingestion owner.

IsraelPolls [profile](https://x.com/IsraelPolls?s=20) and the four original posts were successfully read by direct HTTP. The web reader had a cache miss, but HTTP returned the actual profile and posts. Original graphics and all four historical tables were visually reviewed. New records since the immutable 1 October baseline: Maariv 2 October, i24 1 October, and the incidentally verified C14 1 October. Zman Israel 1 October is already active in that baseline and was corroborated; C13 30 September is also already present. The i24 original footer verifies fieldwork 1 October, 504 adults18+, a digital system combined with a panel, and a declared 4.3% margin at95% confidence.

i24 reports Hendel–Zelekha1.8% precisely. It labels six parties “below1%”: Blue and White, Haredi Public, Black Color, Noam, Israel First and Ahi. These are strict upper bounds. Exact raw percentages remain null. Each graphic/table URL and SHA256 is preserved in source-scan.json; no raw graphic files were saved in this scan.

[N12 homepage](https://www.n12.co.il/), [politics](https://www.mako.co.il/news-politics) and [elections](https://www.mako.co.il/news-israel-elections/2026) were opened directly. All return HTTP200. The latest general national poll is [22 September](https://www.mako.co.il/news-israel-elections/2026/Article-fad59e819c9c0a1027.htm), published21:07 and updated23 September00:56. The index's23 September label is an update date. The [23 September youth poll](https://www.mako.co.il/news-israel-elections/2026/Article-0f9149c460ac0a1026.htm) is a separate Jewish first-time-voter sample age18–22, n301, fieldwork15–22 September; it is excluded from national aggregation.

[C13 homepage](https://13tv.co.il/), [politics overview](https://13tv.co.il/news/politics/), [political-system index](https://13tv.co.il/news/politics/politics/) and [poll index](https://13tv.co.il/tags/survey/) are readable through the web reader with current2 October items. Their latest national poll remains30 September21:05. Direct raw HTTP returns403 for all four URLs; this access limitation is retained separately.

[Kan homepage](https://www.kan.org.il/) and [politics index](https://www.kan.org.il/content/kan-news/politic/) return403; the web reader returns zero lines. They were attempted, but content was unavailable. No conclusion about absence of a new Kan poll follows.

Channel16's actual primary homepage is [ch16.co.il](https://www.ch16.co.il/), linked from the secondary channel index. It returnsHTTP200 with a Next.js application/not-found shell titled ch16israel, and no readable news/politics/poll content or usable index links. The primary content could not be checked. The [secondary index](https://www.skarim.org/channels/channel-16) still lists29 September. The initially tried c16.co.il host is not primary evidence.

A new C14 poll was also found directly on the homepage and verified against its [original article](https://www.c14.co.il/article/1720749): publication1 October21:03, fieldwork1 October, NEXT DATA, n2175 adults, analysis Shlomo Filber. Reported mode and sampling error are missing. Seats sum120; source blocs64/44/12, compared with63/45/12 previously. Full numbers are in the JSON and were passed to the ingestion owner.

X post timezones are unspecified and are not used as fieldwork/publication timestamps. Poll graphics, table replies and primary articles are evidence for the same polls and must not be counted as separate surveys.

