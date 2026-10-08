import AppShell from "./components/AppShell";
import { useT } from "./src/i18n/LanguageProvider";

export default function AdminPage() {
  const { t } = useT();
  return (
    <AppShell pageTitle={t("page_title_admin")} userRole="admin">
      <div
        style={{
          padding: "24px",
          color: "var(--color-neutral-dark)",
          fontSize: "14px",
        }}
      >
        {t("shell_coming_soon")}
      </div>
    </AppShell>
  );
}
