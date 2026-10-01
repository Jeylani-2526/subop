import { ReactNode, useState } from "react";
import NavigationSidebar from "./NavigationSidebar";
import { useT } from "../src/i18n/LanguageProvider";

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
  const { language, setLanguage } = useT();

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
              boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
            }}
          >
            <span style={{ color: "#fff", fontSize: "15px", fontWeight: 600 }}>
              {pageTitle}
            </span>

            <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
              {/* Language Toggle — tek buton */}
              <button
                onClick={() => setLanguage(language === "tr" ? "en" : "tr")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  padding: "4px 10px",
                  borderRadius: "6px",
                  border: "1px solid rgba(255,255,255,0.25)",
                  background: "rgba(255,255,255,0.1)",
                  color: "#fff",
                  fontSize: "11px",
                  fontWeight: 700,
                  cursor: "pointer",
                  letterSpacing: "0.3px",
                  transition: "background 0.2s",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.background = "rgba(255,255,255,0.2)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.background = "rgba(255,255,255,0.1)")
                }
              >
                <span style={{ fontSize: "13px" }}>
                  {language === "tr" ? "🇹🇷" : "🇺🇸"}
                </span>
                {language === "tr" ? "TR" : "EN"}
              </button>

              <div
                style={{
                  width: "1px",
                  height: "20px",
                  background: "rgba(255,255,255,0.15)",
                }}
              />
              <span
                style={{
                  color: "rgba(255,255,255,0.4)",
                  fontSize: "11px",
                  fontWeight: 600,
                  letterSpacing: "2px",
                }}
              >
                SUBOP
              </span>
            </div>
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
