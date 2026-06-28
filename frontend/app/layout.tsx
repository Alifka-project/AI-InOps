import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { KeepAlive } from "@/components/KeepAlive";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Digital Twin — Electrolux UAE Operations",
  description:
    "Supply-chain & warehouse digital twin for sensitive-material resilience under the 2026 Strait of Hormuz crisis.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <KeepAlive />
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
            <Header />
            <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
              {children}
            </main>
            <Footer />
          </div>
        </div>
      </body>
    </html>
  );
}
