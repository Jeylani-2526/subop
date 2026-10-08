# CDC Infrastructure Verification Report

**Task ID:** M7W22T7  
**Project:** SUBOP  
**Date:** October 8, 2026  
**Environment:** Local Development — Docker Compose  
**Status:** Verification completed (final post-restart output not attached)

## 1. Objective

The objective of this task is to verify that the Kafka Connect and Debezium infrastructure starts successfully within the SUBOP Docker Compose development environment.

The verification focuses on:

- Starting the Docker Compose stack from a clean environment.
- Checking container health and service dependencies.
- Verifying Kafka Connect REST API availability.
- Confirming that the Debezium PostgreSQL connector plugin is installed.
- Ensuring that no connectors have been registered at this stage.

Connector registration is intentionally excluded from this task and is planned for Week 23.

## 2. Environment Configuration

The following components were used:

| Component | Docker Image |
|---|---|
| Apache Kafka | confluentinc/cp-kafka:7.6.0 |
| Apache ZooKeeper | confluentinc/cp-zookeeper:7.6.0 |
| Kafka Connect / Debezium | quay.io/debezium/connect:3.6 |
| PostgreSQL | postgres:15 |
| MySQL | mysql:8 |

Kafka Connect was configured with the following settings:

| Configuration | Value |
|---|---|
| Bootstrap Servers | kafka:29092 |
| REST API Port | 8083 |
| Group ID | subop-connect-cluster |
| Config Storage Topic | subop-connect-configs |
| Offset Storage Topic | subop-connect-offsets |
| Status Storage Topic | subop-connect-status |

Kafka Connect depends on Kafka reaching a healthy state before startup.

## 3. Docker Compose Verification

The Docker Compose configuration was validated using:

```bash
docker compose config --quiet
```

**Result:** PASS

The command completed without errors or warnings after the required environment variables were added.

The Debezium image was downloaded using:

```bash
docker compose pull connect
```

**Result:** PASS

The image `quay.io/debezium/connect:3.6` was downloaded successfully.

## 4. Clean Startup Verification

The Docker Compose stack was started using:

```bash
docker compose up -d
```

During the clean startup, the MySQL container was initially reported as unhealthy.

The MySQL logs showed that the database was performing its first-time initialization, including database creation and application user setup.

Relevant log messages:

```text
Initializing database files
Database files initialized
Creating database subop
Creating user subop_app
MySQL init process done. Ready for start up.
ready for connections. port: 3306
```

The MySQL container subsequently reached a healthy state.

Verified output:

```text
subop-mysql   Up 2 minutes (healthy)
```

A longer healthcheck startup grace period of 180 seconds was recommended to accommodate first-time MySQL initialization.

The Compose startup was retried after MySQL became healthy. The final full-stack container status should be retained as additional verification evidence.

## 5. Kafka Connect REST API Verification

### 5.1 Kafka Connect Version Endpoint

Command:

```bash
curl.exe http://localhost:8083/
```

Actual response:

```json
{
  "version": "4.3.0",
  "commit": "a9ce3221537b8653",
  "kafka_cluster_id": "0iuMnjd6TwKPqdNSZzUybw"
}
```

**Result:** PASS

The Kafka Connect REST API returned version and cluster information successfully.

### 5.2 Debezium PostgreSQL Connector Plugin

Command:

```bash
curl.exe http://localhost:8083/connector-plugins
```

The response included the following connector:

```json
{
  "class": "io.debezium.connector.postgresql.PostgresConnector",
  "type": "source",
  "version": "3.6.3.Final"
}
```

**Result:** PASS

The Debezium PostgreSQL source connector plugin is available and recognized by Kafka Connect.

### 5.3 Registered Connectors

Command:

```bash
curl.exe http://localhost:8083/connectors
```

Actual response:

```json
[]
```

**Result:** PASS

The connector list is empty, confirming that no connectors have been registered.

This matches the planned scope of Week 22.

## 6. Container Health Verification

The following components were confirmed healthy during the verification process:

| Service | Observed Status |
|---|---|
| ZooKeeper | Healthy |
| Kafka | Healthy |
| PostgreSQL | Healthy |
| MySQL | Healthy |
| Microsoft SQL Server | Healthy |
| Oracle Database | Healthy |
| Kafka Connect | Running; REST API responsive |

A Docker healthcheck was subsequently added to the Kafka Connect service. Its final healthy status after the full-stack restart should be confirmed from the latest `docker compose ps` output.

## 7. Issues Encountered

### Issue 1 — Debezium Image Not Found

The initially configured image `debezium/connect:3.0` could not be resolved.

**Resolution:** The image reference was changed to `quay.io/debezium/connect:3.6`.

### Issue 2 — Missing Environment Variables

Several required environment variables were initially undefined.

**Resolution:** The local `.env` file was updated with Kafka Connect, pgAdmin, and PostgreSQL CDC configuration values.

### Issue 3 — MySQL Initialization Delay

MySQL was temporarily marked unhealthy during its initial database initialization.

**Resolution:** The initialization was allowed to complete, and MySQL subsequently became healthy. A longer startup grace period was recommended for future clean starts.

## 8. Verification Summary

| Test | Result |
|---|---|
| Docker Compose configuration validation | PASS |
| Debezium image download | PASS |
| Kafka dependency health | PASS |
| Kafka Connect REST API availability | PASS |
| Version endpoint | PASS |
| PostgreSQL connector plugin discovery | PASS |
| Empty connector list | PASS |
| MySQL recovery after initial startup | PASS |
| Final full-stack health after clean restart | Pending output confirmation |

## 9. Conclusion

The Kafka Connect and Debezium infrastructure was successfully deployed in the SUBOP local development environment.

The REST API is accessible, the PostgreSQL connector plugin is available, and no connectors have been registered.

The observed startup issue was related to MySQL initialization rather than Kafka Connect or Debezium.

The infrastructure is ready for the next development phase, in which PostgreSQL CDC connector registration and end-to-end change data capture testing can be implemented.

Final confirmation of all container health states after the clean restart remains to be documented.