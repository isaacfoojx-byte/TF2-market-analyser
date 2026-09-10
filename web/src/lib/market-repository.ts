import Database from "better-sqlite3";
import path from "node:path";
import postgres, { Sql } from "postgres";
import type { Dataset, HistoryPoint, MarketDetail, MarketSummary } from "@/lib/types";

type Row = Record<string, unknown>;
const datasets = new Set<Dataset>(["unusual", "community"]);
function validateDataset(value: string): asserts value is Dataset { if (!datasets.has(value as Dataset)) throw new RangeError(`Unsupported dataset: ${value}`); }
const num = (value: unknown) => typeof value === "number" ? value : Number(value);
const summary = (r: Row): MarketSummary => ({ stableId: String(r.stable_id), dataset: String(r.dataset) as Dataset, itemName: String(r.item_name), effectName: r.effect_name == null ? null : String(r.effect_name), quality: r.quality == null ? null : String(r.quality), craftable: r.craftable == null ? null : Boolean(r.craftable), collectedAt: String(r.collected_at), priceKeys: num(r.price_keys), priceRef: num(r.price_ref) });
const point = (r: Row): HistoryPoint => ({ collectedAt: String(r.collected_at), priceKeys: num(r.price_keys), priceRef: num(r.price_ref), keyPriceRef: r.key_price_ref == null ? null : num(r.key_price_ref), sourceUpdatedAt: r.source_updated_at == null ? null : String(r.source_updated_at), qualityFlags: r.quality_flags == null ? null : String(r.quality_flags) });

let local: Database.Database | undefined;
let remote: Sql | undefined;
function sqlite() { const file = process.env.TFANALYTICS_SQLITE_PATH ?? path.resolve(process.cwd(), "..", "database", "market_v2.db"); local ??= new Database(file, { readonly: true, fileMustExist: true }); local.pragma("query_only = ON"); return local; }
function pg() { if (!process.env.DATABASE_URL) throw new Error("DATABASE_URL is not configured"); remote ??= postgres(process.env.DATABASE_URL, { max: 5, idle_timeout: 20, connect_timeout: 10, ssl: "require" }); return remote; }

const latestSql = `SELECT m.stable_id,m.dataset,m.item_name,m.effect_name,m.quality,m.craftable,s.collected_at,o.price_keys,o.price_ref FROM current_prices o JOIN snapshots s USING(snapshot_id) JOIN markets m USING(market_id) WHERE m.dataset=$dataset ORDER BY m.item_name,m.effect_name,m.quality LIMIT $limit`;
export async function latestMarkets(dataset: string, limit=30): Promise<MarketSummary[]> {
  validateDataset(dataset); const safe=Math.min(Math.max(limit,1),100); let rows: Row[];
  if (process.env.DATABASE_URL) rows=await pg().unsafe(latestSql.replace("$dataset","$1").replace("$limit","$2"),[dataset,safe]) as Row[];
  else rows=sqlite().prepare(latestSql.replace("$dataset","?").replace("$limit","?")).all(dataset,safe) as Row[];
  return rows.map(summary);
}
export async function searchMarkets(dataset: string, query: string, limit=30): Promise<MarketSummary[]> {
  validateDataset(dataset); const term=query.trim(); if (!term) return latestMarkets(dataset,limit); const safe=Math.min(Math.max(limit,1),100); const pattern=`%${term}%`;
  const sql=`SELECT m.stable_id,m.dataset,m.item_name,m.effect_name,m.quality,m.craftable,s.collected_at,o.price_keys,o.price_ref FROM markets m JOIN current_prices o USING(market_id) JOIN snapshots s USING(snapshot_id) WHERE m.dataset=$dataset AND (LOWER(m.item_name) LIKE LOWER($pattern) OR LOWER(COALESCE(m.effect_name,'')) LIKE LOWER($pattern)) ORDER BY m.item_name,m.effect_name,m.quality LIMIT $limit`;
  let rows: Row[];
  if (process.env.DATABASE_URL) rows=await pg().unsafe(sql.replaceAll("$dataset","$1").replaceAll("$pattern","$2").replace("$limit","$3"),[dataset,pattern,safe]) as Row[];
  else rows=sqlite().prepare(sql.replace("$dataset","?").replaceAll("$pattern","?").replace("$limit","?")).all(dataset,pattern,pattern,safe) as Row[];
  return rows.map(summary);
}
export async function marketDetail(id: string): Promise<MarketDetail|null> {
  const marketSql="SELECT stable_id,dataset,item_name,effect_name,quality,craftable,first_seen_at,last_seen_at FROM markets WHERE stable_id=$id";
  const historySql="SELECT s.collected_at,o.price_keys,o.price_ref,o.key_price_ref,o.source_updated_at,o.quality_flags FROM markets m JOIN price_observations o USING(market_id) JOIN snapshots s USING(snapshot_id) WHERE m.stable_id=$id ORDER BY s.collected_at";
  let market: Row|undefined; let history: Row[];
  if(process.env.DATABASE_URL){ const [a,b]=await Promise.all([pg().unsafe(marketSql.replace("$id","$1"),[id]),pg().unsafe(historySql.replace("$id","$1"),[id])]); market=a[0] as Row|undefined; history=b as Row[]; }
  else { market=sqlite().prepare(marketSql.replace("$id","?")).get(id) as Row|undefined; history=sqlite().prepare(historySql.replace("$id","?")).all(id) as Row[]; }
  if(!market) return null;
  return { stableId:String(market.stable_id),dataset:String(market.dataset) as Dataset,itemName:String(market.item_name),effectName:market.effect_name==null?null:String(market.effect_name),quality:market.quality==null?null:String(market.quality),craftable:market.craftable==null?null:Boolean(market.craftable),firstSeenAt:String(market.first_seen_at),lastSeenAt:String(market.last_seen_at),history:history.map(point) };
}
