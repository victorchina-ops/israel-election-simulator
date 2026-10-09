/**
 * Israeli Knesset allocation, Elections Law §§81–82 (120 seats, 13/400 threshold).
 * Primary law: https://www.gov.il/BlobFolder/guide/knesset-elections-law/he/laws_elections-law-book_electionslaws_knesset25.pdf
 * Worked official calculation: https://www.gov.il/BlobFolder/generalpage/appendixtomemorandum-21/he/elections-seats_zikaron-dvarim.pdf
 *
 * Counts must be nonnegative safe integers. Fractional probabilities must first be
 * sampled into ballot counts. An excluded aggregate still contributes to validVotes.
 * Degenerate synthetic totals with zero quota, no survivors, or initial overallocation
 * are rejected: the statutory integer-quota procedure assumes election-scale counts.
 */
export const KNESSET_SEATS = 120;
export const THRESHOLD_NUMERATOR = 13;
export const THRESHOLD_DENOMINATOR = 400;

const SAFE = Number.MAX_SAFE_INTEGER;

// At national-election magnitudes these products are exact JS integers. BigInt
// preserves exactness for deliberately extreme, but still safe-integer, inputs.
function compareProducts(a, b, c, d) {
  if (a <= SAFE / b && c <= SAFE / d) return Math.sign(a * b - c * d);
  const left = BigInt(a) * BigInt(b);
  const right = BigInt(c) * BigInt(d);
  return left === right ? 0 : left > right ? 1 : -1;
}

function integerDivide(a, b) {
  return a < SAFE / 256 ? Math.floor(a / b) : Number(BigInt(a) / BigInt(b));
}

function drawIndex(size, rng) {
  const u = rng();
  if (!Number.isFinite(u) || u < 0 || u >= 1) {
    throw new RangeError('rng must return a finite number in [0, 1).');
  }
  return Math.floor(u * size);
}

function distributeSurplus(units, target, totalVotes, rng, trace, phase) {
  let allocated = units.reduce((sum, unit) => sum + unit.seats, 0);
  if (allocated > target) {
    throw new RangeError('Integer quota overallocated the synthetic vote total; use election-scale counts.');
  }
  while (allocated < target) {
    let ties = [];
    for (let i = 0; i < units.length; i++) {
      const unit = units[i];
      // §81(d)(4), also for linked lists treated as one unit by §82(a).
      if (unit.seats * 2 >= target && compareProducts(unit.votes, 2, totalVotes, 1) <= 0) continue;
      if (ties.length === 0) {
        ties = [i];
      } else {
        const best = units[ties[0]];
        const order = compareProducts(unit.votes, best.seats + 1, best.votes, unit.seats + 1);
        if (order > 0) ties = [i];
        else if (order === 0) ties.push(i);
      }
    }
    if (!ties.length) throw new RangeError('No list can receive the remaining statutory seats.');
    const chosen = ties.length === 1 ? ties[0] : ties[drawIndex(ties.length, rng)];
    const winner = units[chosen];
    if (trace) trace.push({
      phase,
      type: 'surplus',
      seat: allocated + 1,
      members: [...winner.members],
      quotient: { numerator: winner.votes, denominator: winner.seats + 1 },
      lottery: ties.length > 1 ? ties.map(i => [...units[i].members]) : null,
    });
    winner.seats++;
    allocated++;
  }
}

/**
 * @param {number[]} votes Ballot counts, in party order; includes below-threshold votes.
 * @param {Array<[number,number]>} agreements At most one partner per list.
 * @param {{eligibleMask?: boolean[], rng?: ()=>number, trace?: boolean}} options
 * @returns {{seats:number[],passed:boolean[],validVotes:number,eligibleVotes:number,quota:number,appliedAgreements:Array<[number,number]>,trace?:object[]}}
 */
