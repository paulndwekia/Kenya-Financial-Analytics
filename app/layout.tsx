import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kenya Financial Analytics | Market Research Terminal",
  description: "A Kenyan quantitative-finance workspace for CBK market data, Treasury bills, yield curves, bond valuation, portfolio analysis and risk research.",
  applicationName: "Kenya Financial Analytics",
  metadataBase: new URL("https://kenya-financial-analytics-terminal.vercel.app"),
  openGraph: { title: "Kenya Financial Analytics", description: "Kenyan markets, quantitative research and financial risk analysis.", type: "website" },
  robots: { index: true, follow: true }
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}