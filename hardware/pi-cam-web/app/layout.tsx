import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AstroFarm — Martian Greenhouse AI Agent",
  description: "Autonomous greenhouse control for Mars mission · Syngenta x AWS START HACK 2026",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className="h-full antialiased">
      <body suppressHydrationWarning className="min-h-full flex flex-col">
        {children}
      </body>
    </html>
  );
}
