// Shared helpers for every scenario. Open workload model only (arrival-rate executors), so a slow
// system does not slow down the load generator (no coordinated omission).
import http from 'k6/http';
import { check } from 'k6';
import { randomBytes } from 'k6/crypto';

export const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
export const TESTID = __ENV.TESTID || 'adhoc';          // <impl>-<scenario>-<run>, also passed as --tag testid
export const WARMUP = __ENV.WARMUP || '60s';
export const DURATION = __ENV.DURATION || '120s';
export const RATE = parseInt(__ENV.RATE || '200', 10);   // requests per second
export const PRE_VUS = parseInt(__ENV.PRE_VUS || '50', 10);
export const MAX_VUS = parseInt(__ENV.MAX_VUS || '500', 10);

// Measure, don't gate: no thresholds by default. dropped_iterations > 0 means the generator could not keep
// the arrival rate (raise MAX_VUS or the run is invalid, see 04-experiment-plan.html §7).
export const baseOptions = {
  discardResponseBodies: true,
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'p(99.9)', 'max'],
};

// Warmup and measurement are separate scenarios; analysis drops the warmup with stats.py --skip-seconds
// or by filtering on the `scenario` tag.
export function warmupAndMeasure(measureExecutor) {
  return {
    warmup: {
      executor: 'constant-arrival-rate', rate: RATE, timeUnit: '1s', duration: WARMUP,
      preAllocatedVUs: PRE_VUS, maxVUs: MAX_VUS, exec: 'default', tags: { phase: 'warmup' },
    },
    measure: Object.assign({ startTime: WARMUP, exec: 'default', tags: { phase: 'measure' } }, measureExecutor),
  };
}

// uuid v4 from k6's crypto; ids are generated client-side so the integrity checker can match them.
export function uuid() {
  const b = new Uint8Array(randomBytes(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = [...b].map((x) => x.toString(16).padStart(2, '0')).join('');
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

// Example request: REPLACE with the topic's contract call. The payload carries the testid so the
// integrity checker can select exactly the rows written by this run.
export function createItem() {
  const res = http.post(`${BASE_URL}/items`, JSON.stringify({ id: uuid(), payload: `${TESTID}:x` }), {
    headers: { 'Content-Type': 'application/json' },
    tags: { name: 'POST /items' },
  });
  check(res, { 'status is 201': (r) => r.status === 201 });
  return res;
}

export function summaryTo(path) {
  return (data) => ({ [path]: JSON.stringify(data, null, 2) });
}
