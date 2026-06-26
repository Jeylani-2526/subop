**Connector Development**

**Summary&M4 Preparation\
**

[**1.Introduction**](#introduction) **2**

[**2.Connector Interface Review**](#connector-interface-review) **2**

> [2.1.Current Connector Interface](#current-connector-interface) 2
>
> [2.2.Evaluation of Existing Methods](#evaluation-of-existing-methods)
> 4
>
> [2.3.Interface Extensions
> Requirements](#interface-extensions-requirements) 5

[**3.M4 Readiness Checklist**](#m4-readiness-checklist) **7**

[**4.Open Architecture Questions**](#open-architecture-questions) **8**

[**5.Conclusion**](#conclusion) **9**

# 1.Introduction 

As the SUBOP platform continues to expand its database and data source
support, maintaining a consistent and scalable connector architecture
becomes increasingly important. The current connector framework provides
a common interface for database interactions while allowing each
connector to implement database-specific functionality internally.

The purpose of this document is to evaluate the current connector
interface with respect to the planned M4 development scope. It reviews
whether the existing interface is sufficient for the currently supported
SQL-based connectors, identifies connectors that require interface
extensions, and assesses the readiness of each planned connector for
future implementation.

Furthermore, this document summarizes the current implementation status
of the connector ecosystem and identifies the remaining architectural
questions that should be addressed during the M3 architecture phase.
These findings provide a structured handoff from the M2 research
activities to the upcoming M4 connector development tasks.

# 2.Connector Interface Review

## 2.1.Current Connector Interface 

The current connector architecture is based on a unified interface that
defines the core operations required for interacting with supported data
sources. This approach provides a consistent programming model while
allowing each connector to implement database-specific functionality
internally.

At the current stage of the project, the connector interface consists of
the following five public methods:

-   connect()

-   disconnect()

-   execute_query()

-   execute_write()

-   health_check()

These methods represent the fundamental lifecycle of a connector,
including connection management, query execution, write operations, and
basic health monitoring. By exposing the same public interface, the
PostgreSQL, MySQL, and the planned MSSQL connector can be integrated
into the ETL engine without requiring database-specific logic at higher
architectural layers.

Although the internal implementation differs between database systems,
the connector interface remains stable, allowing the ETL engine to
interact with different databases through a common abstraction layer.

The current connector framework defines a common interface that
standardizes database interactions across different connector
implementations. The diagram below illustrates the core methods that form the
basis of the current connector architecture.

As illustrated in the image, all SQL-based connectors follow the same
lifecycle, beginning with connection establishment and ending with
connection termination. Between these stages, the connector provides
standardized methods for executing read and write operations, while the
health_check() method enables basic connectivity verification. This
unified interface simplifies integration with the ETL engine and reduces
database-specific dependencies within higher architectural layers.

## 2.2.Evaluation of Existing Methods

The current connector interface consists of five core methods that
define the lifecycle of SQL-based connectors: connect(), disconnect(),
execute_query(), execute_write(), and health_check(). These methods
provide a clear separation of responsibilities and establish a
consistent programming model for all relational database connectors.

Based on the current implementation and the planned M4 scope, the
existing interface is considered sufficient for SQL-based database
systems, including PostgreSQL, MySQL, and the planned MSSQL connector.
Although these databases differ in connection drivers, SQL dialects, and
internal implementations, the overall interaction pattern remains the
same. Consequently, no modifications to the public connector interface
are required for these database systems.

The primary differences occur within the internal implementation rather
than the interface itself. Each connector is responsible for handling
its own database-specific behavior while exposing the same public
methods to the ETL engine. This design reduces coupling between
higher-level components and individual database technologies while
improving maintainability and extensibility.

To determine whether the current connector interface is suitable for
future development, each planned connector was evaluated against the
existing set of public methods. The image below summarizes the
compatibility of the current interface with both implemented and planned
connector types.

As illustrated on the image the existing connector interface fully
satisfies the requirements of SQL-based connectors such as PostgreSQL,
MySQL, and the planned MSSQL implementation. These connectors share the
same connection lifecycle and database interaction pattern despite
differences in their internal implementations.

However, connectors for non-relational data sources require additional
capabilities beyond the current interface. For example, Kafka connectors
require subscription-based communication, REST connectors need
pagination support, and MongoDB connectors operate on document-oriented
data instead of SQL statements. Consequently, future connector
implementations may require interface extensions while preserving the
existing abstraction for SQL-based connectors.

## 2.3.Interface Extensions Requirements 

Although the current connector interface is sufficient for SQL-based
database systems, not all planned data sources can be fully supported
through the existing set of connector methods. Some connectors require
additional capabilities because their communication models differ
significantly from traditional relational databases.

PostgreSQL, MySQL, and the planned MSSQL connector can all operate using
the existing interface without introducing new public methods. Their
differences are primarily limited to connection management, SQL
dialects, and internal implementation details.

In contrast, connectors for Kafka, REST APIs, and MongoDB introduce
requirements that extend beyond the current abstraction. Kafka
connectors require subscription-based communication for consuming
messages, REST API connectors need built-in pagination support to
retrieve large datasets efficiently, and MongoDB connectors operate on
document-oriented data rather than SQL statements. These differences
indicate that future connector implementations may require
connector-specific interface extensions while maintaining a common
architectural foundation.

The planned connectors can be divided into SQL-based and non-SQL
connector types. The image below illustrates which connectors can
directly reuse the current interface and which require additional
capabilities before implementation.

As shown on the image, SQL-based connectors can be implemented using the
existing connector interface without introducing additional public
methods. Their implementation differences are handled internally through
database-specific drivers and SQL dialects.

Conversely, connectors for Kafka, REST APIs, and MongoDB require
functionality that is not currently represented by the existing
interface. These connectors rely on communication patterns and data
models that differ from relational databases and therefore require
additional connector-specific capabilities. Nevertheless, these
extensions can be incorporated without changing the overall connector
architecture, preserving the modular and extensible design of the SUBOP
platform.

# 3.M4 Readiness Checklist 

To assess the current state of connector development, each planned
connector was evaluated with respect to its implementation status,
estimated complexity, interface compatibility, and remaining development
work. The checklist below summarizes the current readiness of each
connector for the planned M4 implementation phase.

3. M4 Readiness Checklist

To assess the current state of connector development, each planned connector was evaluated with respect to its implementation status, estimated complexity, interface compatibility, and remaining development work. The checklist below summarizes the current readiness of each connector for the planned M4 implementation phase.

| Connector | Status | Interface Compatibility | Estimated Complexity | M2 Research Status | Remaining Work |
|------------|--------|-------------------------|----------------------|-------------------|----------------|
| PostgreSQL | Completed | Fully Supported | Low | Completed | No major work required |
| MySQL | Planned | Fully Supported | Medium | Completed | Validate SQL dialect and implement connector |
| MSSQL | Planned | Fully Supported | High | Completed | Implement ODBC support and SQL Server-specific features |
| Kafka | Planned | Requires Extension | High | Partially Completed | Design subscription interface |
| REST API | Planned | Requires Extension | Medium | Partially Completed | Add pagination support |
| MongoDB | Planned | Requires Extension | High | Partially Completed | Design document abstraction layer |

As summarized in the table above, the current connector framework is well prepared for SQL-based database systems. PostgreSQL has already been implemented, while MySQL and MSSQL can be integrated using the existing connector interface with database-specific adaptations.

The remaining planned connectors represent a different category of data sources. Since Kafka, REST APIs, and MongoDB rely on communication models that differ from relational databases, additional architectural work is required before implementation can begin. Nevertheless, the current abstraction provides a solid foundation that can be extended without introducing significant changes to the overall connector framework.

# 4.Open Architecture Questions 

Although the current connector interface provides a solid foundation for
SQL-based connectors, several architectural questions remain unanswered
before the M4 implementation phase can begin. These questions should be
addressed during the M3 architecture phase to ensure that future
connector implementations remain scalable, maintainable, and consistent
across different data sources.

1.  **Should the connector framework support only synchronous execution,
    or should asynchronous execution also be supported for connectors
    such as Kafka and REST APIs?**

2.  **Should all connectors expose the same public interface, or should
    connector-specific methods (e.g., subscribe() for Kafka) be
    introduced through interface extensions?**

3.  **How should non-relational data sources such as MongoDB be
    integrated while preserving a consistent abstraction layer designed
    primarily for SQL-based connectors?**

4.  **Should connector-specific features such as REST API pagination,
    Kafka subscriptions, and MongoDB document operations be implemented
    within individual connectors or standardized through shared
    abstraction components?**

5.  **What common result format and error-handling strategy should be
    adopted to ensure consistent behavior across all supported
    connectors regardless of the underlying technology?**

Answering these questions will provide the architectural guidance
required for implementing future connectors while maintaining the
modular design principles of the SUBOP platform.

# 5.Conclusion 

This document evaluated the current connector architecture with respect
to the planned M4 implementation scope. The review confirms that the
existing connector interface is sufficient for SQL-based database
systems, including PostgreSQL, MySQL, and the planned MSSQL connector,
as they share a common connection lifecycle and interaction model.

The evaluation also identified several planned connectors that require
interface extensions due to their different communication patterns and
data models. In particular, Kafka, REST API, and MongoDB connectors
introduce additional architectural requirements that should be addressed
during the M3 architecture phase before implementation begins.

The M4 readiness assessment demonstrates that the current connector
framework provides a solid foundation for future development while
remaining flexible enough to support additional connector-specific
capabilities when required. By maintaining a common abstraction layer
and extending the architecture only where necessary, the SUBOP platform
can continue to evolve in a scalable, maintainable, and
database-independent manner.

Overall, this development summary provides a clear overview of the
current connector status, highlights the remaining architectural
challenges, and serves as a preparation document for the upcoming M4
connector implementation tasks.
