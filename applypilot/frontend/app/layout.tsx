import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'ApplyPilot AI — Your career copilot', description: 'Discover better-fit jobs and manage every application with your AI career copilot.' };
export default function RootLayout({ children }: Readonly<{children: React.ReactNode}>) { return <html lang="en"><body>{children}</body></html>; }
