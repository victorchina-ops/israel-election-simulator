# To120 as an additional discovery source

Audit date: 9 October 2026, 06:35 UTC. Direct requests to the three pages below returned HTTP 200. Saved HTML, readable text, response metadata and SHA-256 hashes are in this directory. Browser-search cached responses were older: the data page there showed 6 October, while the direct response showed the 8 October package. The methodology page failed in the browsing tool but succeeded by direct HTTP; it was therefore inspected from the saved primary-page response.

## What is available

The [download page](https://twonetwenty.com/data) offers `poll_observations.csv/json`: retained aggregate poll figures, source URLs, publication and fieldwork dates, and sample sizes where retained. These are party-level published observations, not respondent microdata. It separately offers prepared `model_inputs`, membership/audit tables, model settings, forecasts and simulated draws. Reported and derived values must not be confused.

The current package is `/data/k26/2026-10-08-tatika/reader/`. No large CSV was downloaded again during this audit. The [evidence page](https://twonetwenty.com/he/evidence) shows 134 surveys with documented roles and 165 scenarios for 8 October, and includes 14 distinct government `Survey_*.pdf` links in its current initial response. Those counts describe the page's displayed roles, not our admitted post-closure corpus or 14 new surveys.

The [methodology page](https://twonetwenty.com/he/methodology) distinguishes vote percentages from published seats and describes a local-level model. Its own historical-accuracy ratings, institute offsets and turnout adjustment are absent; our optional reliability adjustment and other controls are adaptations, not replication of To120's implementation. Model settings, fitted poll weights and exported forecasts are additional derived model material, not new polling measurements.

The download/evidence pages state that commercial use of To120's model inputs or outputs requires Ariel Danieli's explicit prior consent. This project can use its indexed original-source links as discovery leads and independently read the public poll reports. Credit does not by itself replace the stated consent condition for copying the compiled model inputs/outputs.

## Concrete future update rule

1. Continue the existing required IsraelPolls and direct primary-publisher checks. When percentages or methodology remain missing, inspect To120's evidence page and current poll-observation index for additional source URLs.
2. Follow the linked Central Elections Committee PDF or original publisher report. Save the original bytes, retrieval time and SHA-256; record To120 as the discovery link and the original report as measurement provenance.
3. Match the poll to our existing record by institute, publisher, publication date, verified fieldwork window and seat vector, plus the original PDF hash where available. Multiple party rows or scenario rows from one survey do not become multiple independent surveys. A repost date is not a survey date.
4. Extract and retain the original percentages and exact denominator wording. Admit normalized percentages to `data/signal-noise-observations.json` only when the denominator is documented and compatible. Label a justified inferred denominator explicitly. A missing percentage remains absent; a below-threshold statement is a bound unless a numeric percentage is reported. Published mandates are never a source vote percentage.
5. Use the actual achieved sample size and verified fieldwork dates. Record conflicting aggregator metadata; do not silently overwrite canonical values. Admit no future or pre-closure observation. Preserve the older coverage when no compatible report is found.
6. Do not import To120's prepared model inputs, Q/R calibration, weights, probabilities or simulated outcomes as if they were raw source polls. Keep the implementation and fit independent, retain credit to אריאל דניאלי / עד120, and preserve its experimental and short-series limitations.

This audit made no changes to canonical polling records or reviewed signal/noise observations and did not conclude that there were no newly published polls.
