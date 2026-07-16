import AppShell from './components/AppShell';

export default function AdminPage() {
  return (
    <AppShell pageTitle="Admin Panel" userRole="admin">
      <div style={{ color: 'var(--color-neutral-dark)', fontSize: '12px' }} />
    </AppShell>
  );
}
