import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "Amazon SEO Copilot - Competitor Keyword Intelligence SaaS",
  description: "Discover keyword gaps, analyze competitor Share of Voice, optimize product listings, and chat with your Amazon data using local AI Copilot.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full bg-bg-deep text-gray-100 antialiased selection:bg-brand-primary selection:text-white">
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
