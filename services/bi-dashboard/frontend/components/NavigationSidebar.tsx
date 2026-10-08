import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useT } from "../src/i18n/LanguageProvider";
import { TranslationKey } from "../src/i18n/tr";

interface NavItem {
  labelKey: TranslationKey;
  path: string;
  adminOnly?: boolean;
  icon: string;
}

interface NavigationSidebarProps {
  userRole: "admin" | "data_engineer" | "bi_analyst" | "viewer";
}

const NAV_ITEMS: NavItem[] = [
  { labelKey: "nav_overview", path: "/", icon: "⊞" },
  { labelKey: "nav_pipeline_monitor", path: "/pipelines", icon: "⟳" },
  { labelKey: "nav_data_quality", path: "/quality", icon: "✦" },
  { labelKey: "nav_lineage_explorer", path: "/lineage", icon: "⤢" },
  { labelKey: "nav_data_catalog", path: "/catalog", icon: "☰" },
  { labelKey: "nav_bi_reports", path: "/reports", icon: "▦" },
  { labelKey: "nav_cdc", path: "/cdc", icon: "◎" },
  { labelKey: "nav_admin", path: "/admin", adminOnly: true, icon: "⚙" },
  {
    labelKey: "nav_user_management",
    path: "/admin/users",
    adminOnly: true,
    icon: "⊙",
  },
];

export default function NavigationSidebar({
  userRole,
}: NavigationSidebarProps) {
  const { t } = useT();
  const location = useLocation();
  const navigate = useNavigate();
  const isAdmin = userRole === "admin";
  const visibleItems = NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin);

  return (
    <nav
      className="subop-sidebar"
      style={{
        height: "100vh",
        backgroundColor: "var(--color-primary)",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
        overflow: "hidden",
      }}
    >
      {/* Logo */}
      <div
        onClick={() => navigate("/")}
        style={{
          padding: "20px 16px",
          borderBottom: "1px solid rgba(255,255,255,0.1)",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: "10px",
          minHeight: "64px",
        }}
      >
        <span style={{ fontSize: "18px", flexShrink: 0 }}>◈</span>
        <span
          className="nav-logo-text"
          style={{
            color: "#fff",
            fontWeight: 700,
            fontSize: "16px",
            letterSpacing: "1px",
            whiteSpace: "nowrap",
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
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "9px 16px",
                color: isActive ? "#fff" : "rgba(255,255,255,0.7)",
                backgroundColor: isActive
                  ? "var(--color-secondary)"
                  : "transparent",
                textDecoration: "none",
                fontSize: "12px",
                fontWeight: isActive ? 600 : 400,
                transition: "background-color 0.15s",
                whiteSpace: "nowrap",
              }}
            >
              <span
                style={{
                  fontSize: "16px",
                  flexShrink: 0,
                  width: "20px",
                  textAlign: "center",
                }}
              >
                {item.icon}
              </span>
              <span className="nav-label">{t(item.labelKey)}</span>
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}
