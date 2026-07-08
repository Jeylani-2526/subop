import { ReactNode } from 'react';
import NavigationSidebar from './NavigationSidebar';

interface AppShellProps {
  children: ReactNode;
  userRole: 'admin' | 'data_engineer' | 'bi_analyst' | 'viewer';
  pageTitle: string;
}

export default function AppShell({ children, userRole, pageTitle }: AppShellProps) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>

      {/* Sidebar */}
      <NavigationSidebar userRole={userRole} />

      {/* Right side */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>

        {/* Header */}
        <header
          style={{
            height: '56px',
            backgroundColor: 'var(--color-primary)',
            display: 'flex',
            alignItems: 'center',
            padding: '0 24px',
            justifyContent: 'space-between',
            flexShrink: 0,
          }}
        >
          <span style={{ color: '#fff', fontSize: '15px', fontWeight: 600 }}>
            {pageTitle}
          </span>
          <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: '12px' }}>
            SUBOP
          </span>
        </header>

        {/* Main content */}
        <main
          style={{
            flex: 1,
            backgroundColor: 'var(--color-background)',
            padding: '16px 24px',
          }}
        >
          {children}
        </main>

      </div>
    </div>
  );
}
