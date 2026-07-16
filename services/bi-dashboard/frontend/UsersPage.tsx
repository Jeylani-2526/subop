import AppShell from './components/AppShell';

export default function UsersPage() {
  return (
    <AppShell pageTitle="User Management" userRole="admin">
      <div style={{ color: 'var(--color-neutral-dark)', fontSize: '12px' }} />
    </AppShell>
  );
}
