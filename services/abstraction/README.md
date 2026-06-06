# Module 2 — Database Abstraction Layer

**Status:** ⏳ Scheduled for M4 (20 Jul – 9 Aug 2026)
**Owner:** Omer

## Description

Hides the differences between database engines behind a single, unified interface.
ETL pipelines written once execute correctly across all supported databases
with zero code change when switching the underlying database engine.

## Key Capabilities

- Universal SQL/NoSQL query interface
- Type normalisation across different database type systems
- SQL dialect translation (PostgreSQL → MySQL → MSSQL)
- Performance target: ≥85% of native database query performance retained

## Architecture Constraint

Column masking is enforced server-side at this layer — never client-side.
