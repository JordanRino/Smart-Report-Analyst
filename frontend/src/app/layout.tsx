import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { CopilotKit } from "@copilotkit/react-core";
import { AppProvider } from "@/context/AppContext";
import "@copilotkit/react-ui/styles.css"; // Essential for the chat UI
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Smart Report Analyst",
  description: "Interactive data analysis and reporting with AI-powered SQL generation and visualization.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="h-full bg-zinc-50">
        <AppProvider>
          {/* Replace URL with your FastAPI backend address later */}
          <CopilotKit runtimeUrl="http://localhost:8000/api/copilotkit">
            {children}
          </CopilotKit>
        </AppProvider>
      </body>
    </html>
  );
}