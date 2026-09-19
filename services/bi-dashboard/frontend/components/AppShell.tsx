import { ReactNode, useState } from "react";
import NavigationSidebar from "./NavigationSidebar";

interface AppShellProps {
  children: ReactNode;
  userRole: "admin" | "data_engineer" | "bi_analyst" | "viewer";
  pageTitle: string;
}

export default function AppShell({
  children,
  userRole,
  pageTitle,
}: AppShellProps) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        overflow: "hidden",
        flexDirection: "column",
      }}
    >
      {/* Mobile Header */}
      <div className="subop-mobile-header">
        <span>SUBOP</span>
        <button
          onClick={() => setMobileNavOpen(!mobileNavOpen)}
          style={{
            background: "none",
            border: "none",
            color: "#fff",
            fontSize: "20px",
            cursor: "pointer",
            padding: 0,
          }}
        >
          ☰
        </button>
      </div>

      {/* Mobile Nav Overlay */}
      {mobileNavOpen && (
        <div
          onClick={() => setMobileNavOpen(false)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            zIndex: 200,
          }}
        />
      )}
      {mobileNavOpen && (
        <div
          className="subop-mobile-overlay"
          style={{
            position: "fixed",
            left: 0,
            top: 0,
            zIndex: 300,
            height: "100vh",
          }}
        >
          <NavigationSidebar userRole={userRole} />
        </div>
      )}

      {/* Desktop + Tablet */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <NavigationSidebar userRole={userRole} />

        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minWidth: 0,
            overflow: "hidden",
          }}
        >
          <header
            style={{
              height: "56px",
              flexShrink: 0,
              backgroundColor: "var(--color-primary)",
              display: "flex",
              alignItems: "center",
              padding: "0 24px",
              justifyContent: "space-between",
            }}
          >
            <span style={{ color: "#fff", fontSize: "15px", fontWeight: 600 }}>
              {pageTitle}
            </span>
            <span style={{ color: "rgba(255,255,255,0.7)", fontSize: "12px" }}>
              SUBOP
            </span>
          </header>
          <main
            style={{
              flex: 1,
              minHeight: 0,
              overflow: "hidden",
              backgroundColor: "var(--color-background)",
            }}
          >
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