export function allocateSeats(votes, agreements = [], options = {}) {
  if (!Array.isArray(votes) || votes.length === 0 || Array.from(votes).some(v => !Number.isSafeInteger(v) || v < 0)) {
    throw new TypeError('votes must be a nonempty array of nonnegative safe integer ballot counts.');
  }
  const validVotes = votes.reduce((sum, v) => sum + v, 0);
  if (!Number.isSafeInteger(validVotes) || validVotes <= 0) throw new RangeError('Total valid votes must be a positive safe integer.');
  if (!options || typeof options !== 'object' || Array.isArray(options)) throw new TypeError('options must be an object.');
  const { eligibleMask = votes.map(() => true), rng = Math.random } = options;
  if (!Array.isArray(eligibleMask) || eligibleMask.length !== votes.length || Array.from(eligibleMask).some(v => typeof v !== 'boolean')) {
    throw new TypeError('eligibleMask must contain one boolean per vote entry.');
  }
  if (typeof rng !== 'function') throw new TypeError('rng must be a function.');
  if (!Array.isArray(agreements)) throw new TypeError('agreements must be an array of index pairs.');
  const partners = new Set();
  for (const pair of agreements) {
    if (!Array.isArray(pair) || pair.length !== 2 || pair.some(i => !Number.isInteger(i) || i < 0 || i >= votes.length) || pair[0] === pair[1]) {
      throw new TypeError('Each surplus agreement must contain two different valid party indexes.');
    }
    if (pair.some(i => partners.has(i))) throw new RangeError('A party cannot have more than one surplus agreement.');
    if (pair.some(i => !eligibleMask[i])) throw new RangeError('An excluded aggregate cannot sign a surplus agreement.');
    pair.forEach(i => partners.add(i));
  }
  const passed = votes.map((v, i) => eligibleMask[i] && compareProducts(v, 400, validVotes, 13) >= 0);
  const eligibleVotes = votes.reduce((sum, v, i) => sum + (passed[i] ? v : 0), 0);
  if (eligibleVotes === 0) throw new RangeError('No ballot list passes the statutory threshold.');
  const quota = integerDivide(eligibleVotes, KNESSET_SEATS);
  if (quota === 0) throw new RangeError('Integer allocation quota is zero; use election-scale counts.');
  const seats = votes.map((v, i) => passed[i] ? integerDivide(v, quota) : 0);
  const appliedAgreements = agreements.filter(([a, b]) => passed[a] && passed[b]).map(pair => [...pair]);
  const trace = options.trace ? [{ phase: 'national', type: 'initial', quota, eligibleVotes, seats: [...seats] }] : null;
  const grouped = new Set();
  const units = appliedAgreements.map(members => {
    members.forEach(i => grouped.add(i));
    return { members, votes: members.reduce((sum, i) => sum + votes[i], 0), seats: members.reduce((sum, i) => sum + seats[i], 0) };
  });
  votes.forEach((v, i) => {
    if (passed[i] && !grouped.has(i)) units.push({ members: [i], votes: v, seats: seats[i] });
  });
  distributeSurplus(units, KNESSET_SEATS, eligibleVotes, rng, trace, 'national');

  for (const unit of units) {
    if (unit.members.length === 1) {
      seats[unit.members[0]] = unit.seats;
      continue;
    }
    // §82(b): recalculate the pair's integer quota and initial allocation,
    // rather than assigning each extra seat to a partner greedily as it arrives.
    const pairQuota = integerDivide(unit.votes, unit.seats);
    if (pairQuota === 0) throw new RangeError('Internal pair quota is zero.');
    const inside = unit.members.map(i => ({ members: [i], votes: votes[i], seats: integerDivide(votes[i], pairQuota) }));
    if (trace) trace.push({ phase: 'pair', type: 'initial', members: [...unit.members], quota: pairQuota, target: unit.seats, seats: inside.map(x => x.seats) });
    distributeSurplus(inside, unit.seats, unit.votes, rng, trace, 'pair');
    inside.forEach(x => { seats[x.members[0]] = x.seats; });
  }
  const result = { seats, passed, validVotes, eligibleVotes, quota, appliedAgreements };
  if (trace) result.trace = trace;
  return result;
}
