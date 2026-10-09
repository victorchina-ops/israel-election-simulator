/**
 * Geographic ballot-channel response model; not a demographic population model.
 * Source input: data/turnout-2022.json (CEC national/locality counts + CBS labels).
 * Historical profiles describe WHERE each 2022 party's ballots were counted.
 * Applying a profile to current support is an explicit stability/mapping assumption.
 * The external-envelope channel adds ballots once and adds NO eligible population.
 */
export const TURNOUT_MODEL_VERSION = 'geographic-response-2022-v1';

export const DEFAULT_TURNOUT_MAPPINGS = Object.freeze({
  likud: Object.freeze(['מחל']),
  yisrael_beiteinu: Object.freeze(['ל']),
  utj: Object.freeze(['ג']),
  shas: Object.freeze(['שס']),
  raam: Object.freeze(['עם']),
  democrats: Object.freeze(['אמת', 'מרצ']),
  joint: Object.freeze(['ום', 'ד']),
});

const sum = xs => xs.reduce((a, b) => a + b, 0);
const own = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);
const record = x => x !== null && typeof x === 'object' && !Array.isArray(x);
const EXTERNAL = 'external_envelopes';

function nonnegative(value, name) {
  if (!Number.isFinite(value) || value < 0) throw new RangeError(`${name} must be finite and nonnegative.`);
  return value;
}

function validateSource(data) {
  if (!data || !Array.isArray(data.groups) || !data.national) throw new TypeError('Invalid geographic turnout source.');
  const ids = new Set();
  for (const g of data.groups) {
    if (!g.id || ids.has(g.id)) throw new TypeError('Geographic channel IDs must be unique.');
    ids.add(g.id);
    for (const field of ['eligible', 'voters', 'valid', 'invalid']) {
      if (!Number.isSafeInteger(g[field]) || g[field] < 0) throw new RangeError(`Invalid ${g.id}.${field}.`);
    }
    if (g.valid + g.invalid !== g.voters) throw new RangeError(`Ballot totals do not reconcile in ${g.id}.`);
    if (!record(g.partyVotes2022ByBallot) || Object.values(g.partyVotes2022ByBallot).some(v => !Number.isSafeInteger(v) || v < 0) || sum(Object.values(g.partyVotes2022ByBallot)) !== g.valid) {
      throw new RangeError(`Party ballots do not reconcile in ${g.id}.`);
    }
    if (g.id === EXTERNAL) {
      if (g.eligible !== 0) throw new RangeError('External envelopes must not add a second eligible population.');
    } else if (g.eligible <= 0 || g.voters > g.eligible || g.voters <= 0) {
      throw new RangeError(`Invalid registry-based baseline for ${g.id}.`);
    }
  }
  if (!ids.has(EXTERNAL)) throw new TypeError('The external-envelope ballot channel must be explicit.');
  for (const field of ['eligible', 'voters', 'valid', 'invalid']) {
    if (!Number.isSafeInteger(data.national[field]) || data.national[field] < 0 || sum(data.groups.map(g => g[field])) !== data.national[field]) {
      throw new RangeError(`National ${field} does not reconcile with disjoint geographic channels.`);
    }
  }
  if (data.national.eligible <= 0 || data.national.valid <= 0 || data.national.voters > data.national.eligible) throw new RangeError('Invalid national turnout baseline.');
}

/** Reset configuration. Percentages refer to recorded locality ballots / registry,
 * excluding voters recorded in the separate external-envelope channel. */
export function baselineTurnoutConfig(data, parties = []) {
  return {
    turnout: Object.fromEntries(data.groups.filter(g => g.id !== EXTERNAL).map(g => [g.id, g.voters / g.eligible * 100])),
    externalMultiplier: 1,
    blocMultipliers: { a: 1, b: 1, arab: 1, other: 1 },
    partyBlocs: Object.fromEntries(parties.map(p => [p.id, p.defaultBloc ?? 'other'])),
    turnoutMappings: {},
  };
}

/**
 * config.turnout = { groupId: percentage }, defaults to source recorded rates.
 * config.externalMultiplier defaults to 1 (a channel factor, never a turnout rate).
 * config.blocMultipliers = { blocId: relative motivation }, all default to 1.
 * config.partyBlocs = { partyId: blocId }, defaults to each party.defaultBloc.
 * config.turnoutMappings = { partyId: ['2022 ballot', ...] | {ballot: weight} | null }.
 * Arrays pool historical ballots (not equal party weights); object coefficients
 * multiply source ballot counts before pooling. null/[] explicitly use fallback.
 * config.fallbackExposure optionally sets {groupId: weight} for unresolved parties;
 * otherwise the national distribution of 2022 valid ballots is the neutral proxy.
 */
