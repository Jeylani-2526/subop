from services.connectors.errors import (
    ConnectionError as ConnectorConnectionError,
)

_CONNECTOR_TYPE = "streaming"


class StreamingConnectionConfig:
    """Stores the connection settings for a streaming (Kafka) source."""

    def __init__(self, bootstrap_servers, topic, group_id):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id


class StreamingConnector:
    """
    Optional mixin adding streaming capability to a connector.

    Per Architecture Section 3, decision 2 (interface segregation):
    ConnectorBase's five methods stay mandatory for every connector;
    StreamingConnector.subscribe() is added only where streaming applies,
    composed in rather than forced onto every connector. Per decision 1,
    ConnectorBase stays synchronous while this mixin is asynchronous —
    FastAPI threadpool-wraps sync connector calls, which a native async
    method does not need.

    Not an abc.ABC: services/connectors/ raises ConnectorError by
    convention rather than enforcing method presence at class-definition
    time, the same pattern FileConnectorBase already follows.
    """

    def __init__(self, config):
        self.config = config
        self.subscribed = False

    async def subscribe(self, on_message):
        """
        Subscribe to the configured topic, invoking on_message(event) for
        each message received.

        Args:
            on_message:
                Callable (sync or async) invoked once per message. Its
                signature and the event shape it receives are defined by
                the concrete connector — e.g. a Kafka connector wrapping
                confluent-kafka's Consumer, yielding Debezium envelopes.

        Raises:
            ConnectorError subclass (see services/connectors/errors.py)
            on failure — the same shape QueryError/WriteError already use,
            so a streaming failure surfaces no differently from any other
            connector failure.

        No consumption logic in M7W22T3 by design: this method raises
        NotImplementedError until Week 23's connector implements it, so
        later milestones have a fixed contract to build against rather
        than inventing one under time pressure.
        """
        raise NotImplementedError(
            "subscribe() is defined by StreamingConnector but has no "
            "implementation until Week 23's Kafka connector lands."
        )

    async def unsubscribe(self):
        """Stop consuming and release the subscription, if active."""
        self.subscribed = False

    def health_check(self):
        """Check whether the subscription is currently active."""
        return self.subscribed


def raise_streaming_connection_error(message, *, error_code, retryable=False):
    """
    Shared helper so every streaming connector raises the same
    ConnectorConnectionError shape (error_code, connector_type="streaming",
    retryable) rather than each one constructing it ad hoc.
    """
    raise ConnectorConnectionError(
        message,
        error_code=error_code,
        connector_type=_CONNECTOR_TYPE,
        retryable=retryable,
    )
