import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CloudCommander Control Plane",
  description: "Blast-radius graph and control-plane telemetry"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
