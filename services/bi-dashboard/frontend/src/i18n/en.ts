// services/bi-dashboard/frontend/src/i18n/en.ts
const en = {
  // Navigation
  nav_overview: "Overview",
  nav_pipeline_monitor: "Pipeline Monitor",
  nav_data_quality: "Data Quality",
  nav_lineage_explorer: "Lineage Explorer",
  nav_data_catalog: "Data Catalog",
  nav_bi_reports: "BI Reports",
  nav_admin: "Admin",
  nav_user_management: "User Management",

  // AppShell
  app_name: "SUBOP",

  // HomePage KPI cards
  kpi_active_pipelines: "Active Pipelines",
  kpi_active_pipelines_trend: "+3 from yesterday",
  kpi_data_quality: "Data Quality Score",
  kpi_data_quality_null: "Not available yet",
  kpi_data_quality_trend: "+2 from last week",
  kpi_records_today: "Records Processed Today",
  kpi_records_trend: "Updated 5 min ago",
  kpi_cdc_latency: "CDC Latency",
  kpi_cdc_trend: "Coming in M7",
  kpi_connectors: "Connectors",
  kpi_connectors_trend: "Live from registry",

  // Pipeline Monitor
  pipeline_search: "Search pipelines...",
  pipeline_all_times: "All Time",
  pipeline_last_1h: "Last 1 Hour",
  pipeline_last_24h: "Last 24 Hours",
  pipeline_last_7d: "Last 7 Days",
  pipeline_all_statuses: "All Statuses",
  pipeline_refresh: "↻ Refresh",
  pipeline_clear: "✕ Clear",
  pipeline_new: "+ New Pipeline",
  pipeline_select: "Select a pipeline to view details",
  pipeline_loading: "Loading...",
  pipeline_empty: "No pipelines yet",
  pipeline_no_results: "No results match the filter",
  pipeline_api_error: "Failed to load pipelines. Is the API running?",
  pipeline_count_suffix: "pipeline",
  pipeline_source: "Source",
  pipeline_target: "Target",
  pipeline_created: "Created",
  pipeline_rows: "Rows processed",
  pipeline_quarantine: "Quarantine",
  pipeline_execution_log: "Execution Log",
  pipeline_no_log: "No log found",
  pipeline_no_run: "No runs yet for this pipeline",
  pipeline_bi_analyst_note:
    "Execution log and pipeline management are restricted in the BI Analyst role.",
  pipeline_back: "← Back to pipeline list",
  pipeline_mobile_readonly: "Pipeline management is read-only on mobile.",

  // Pipeline Form
  form_title: "New Pipeline",
  form_pipeline_name: "Pipeline Name",
  form_pipeline_name_placeholder: "e.g. Orders ETL",
  form_source: "Source",
  form_target: "Target",
  form_connector: "Connector",
  form_connection_ref: "Connection Ref",
  form_table: "Table / Collection",
  form_write_mode: "Write Mode",
  form_compliance: "Compliance",
  form_processing_purpose: "Processing Purpose",
  form_processing_purpose_placeholder: "Order integration",
  form_data_subjects: "Data Subject Categories",
  form_data_subjects_placeholder: "customers, employees",
  form_recipients: "Transfer Recipients (optional)",
  form_recipients_placeholder: "Leave blank if none",
  form_select: "Select",
  form_cancel: "Cancel",
  form_create: "Create",
  form_creating: "Creating...",
  form_success: "✓ Pipeline created successfully!",
  form_error_required: "Required",
  form_error_verbis: "VERBIS registration incomplete",
  form_error_generic: "An error occurred, please try again.",

  // CDC Monitor nav
  nav_cdc: "CDC Monitor",

  // Page titles
  page_title_quality: "Data Quality",
  page_title_lineage: "Lineage Explorer",
  page_title_catalog: "Data Catalog",
  page_title_reports: "BI Reports",
  page_title_admin: "Admin",
  page_title_users: "User Management",
  page_title_cdc: "CDC Monitor",

  // Shell pages — placeholder
  shell_coming_soon: "This module is currently under development.",

  // KPI — CDC Latency
  kpi_cdc_latency_unit: "ms",
  kpi_cdc_latency_pending: "Goes live in W25",

  // CDC Monitor page (wired in W24)
  cdc_latency_strip_title: "Latency Summary",
  cdc_event_feed_title: "Change Event Feed",
  cdc_connector_title: "Connector Status",
  cdc_pending_notice: "Data connection will be wired in W24.",
  cdc_hop_e2e: "End-to-End",
  cdc_hop_capture: "Capture",
  cdc_hop_publish: "Publish",
  cdc_hop_consumer: "Consumer Lag",
  cdc_hop_warehouse: "Warehouse Write",
  cdc_status_healthy: "Healthy",
  cdc_status_warning: "Warning",
  cdc_status_error: "Error",
  cdc_status_unknown: "Unknown",
  cdc_col_table: "Table",
  cdc_col_op: "Op",
  cdc_col_before: "Before",
  cdc_col_after: "After",
  cdc_col_latency: "Latency",
  cdc_col_connector: "Connector",
  cdc_col_status: "Status",
  cdc_col_last_event: "Last Event",
  cdc_col_lag: "Lag",
};

export default en;
