import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import { AppShell } from "@/components/app-shell";
import { AuthProvider } from "@/components/auth-provider";
import "./globals.css";
import "leaflet/dist/leaflet.css";

const manrope = Manrope({ subsets: ["latin", "latin-ext"], display: "swap" });

export const metadata: Metadata = {
  title: { default: "Sreality Tracker", template: "%s | Sreality Tracker" },
  description: "Soukromý přehled nabídkových cen chat a chalup.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="cs"><body className={manrope.className}><AuthProvider><AppShell>{children}</AppShell></AuthProvider></body></html>;
}
