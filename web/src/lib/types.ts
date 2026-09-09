export type Dataset = "unusual" | "community";
export type MarketSummary = { stableId: string; dataset: Dataset; itemName: string; effectName: string | null; quality: string | null; craftable: boolean | null; collectedAt: string; priceKeys: number; priceRef: number };
export type HistoryPoint = { collectedAt: string; priceKeys: number; priceRef: number; keyPriceRef: number | null; sourceUpdatedAt: string | null; qualityFlags: string | null };
export type MarketDetail = { stableId: string; dataset: Dataset; itemName: string; effectName: string | null; quality: string | null; craftable: boolean | null; firstSeenAt: string; lastSeenAt: string; history: HistoryPoint[] };
