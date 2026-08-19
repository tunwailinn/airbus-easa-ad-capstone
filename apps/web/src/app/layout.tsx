import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Airbus EASA AD Assistant",
  description: "Evidence-grounded aviation maintenance document assistant",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
