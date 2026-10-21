// Fixed arrival rate: the default scenario for comparing before vs implementations at one load level.
import { baseOptions, warmupAndMeasure, RATE, DURATION, PRE_VUS, MAX_VUS, createItem, summaryTo } from './lib.js';

export const options = Object.assign({}, baseOptions, {
  scenarios: warmupAndMeasure({
    executor: 'constant-arrival-rate', rate: RATE, timeUnit: '1s', duration: DURATION,
    preAllocatedVUs: PRE_VUS, maxVUs: MAX_VUS,
  }),
});

export default function () {
  createItem();
}

export const handleSummary = summaryTo(__ENV.SUMMARY_OUT || '/out/summary.json');
