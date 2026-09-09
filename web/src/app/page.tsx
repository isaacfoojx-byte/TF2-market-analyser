import Link from "next/link";
import {latestMarkets,searchMarkets} from "@/lib/market-repository";
import type {Dataset} from "@/lib/types";
const price=(v:number)=>`${v.toLocaleString(undefined,{maximumFractionDigits:2})} keys`;
export default async function Home({searchParams}:{searchParams:Promise<{q?:string;dataset?:string}>}){
 const p=await searchParams,dataset:Dataset=p.dataset==="community"?"community":"unusual",q=p.q?.trim()??"";
 const markets=q?await searchMarkets(dataset,q):await latestMarkets(dataset);
 return <main><section className="hero"><div><p className="eyebrow">MARKET WORKBENCH</p><h1>Find a market.<br/>Read its history.</h1><p>Browse exact Unusual combinations or community variants from the latest validated snapshot.</p></div><aside><i/>Historical archive connected</aside></section>
 <form className="search"><label htmlFor="q">Item or effect</label><div><input id="q" name="q" defaultValue={q} placeholder="Try Team Captain or Burning Flames"/><select name="dataset" defaultValue={dataset}><option value="unusual">Unusual markets</option><option value="community">Community prices</option></select><button>Search</button></div></form>
 <section className="results"><div className="section-title"><div><p className="eyebrow">{q?"SEARCH RESULTS":"LATEST SNAPSHOT"}</p><h2>{q?`Matches for “${q}”`:dataset==="unusual"?"Unusual markets":"Community prices"}</h2></div><span>{markets.length} shown</span></div>
 {markets.length?<div className="list">{markets.map(m=><Link className="row" href={`/markets/${encodeURIComponent(m.stableId)}`} key={m.stableId}><span><strong>{m.itemName}</strong><small>{m.effectName??`${m.quality??"Unknown"}${m.craftable===false?" · Non-craftable":""}`}</small></span><time>{new Date(m.collectedAt).toLocaleDateString()}</time><b>{price(m.priceKeys)}</b><em>↗</em></Link>)}</div>:<div className="empty">No markets matched. Try a shorter item or effect name.</div>}</section></main>;
}
