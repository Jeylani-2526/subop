import { NavLink, useLocation } from 'react-router-dom';

interface NavItem {
  label: string;
  path: string;
  adminOnly?: boolean;
}

interface NavigationSidebarProps {
  /** The authenticated user's role — controls visibility of admin-only items */
  userRole: 'admin' | 'data_engineer' | 'bi_analyst' | 'viewer';
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Overview',          path: '/' },
  { label: 'Pipeline Monitor',  path: '/pipelines' },
  { label: 'Data Quality',      path: '/quality' },
  { label: 'Lineage Explorer',  path: '/lineage' },
  { label: 'Data Catalog',      path: '/catalog' },
  { label: 'BI Reports',        path: '/reports' },
  { label: 'Admin',             path: '/admin',        adminOnly: true },
  { label: 'User Management',   path: '/admin/users',  adminOnly: true },
];

/**
 * NavigationSidebar
 *
 * Persistent left sidebar rendered on all authenticated pages.
 * Active state is derived from the current React Router route via useLocation().
 * Admin-only items are not rendered for non-admin roles.
 *
 * @param userRole - Authenticated user role. Controls admin item visibility.
 */
export default function NavigationSidebar({ userRole }: NavigationSidebarProps) {
  const location = useLocation();
  const isAdmin = userRole === 'admin';

  const visibleItems = NAV_ITEMS.filter(item => !item.adminOnly || isAdmin);

  return (
    <nav
      style={{
        width: '240px',
        minHeight: '100vh',
        backgroundColor: 'var(--color-primary)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
      }}
    >
      {/* Logo */}
      <div
        style={{
          padding: '24px 16px',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
        }}
      >
        <span style={{ color: '#fff', fontWeight: 700, fontSize: '16px', letterSpacing: '1px' }}>
          SUBOP
        </span>
      </div>

      {/* Nav items */}
      <div style={{ flex: 1, padding: '8px 0' }}>
        {visibleItems.map(item => {
          const isActive = item.path === '/'
            ? location.pathname === '/'
            : location.pathname.startsWith(item.path);

          return (
            <NavLink
              key={item.path}
              to={item.path}
              style={{
                display: 'block',
                padding: '8px 16px',
                color: isActive ? '#fff' : 'rgba(255,255,255,0.7)',
                backgroundColor: isActive ? 'var(--color-secondary)' : 'transparent',
                textDecoration: 'none',
                fontSize: '12px',
                fontWeight: isActive ? 600 : 400,
                transition: 'background-color 0.15s, color 0.15s',
              }}
              onMouseEnter={e => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--color-secondary)';
                  (e.currentTarget as HTMLElement).style.color = '#fff';
                }
              }}
              onMouseLeave={e => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
                  (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.7)';
                }
              }}
            >
              {item.label}
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}
