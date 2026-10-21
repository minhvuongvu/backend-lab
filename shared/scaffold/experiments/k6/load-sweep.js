// Step the arrival rate up to find the knee: max throughput under the SLO and the throughput-latency curve.
// STEPS="100,200,400,800" STEP_DURATION=60s. Each step is long enough to reach steady state; analyse per step.
import { baseOptions, PRE_VUS, MAX_VUS, WARMUP, RATE, createItem, summaryTo } from './lib.js';

const steps = (__ENV.STEPS || '100,200,400,800').split(',').map((x) => parseInt(x, 10));
const stepDuration = __ENV.STEP_DURATION || '60s';

export const options = Object.assign({}, baseOptions, {
  scenarios: {
    warmup: {
      executor: 'constant-arrival-rate', rate: steps[0] || RATE, timeUnit: '1s', duration: WARMUP,
      preAllocatedVUs: PRE_VUS, maxVUs: MAX_VUS, tags: { phase: 'warmup' },
    },
    sweep: {
      executor: 'ramping-arrival-rate', startRate: steps[0], timeUnit: '1s', startTime: WARMUP,
      preAllocatedVUs: PRE_VUS, maxVUs: MAX_VUS, tags: { phase: 'measure' },
      // hold each step (a 1s ramp to the next rate, then a plateau) so each plateau is a steady-state window
      stages: steps.flatMap((r) => [{ target: r, duration: '1s' }, { target: r, duration: stepDuration }]),
    },
  },
});

export default function () {
  createItem();
}

export const handleSummary = summaryTo(__ENV.SUMMARY_OUT || '/out/summary.json');
