// Seeded PRNG and exact aggregate ballot samplers. No per-person allocation loop.
export function seededRandom(seed = 120) {
  let a = Number(seed) >>> 0;
  return () => { a += 0x6D2B79F5; let t=a; t=Math.imul(t ^ t>>>15,t|1); t^=t+Math.imul(t ^ t>>>7,t|61); return ((t ^ t>>>14)>>>0)/4294967296; };
}
export function normal(rng) {
  let u=0; while(!u) u=rng();
  return Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*rng());
}
export function gamma(shape,rng) {
  if(shape<1) return gamma(shape+1,rng)*Math.pow(Math.max(rng(),Number.MIN_VALUE),1/shape);
  const d=shape-1/3,c=1/Math.sqrt(9*d);
  for(;;){const x=normal(rng),t=1+c*x;if(t<=0)continue;const v=t*t*t,u=rng();if(u<1-.0331*x*x*x*x || Math.log(u)<.5*x*x+d*(1-v+Math.log(v)))return d*v;}
}
export function beta(a,b,rng){const x=gamma(a,rng),y=gamma(b,rng);return x/(x+y);}
export function binomial(n,p,rng){
  if(!Number.isSafeInteger(n)||n<0||!Number.isFinite(p)||p<0||p>1)throw new Error("Invalid binomial parameters");
  if(!n||p===0)return 0;if(p===1)return n;
  if(p>.5)return n-binomial(n,1-p,rng);
  let k=0;
  // Exact beta/order-statistic splitting, then inverse CDF for small means.
  while(n*p>16 && n>64){
    const a=1+Math.floor(n/2),b=n-a+1,x=beta(a,b,rng);
    if(x>=p){n=a-1;p/=x;}else{k+=a;n=b-1;p=(p-x)/(1-x);}
    p=Math.max(0,Math.min(1,p));
    // A beta split can move the conditional probability above one half.
    // Reflect again before inversion: (1-p)^n could otherwise underflow.
    if(p>.5)return k+n-binomial(n,1-p,rng);
  }
  if(p===1)return k+n;
  const q=1-p;let mass=Math.exp(n*Math.log1p(-p)),u=rng(),j=0;
  while(u>mass&&j<n){u-=mass;j++;mass*=((n-j+1)/j)*(p/q);if(mass===0)throw new Error("Binomial inversion underflow: "+JSON.stringify({n,p,j,u,mass}));}
  return k+j;
}
export function multinomial(n,probabilities,rng){
  const out=new Array(probabilities.length).fill(0);let left=n,remaining=probabilities.reduce((a,b)=>a+b,0);
  for(let j=0;j<out.length-1;j++){const q=remaining>0?Math.max(0,Math.min(1,probabilities[j]/remaining)):0;out[j]=binomial(left,q,rng);left-=out[j];remaining-=probabilities[j];}
  out[out.length-1]=left;return out;
}
export function normalise(values){const s=values.reduce((a,b)=>a+b,0);if(!(s>0))throw new Error("Empty probability vector");return values.map(v=>v/s);}
export function quantileHistogram(hist,q){const n=hist.reduce((a,b)=>a+b,0);if(!n)return null;const target=Math.max(1,Math.ceil(q*n));let s=0;for(let i=0;i<hist.length;i++){s+=hist[i];if(s>=target)return i;}return hist.length-1;}
export function wilson(success,n,z=1.95996398454){if(!n)return [0,1];const p=success/n,d=1+z*z/n,c=(p+z*z/(2*n))/d,h=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return [Math.max(0,c-h),Math.min(1,c+h)];}
