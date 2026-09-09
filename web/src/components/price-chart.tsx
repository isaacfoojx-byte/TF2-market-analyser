import type { HistoryPoint } from "@/lib/types";
export function PriceChart({points}:{points:HistoryPoint[]}) {
  if(points.length<2) return <div className="empty">More snapshots are needed for a trend line.</div>;
  const w=900,h=320,p=34,values=points.map(x=>x.priceKeys),min=Math.min(...values),max=Math.max(...values),spread=max-min||Math.max(max*.1,1);
  const coords=points.map((point,i)=>({point,x:p+i/(points.length-1)*(w-p*2),y:h-p-(point.priceKeys-min)/spread*(h-p*2)}));
  const line=coords.map(({x,y},i)=>`${i?"L":"M"} ${x} ${y}`).join(" ");
  return <figure className="chart"><svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={`Price history from ${min.toFixed(2)} to ${max.toFixed(2)} keys`}><defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#f1a43c" stopOpacity=".35"/><stop offset="1" stopColor="#f1a43c" stopOpacity="0"/></linearGradient></defs>{[0,1,2,3].map(i=><line key={i} x1={p} x2={w-p} y1={p+i/3*(h-p*2)} y2={p+i/3*(h-p*2)} className="grid"/>)}<path d={`${line} L ${w-p} ${h-p} L ${p} ${h-p} Z`} fill="url(#fill)"/><path d={line} className="trend"/>{coords.map(({x,y,point})=><circle key={point.collectedAt} cx={x} cy={y} r="3.5"><title>{`${new Date(point.collectedAt).toLocaleDateString()}: ${point.priceKeys.toFixed(2)} keys`}</title></circle>)}</svg><figcaption><span>{new Date(points[0].collectedAt).toLocaleDateString()}</span><span>{new Date(points.at(-1)!.collectedAt).toLocaleDateString()}</span></figcaption></figure>;
}
