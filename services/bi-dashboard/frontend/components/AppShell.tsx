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

  const langs = [
    { code: "tr" as const, label: "TR", flag: "🇹🇷" },
    { code: "en" as const, label: "EN", flag: "🇺🇸" },
  ];

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
              {/* Language Segmented Pill */}
              <div
                style={{
                  display: "inline-flex",
                  background: "#112d57",
                  borderRadius: "8px",
                  padding: "2px",
                  gap: "1px",
                }}
              >
                {langs.map((lang) => {
                  const isActive = language === lang.code;
                  return (
                    <button
                      key={lang.code}
                      onClick={() => setLanguage(lang.code)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                        padding: "4px 10px",
                        borderRadius: "6px",
                        border: "none",
                        background: isActive ? "#fff" : "transparent",
                        color: isActive
                          ? "var(--color-primary)"
                          : "rgba(255,255,255,0.5)",
                        fontSize: "11px",
                        fontWeight: isActive ? 700 : 600,
                        cursor: "pointer",
                        letterSpacing: "0.3px",
                        transition: "all 0.2s",
                      }}
                    >
                      <span style={{ fontSize: "13px" }}>{lang.flag}</span>
                      {lang.label}
                    </button>
                  );
                })}
              </div>

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
