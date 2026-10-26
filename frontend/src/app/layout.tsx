import type { Metadata } from "next";
import "./globals.css";
import { TopBar } from "@/components/TopBar";
import { Navigation } from "@/components/Navigation";

export const metadata: Metadata = {
  title: "VANTA Terminal — Quantitative ML Research Workstation",
  description: "Bloomberg-inspired local research terminal for crypto-futures strategy modeling.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-terminal-bg text-terminal-text font-mono min-h-screen flex flex-col antialiased">
        <TopBar />
        <div className="flex-1 flex overflow-hidden">
          <Navigation />
          <main className="flex-1 overflow-y-auto bg-terminal-bg p-4">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
