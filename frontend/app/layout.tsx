import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Dark Factory',
  description: 'Autonomous AI Product Factory Dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="cs">
      <body style={{ margin: 0, fontFamily: 'monospace', background: '#0a0a0a', color: '#e0e0e0' }}>
        {children}
      </body>
    </html>
  )
}
