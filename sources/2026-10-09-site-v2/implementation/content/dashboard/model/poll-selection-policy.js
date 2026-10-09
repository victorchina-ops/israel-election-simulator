// Keep publisher selection independent of numerical weighting. Site defaults
// explicitly turn Channel 14 OFF; an omitted flag preserves the older core API
// and archived scenario reproducibility. This filter never removes source data.
export function validatePollSelectionPolicy(config={}){
  if(config.includeChannel14!==undefined&&typeof config.includeChannel14!=='boolean')throw new Error('מתג סקרי ערוץ 14 חייב להיות מופעל או כבוי.');
  return config;
}

export function channel14Included(config={}){
  validatePollSelectionPolicy(config);
  return config.includeChannel14!==false;
}

export function isChannel14Poll(poll={}){
  // The current Channel 14 series is NEXT DATA. An explicit publisher channel
  // also supports a future change of institute without leaking its surveys in.
  if(poll.pollsterId==='next_data')return true;
  const channel=poll.publisherChannel??poll.channel;
  if(channel===14)return true;
  if(typeof channel==='string'&&/^(?:14|c14|channel[ _-]?14|ערוץ\s*14|חדשות\s*14)$/i.test(channel.trim()))return true;
  return typeof poll.publisher==='string'&&/^(?:עכשיו\s*14|ערוץ\s*14|חדשות\s*14|channel\s*14)$/i.test(poll.publisher.trim());
}

export function pollAllowedByChannelPolicy(poll,config={}){
  return channel14Included(config)||!isChannel14Poll(poll);
}
