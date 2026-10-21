// Sudden burst on top of a base load: how fast latency degrades and recovers (queueing, pool exhaustion).
import { baseOptions, PRE_VUS, MAX_VUS, WARMUP, RATE, createItem, summaryTo } from './lib.js';

const spikeRate = parseInt(__ENV.SPIKE_RATE || String(RATE * 5), 10);

export const options = Object.assign({}, baseOptions, {
  scenarios: {
    spike: {
      executor: 'ramping-arrival-rate', startRate: RATE, timeUnit: '1s',
      preAllocatedVUs: PRE_VUS, maxVUs: MAX_VUS, tags: { phase: 'measure' },
      stages: [
        { target: RATE, duration: WARMUP },          // base load (also warmup)
        { target: spikeRate, duration: '5s' },       // spike up
        { target: spikeRate, duration: __ENV.SPIKE_HOLD || '30s' },
        { target: RATE, duration: '5s' },            // back down
        { target: RATE, duration: __ENV.RECOVERY || '90s' }, // observe recovery
      ],
    },
  },
});

export default function () {
  createItem();
}

export const handleSummary = summaryTo(__ENV.SUMMARY_OUT || '/out/summary.json');
