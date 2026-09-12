import "./globals.css";
import type { Metadata } from "next";
export const metadata: Metadata = {
  title: "RamanPlay",
  description: "RamanPlay — All Your Games. One Place.",
  icons: { icon: "/favicon.svg" },
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
