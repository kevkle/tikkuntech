import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TikkunTech",
  description: "Think before you post",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
