// UI policy: simulations always include a positive polling-error component.
// Preserve other imported assumptions while upgrading older fixed-probability scenarios.
export function withPollUncertainty(config){
 const scale=Number(config?.uncertaintyScale??1);
 return {...config,samplingMode:'poll',uncertaintyScale:Number.isFinite(scale)?Math.max(.1,scale):1};
}
