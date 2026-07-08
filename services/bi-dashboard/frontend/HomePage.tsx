import AppShell from '../components/AppShell';
import KPISummaryCard from '../components/KPISummaryCard';

export default function HomePage() {
  return (
    <AppShell pageTitle="Home / Overview" userRole="admin">
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '16px',
        }}
      >
        <KPISummaryCard
          label="Active Pipelines"
          value={24}
          trend="up"
          trendValue="+3 from yesterday"
          status="healthy"
        />
        <KPISummaryCard
          label="Data Quality Score"
          value={87}
          unit="%"
          trend="up"
          trendValue="+2 from last week"
          status="healthy"
        />
        <KPISummaryCard
          label="Records Processed Today"
          value="4.8M"
          trend="neutral"
          trendValue="Updated 5 min ago"
          status="healthy"
        />
        <KPISummaryCard
          label="CDC Latency"
          value={12}
          unit="ms"
          trend="down"
          trendValue="Above threshold"
          status="warning"
        />
      </div>
    </AppShell>
  );
}
