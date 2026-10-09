import {combinePolls} from './reconstruct.js';
import {createSignalNoiseCombination} from './signal-noise.js';

export function isSignalNoiseEnabled(config={}){
  return config.signalNoiseEnabled===true||config.weightMode==='signal_noise';
}
export function resolveForecastConfig(config={}){
  if(config.signalNoiseEnabled!==undefined&&typeof config.signalNoiseEnabled!=='boolean')throw new Error('מתג אות ורעש חייב להיות מופעל או כבוי.');
  if(config.weightMode!=='signal_noise')return config;
  return {...config,weightMode:config.signalNoiseHistoricalQuality===false?'equal':'quality',signalNoiseEnabled:true};
}

// The switch changes support estimation, while the chosen policy supplies
// relative institute reliability. A posterior is never an extra ensemble poll.
export function combineForecast(input, config, calibration = {}) {
  const effective=resolveForecastConfig(config);
  const sourceCalibration = {...(input.calibration || {}), ...calibration,
    weightPresets: input.weightPresets};
  const policy=combinePolls(input.current.polls,input.parties,effective,sourceCalibration);
  return isSignalNoiseEnabled(effective)
    ? createSignalNoiseCombination(input,effective,sourceCalibration,policy)
    : policy;
}
