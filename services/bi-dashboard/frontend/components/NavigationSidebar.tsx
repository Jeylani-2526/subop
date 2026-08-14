import { NavLink, useLocation, useNavigate } from "react-router-dom";

interface NavItem {
  label: string;
  path: string;
  adminOnly?: boolean;
}

interface NavigationSidebarProps {
  userRole: "admin" | "data_engineer" | "bi_analyst" | "viewer";
}

const NAV_ITEMS: NavItem[] = [
  { label: "Overview", path: "/" },
  { label: "Pipeline Monitor", path: "/pipelines" },
  { label: "Data Quality", path: "/quality" },
  { label: "Lineage Explorer", path: "/lineage" },
  { label: "Data Catalog", path: "/catalog" },
  { label: "BI Reports", path: "/reports" },
  { label: "Admin", path: "/admin", adminOnly: true },
  { label: "User Management", path: "/admin/users", adminOnly: true },
];

export default function NavigationSidebar({
  userRole,
}: NavigationSidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const isAdmin = userRole === "admin";
  const visibleItems = NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin);

  return (
    <nav
      style={{
        width: "240px",
        minWidth: "240px",
        height: "100vh",
        backgroundColor: "var(--color-primary)",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
        overflow: "hidden",
      }}
    >
      {/* Logo — tıklanınca ana sayfaya gider */}
      <div
        onClick={() => navigate("/")}
        style={{
          padding: "24px 16px",
          borderBottom: "1px solid rgba(255,255,255,0.1)",
          cursor: "pointer",
        }}
      >
        <span
          style={{
            color: "#fff",
            fontWeight: 700,
            fontSize: "16px",
            letterSpacing: "1px",
          }}
        >
          SUBOP
        </span>
      </div>

      {/* Nav Items */}
      <div style={{ flex: 1, padding: "8px 0", overflowY: "auto" }}>
        {visibleItems.map((item) => {
          const isActive =
            item.path === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(item.path);

          return (
            <NavLink
              key={item.path}
              to={item.path}
              style={{
                display: "block",
                padding: "8px 16px",
                color: isActive ? "#fff" : "rgba(255,255,255,0.7)",
                backgroundColor: isActive
                  ? "var(--color-secondary)"
                  : "transparent",
                textDecoration: "none",
                fontSize: "12px",
                fontWeight: isActive ? 600 : 400,
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
