// V2 site policy. Archived signal/noise reproducers retain their original engine.
export function retiredSignalNoiseRequested(config={}) {
  return config.signalNoiseEnabled===true||config.weightMode==='signal_noise';
}
export function normalizeSiteScenario(config) {
  if(config.signalNoiseEnabled!==undefined&&typeof config.signalNoiseEnabled!=='boolean')throw new TypeError('signalNoiseEnabled must be boolean');
  return {...config,signalNoiseEnabled:false,weightMode:config.weightMode==='signal_noise'?(config.signalNoiseHistoricalQuality===false?'equal':'quality'):config.weightMode};
}
