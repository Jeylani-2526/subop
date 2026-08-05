import { ReactNode } from "react";
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
  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
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
  );
}