export function createTurnoutModel(data, parties, config = {}) {
  validateSource(data);
  if (!Array.isArray(parties) || parties.length === 0 || new Set(parties.map(p => p.id)).size !== parties.length || parties.some(p => !p.id)) {
    throw new TypeError('parties must have unique nonempty IDs.');
  }
  if (!record(config)) throw new TypeError('Turnout config must be an object.');
  for (const field of ['turnout', 'blocMultipliers', 'partyBlocs', 'turnoutMappings']) {
    if (config[field] !== undefined && !record(config[field])) throw new TypeError(`${field} must be an object.`);
  }
  const groupIds = data.groups.map(g => g.id);
  const baselineRates = baselineTurnoutConfig(data).turnout;
  for (const id of Object.keys(config.turnout ?? {})) if (!own(baselineRates, id)) throw new RangeError(`Unknown geographic turnout group: ${id}.`);
  const rates = { ...baselineRates, ...(config.turnout ?? {}) };
  for (const [id, pct] of Object.entries(rates)) {
    nonnegative(pct, id);
    if (pct > 100) throw new RangeError(`${id} turnout percentage cannot exceed 100.`);
  }
  const externalMultiplier = nonnegative(config.externalMultiplier ?? 1, 'externalMultiplier');
  const channelRatios = data.groups.map(g => g.id === EXTERNAL ? externalMultiplier : rates[g.id] === baselineRates[g.id] ? 1 : rates[g.id] / baselineRates[g.id]);
  const geographyUnchanged = channelRatios.every(r => r === 1);
  const baselineTurnoutRate = data.national.voters / data.national.eligible;
  const projectedChannelVoters = data.groups.map((g, i) => g.voters * channelRatios[i]);
  const geographicTurnoutRate = geographyUnchanged ? baselineTurnoutRate : sum(projectedChannelVoters) / data.national.eligible;
  if (geographicTurnoutRate > 1) throw new RangeError('Geographic turnout plus external ballots exceeds the single national registry; this scenario is infeasible.');

  let fallback = data.groups.map(g => g.valid / data.national.valid);
  if (config.fallbackExposure !== undefined) {
    if (!record(config.fallbackExposure) || Object.keys(config.fallbackExposure).some(id => !groupIds.includes(id))) throw new TypeError('fallbackExposure must use known geographic channel IDs.');
    fallback = groupIds.map(id => nonnegative(config.fallbackExposure[id] ?? 0, `fallbackExposure.${id}`));
    const total = sum(fallback);
    if (total <= 0) throw new RangeError('fallbackExposure requires positive total weight.');
    fallback = fallback.map(v => v / total);
  }
  const nationalByBallot = {};
  for (const g of data.groups) for (const [ballot, count] of Object.entries(g.partyVotes2022ByBallot)) nationalByBallot[ballot] = (nationalByBallot[ballot] ?? 0) + count;
  const exposures = parties.map(p => {
    const userSpecified = own(config.turnoutMappings ?? {}, p.id);
    const mapping = userSpecified ? config.turnoutMappings[p.id] : DEFAULT_TURNOUT_MAPPINGS[p.id];
    let weights = {};
    if (Array.isArray(mapping)) {
      for (const ballot of mapping) {
        if (typeof ballot !== 'string' || own(weights, ballot)) throw new TypeError(`Invalid or duplicate historical ballot mapping for ${p.id}.`);
        weights[ballot] = 1;
      }
    } else if (mapping !== undefined && mapping !== null) {
      if (!record(mapping)) throw new TypeError(`Invalid turnout mapping for ${p.id}.`);
      weights = { ...mapping };
    }
    for (const [ballot, weight] of Object.entries(weights)) {
      nonnegative(weight, `mapping.${p.id}.${ballot}`);
      if (!own(nationalByBallot, ballot)) throw new RangeError(`Unknown 2022 ballot ${ballot} in mapping for ${p.id}.`);
    }
    const historicalTotal = sum(Object.entries(weights).map(([ballot, weight]) => weight * nationalByBallot[ballot]));
    if (!Number.isFinite(historicalTotal)) throw new RangeError(`Mapping coefficients are too large for ${p.id}.`);
    const unresolved = historicalTotal <= 0;
    const profile = unresolved ? [...fallback] : data.groups.map(g => sum(Object.entries(weights).map(([ballot, weight]) => weight * (g.partyVotes2022ByBallot[ballot] ?? 0))) / historicalTotal);
    const merged = Object.values(weights).filter(v => v > 0).length > 1;
    const mappingStatus = unresolved ? 'unresolved-national-proxy' : userSpecified ? 'user-assumed-mapping' : merged ? 'assumed-merged-profile' : 'assumed-profile-stability';
    const note = unresolved
      ? `${p.name ?? p.id}: אין זיהוי היסטורי מספק; מופעל פרופיל ${config.fallbackExposure ? 'חלופי שבחר המשתמש' : 'הפיזור הארצי של פתקי 2022'}. אין כאן אומדן למעבר מצביעים.`
      : `${p.name ?? p.id}: פרופיל פתקי 2022 (${Object.keys(weights).join(' + ')}) מועבר לתמיכה הנוכחית כהנחת תרחיש${merged ? '; המיזוג משוקלל לפי מספר הקולות ההיסטורי' : ''}.`;
    return { partyId: p.id, profile, byGroup: Object.fromEntries(groupIds.map((id, i) => [id, profile[i]])), mapping: weights, mappingStatus, unresolved, historicalTotal, note };
  });
  const geographicFactors = exposures.map(e => geographyUnchanged ? 1 : sum(e.profile.map((weight, i) => weight * channelRatios[i])));
  const motivationFactors = parties.map(p => nonnegative(config.blocMultipliers?.[config.partyBlocs?.[p.id] ?? p.defaultBloc ?? 'other'] ?? 1, `bloc motivation for ${p.id}`));
  const noMotivationChange = motivationFactors.every(v => v === 1);
  const factors = geographicFactors.map((g, i) => g * motivationFactors[i]);
  const notes = [
    'זהו מודל תגובה לשינוי בהשתתפות לפי ערוץ ספירת קולות גאוגרפי, המבוסס על 2022. הוא אינו מודל אוכלוסייה דמוגרפי או מדידה של הרכב מצביעי 2026.',
    'מחווני היישובים פועלים יחסית לבסיס הסקר: בברירות המחדל תמיכת כל מפלגה נשארת בדיוק כפי שנכנסה. אין להחיל שוב תיקון השתתפות שכבר הוחל על נתוני הקלט.',
    'שלוש הערים אינן כלל הציבור החרדי; יתר היישובים כוללים ערים מעורבות וחרדים מחוץ לשלוש הערים. אין להציג את הקבוצות כמגזרים אישיים.',
    'מעטפות חיצוניות הן ערוץ פתקים ללא מכנה זכאים נוסף. תושביהן כבר כלולים בפנקס; אי אפשר לשייך את הפתקים חזרה למגזר מתוך קובץ היישובים.',
    'נפח המצביעים מעוגן במספרי הפתקים ובפנקס 2022, תוך הנחת יציבות של משקל היישובים; מוטיבציית גוש היא מכפיל יחסי לפי תמיכת התרחיש, ואינה אחוז השתתפות שנמדד.',
    'נפח ההצבעה הגאוגרפי נשען על חלוקת המצביעים ההיסטורית, וחלוקת התמיכה נשענת על פרופילי המפלגות. זו הנחת תגובה בשני חלקים, ולא טבלת מגזר × מפלגה מזוהה לשנת 2026.',
    ...exposures.map(e => e.note),
  ];

  function adjust(probabilities) {
    if (!Array.isArray(probabilities) || probabilities.length !== parties.length || Array.from(probabilities).some(p => !Number.isFinite(p) || p < 0)) throw new TypeError('One finite nonnegative probability per party is required.');
    const total = sum(probabilities);
    if (Math.abs(total - 1) > 1e-8) throw new RangeError('Input probabilities must sum to one.');
    const geographicMass = sum(probabilities.map((p, i) => p * geographicFactors[i]));
    const motivatedMass = sum(probabilities.map((p, i) => p * factors[i]));
    if (!(geographicMass > 0 && motivatedMass > 0 && geographicTurnoutRate > 0)) throw new RangeError('The scenario leaves no positive voting mass.');
    const motivationVolumeRatio = noMotivationChange ? 1 : motivatedMass / geographicMass;
    const turnoutRate = geographicTurnoutRate * motivationVolumeRatio;
    if (!Number.isFinite(turnoutRate) || turnoutRate > 1) throw new RangeError('Turnout exceeds 100% of the single registry; reduce participation or motivation multipliers.');
    // Exact baseline/uniform identity, including structural zero-support parties.
    const uniformFactors = factors.every(f => f === factors[0]);
    const adjusted = uniformFactors ? [...probabilities] : probabilities.map((p, i) => p === 0 ? 0 : p * factors[i] / motivatedMass);
    return {
      probabilities: adjusted,
      turnoutRate,
      factors: [...factors],
      geographicFactors: [...geographicFactors],
      motivationVolumeRatio,
      unresolvedParties: exposures.filter(e => e.unresolved).map(e => e.partyId),
      zeroSupportParties: parties.filter((_, i) => probabilities[i] === 0).map(p => p.id),
    };
  }
  return {
    adjust, exposures, notes, baselineRates, factors: [...factors], geographicFactors: [...geographicFactors],
    groupIds, channelRatios, baselineTurnoutRate, geographicTurnoutRate,
    projectedChannelVoters: Object.fromEntries(groupIds.map((id, i) => [id, projectedChannelVoters[i]])),
    modelVersion: TURNOUT_MODEL_VERSION,
    sources: [...(data.sourceUrls ?? [])],
    assumptions: { responseModel: true, individualDemographicsIdentified: false, currentProfilesObserved: false, externalEligibleAdded: 0, historicalYear: data.year, fallbackExposure: [...fallback] },
  };
}
