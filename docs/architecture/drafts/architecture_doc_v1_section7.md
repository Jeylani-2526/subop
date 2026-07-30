# SUBOP Architecture Document v1
**Section 7 of 9 · Owner: Abdullah · Draft date: 9 July 2026**



---

## Section 7 — Deployment Topology

### 7.1 Docker Container Network Diagram

The full SUBOP development environment runs as a single Docker Compose stack, all services attached to one bridge network (`subop_network`). The network diagram below shows every service currently defined in `docker-compose.yml`, drawn and exported per Omer's confirmed port mappings.

**Diagram files (embedded/attached):**
- `deployment_topology_diagram.drawio` — editable source (open in diagrams.net / draw.io)

![Deployment Topology Diagram](deployment_topology_diagram.png)

**Reachability boundaries:**

| Service | Port Mapping | Reachability | Notes |
|---|---|---|---|
| `postgres` (15) | 5432:5432 | Application-layer reachable (internal) | Warehouse target; also the BI Dashboard's only dependency |
| `mysql` (8) | 3306:3306 | Application-layer reachable (internal) | Source connector target |
| `mssql` (2022-latest) | 1433:1433 | Application-layer reachable (internal) | Source connector target; heaviest single-container memory footprint of the three databases |
| `kafka` | 9092:9092 | Application-layer reachable (internal) | CDC event bus; depends on `zookeeper` at startup |
| `zookeeper` | 2181:2181 | Internal-only — not reachable by application code directly | Exists solely to coordinate Kafka; no SUBOP module calls it directly |
| `pgadmin` | 8080:80 (mapped to host) | Host/dev-machine reachable only | Developer GUI tooling; not a runtime dependency of any SUBOP module and is not part of the application-layer trust boundary |

This distinction matters for Section 8 (Security Architecture): `pgadmin` sits outside the application trust boundary and is a candidate for exclusion from any pilot/production deployment entirely, since it exists for local developer convenience rather than a platform function.

### 7.2 Service Dependency Table

| Consuming Module | Depends On | Failure Impact if Dependency Is Unavailable |
|---|---|---|
| ETL Engine | `postgres`, `mysql`, `mssql`, `kafka` | Batch runs against the affected source fail (recoverable — retried per Section 5.1's connector-timeout classification); CDC-fed runs stall if `kafka` is down |
| Connector Framework | Whichever of `postgres` / `mysql` / `mssql` is configured for that connector instance | Connection attempts fail `health_check()`; classified per `ConnectorError.retryable` (Section 3.5, Question 5) |
| CDC / Real-Time Streaming | `kafka` (which itself depends on `zookeeper`) + the source database's WAL/binlog | If `zookeeper` is down, `kafka` cannot accept broker connections, which stalls the entire CDC path — this is the single most fragile dependency chain in the stack |
| BI Dashboard & OLAP | `postgres` only | Dashboards fail to load; no dependency on `mysql`, `mssql`, or `kafka` since the warehouse is the sole read target (Section 2.4/2.5) |
| Governance Layer (Quality, Lineage, Catalog) | `postgres` only | Same isolation as BI Dashboard — governance metadata lives in the same warehouse |
| Security & Compliance | None of the above directly; wraps every module as middleware (Section 2.7) | Not affected by any single service outage; addressed fully in Section 8 |

**Observation for M4 planning:** every module except CDC has exactly one direct-dependency failure mode. CDC is the outlier — its two-hop dependency (`kafka` → `zookeeper`) is the only place in this topology where a single container failure (`zookeeper`) can silently stall a module (`kafka`) that three other things depend on. This is worth carrying into M7 as an explicit monitoring requirement (alert on `zookeeper` health specifically, not just `kafka`'s).

### 7.3 Estimated Container Resource Requirements

Estimates below are planning figures confirmed against Omer's Week 8 setup and standard image guidance (e.g., Microsoft's documented minimum for MSSQL Developer edition); they are not yet backed by measured `docker stats` output under production-representative load, and should be revisited once M4 connector work generates realistic traffic.

| Service | Single-Node Dev (per container) | Multi-Node Pilot (per container) | Rationale |
|---|---|---|---|
| `postgres` | 1 vCPU / 1 GB RAM | 2 vCPU / 4 GB RAM | Warehouse target carries the heaviest read load in pilot (BI + Governance both query it exclusively) |
| `mysql` | 1 vCPU / 1 GB RAM | 2 vCPU / 4 GB RAM | Source-side only; scales with connector test/pilot traffic |
| `mssql` | 2 vCPU / 2 GB RAM | 2 vCPU / 4 GB RAM | Microsoft's documented minimum for Developer edition is 2 GB RAM; this is a floor, not a target |
| `kafka` | 1 vCPU / 1 GB RAM | 2 vCPU / 2 GB RAM | JVM heap needs headroom beyond the container floor once CDC throughput increases in M7 |
| `zookeeper` | 0.5 vCPU / 256 MB RAM | 1 vCPU / 512 MB RAM | Lightweight coordination role only |
| `pgadmin` | 0.25 vCPU / 256 MB RAM | 0.25 vCPU / 256 MB RAM | Dev tooling only — intentionally not scaled for pilot; candidate for exclusion per 7.1 |
| **Total (dev host)** | **~5.75 vCPU / ~5.5 GB RAM** | — | Comfortably runs on a standard developer laptop (8 vCPU / 16 GB class machine) |
| **Total (pilot, excl. pgadmin)** | — | **~9.25 vCPU / ~14.5 GB RAM** | Recommended split across at least two nodes: databases (postgres/mysql/mssql) on one node, Kafka/Zookeeper + application layer on a second, to isolate the CDC path's failure domain from the connector-heavy database node |

**Single-node dev vs. multi-node pilot — the key difference isn't just headroom.** The dev topology co-locates everything deliberately, since local development doesn't need failure isolation. The pilot split above exists specifically so that a database-side issue (e.g., an MSSQL connector under heavy load) doesn't compete for CPU with the CDC path, which has a hard 30-second end-to-end latency KPI (Section 5.2) that a resource-starved `kafka`/`zookeeper` pair would jeopardize first.

---

