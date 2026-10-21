// Long run at a moderate rate: leaks, table/index bloat, GC drift, connection churn show up only over time.
import { baseOptions, warmupAndMeasure, RATE, PRE_VUS, MAX_VUS, createItem, summaryTo } from './lib.js';

export const options = Object.assign({}, baseOptions, {
  scenarios: warmupAndMeasure({
    executor: 'constant-arrival-rate', rate: RATE, timeUnit: '1s', duration: __ENV.SOAK_DURATION || '60m',
    preAllocatedVUs: PRE_VUS, maxVUs: MAX_VUS,
  }),
});

export default function () {
  createItem();
}

export const handleSummary = summaryTo(__ENV.SUMMARY_OUT || '/out/summary.json');
