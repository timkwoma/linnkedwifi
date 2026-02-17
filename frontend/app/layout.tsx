import type { Metadata } from "next";
import { Manrope, Space_Grotesk } from "next/font/google";
import "./globals.css";

const space = Space_Grotesk({ subsets: ["latin"], variable: "--font-space" });
const manrope = Manrope({ subsets: ["latin"], variable: "--font-manrope" });

export const metadata: Metadata = {
  title: "LINKEDWIFI SaaS",
  description: "Multi-tenant hotspot and home router SaaS platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${space.variable} ${manrope.variable} font-body text-ink`}>{children}</body>
    </html>
  );
}

