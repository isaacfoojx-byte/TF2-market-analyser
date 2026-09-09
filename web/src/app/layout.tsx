import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
export const metadata: Metadata={title:{default:"TFAnalytics",template:"%s · TFAnalytics"},description:"Explore current and historical Team Fortress 2 guide prices."};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body><header><Link href="/" className="brand"><b>TF</b> TFAnalytics</Link><span>Daily market snapshots</span></header>{children}</body></html>}
