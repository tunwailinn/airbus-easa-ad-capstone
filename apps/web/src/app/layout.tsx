import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Airbus EASA AD Assistant | Regulatory Intelligence Workspace",
  description: "Evidence-grounded Airbus Airworthiness Directive research and decision support.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
