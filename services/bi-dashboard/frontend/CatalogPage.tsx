import AppShell from './components/AppShell';

export default function CatalogPage() {
  return (
    <AppShell pageTitle="Data Catalog" userRole="admin">
      <div style={{ color: 'var(--color-neutral-dark)', fontSize: '12px' }} />
    </AppShell>
  );
}
