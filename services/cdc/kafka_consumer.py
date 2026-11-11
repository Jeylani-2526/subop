"""Kafka CDC consumer — StreamingConnector.subscribe() for Debezium topics (M7W26T3).

Run:  python -m services.cdc.kafka_consumer
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from services.cdc.normalizer import SchemaDriftDetector, message_table
from services.connectors.errors import ConnectorError
from services.connectors.streaming_connector_base import (
    StreamingConnectionConfig,
    StreamingConnector,
    raise_streaming_connection_error,
)

log = logging.getLogger("subop.cdc.consumer")

DEFAULT_PATTERN = r"^subop-postgres-cdc\.cdc_demo\..*"
DEFAULT_GROUP = "subop-cdc-consumer"
DEFAULT_STATE_REF = "dw-main"
RETRY_DELAY_SECONDS = 2.0

# Message outcomes, returned by handle_message so tests can assert on them.
HANDLED = "handled"
HALTED = "halted"
RETRY = "retry"
SKIPPED = "skipped"

Handler = Callable[[Dict[str, Any], Dict[str, Any]], None]


class KafkaCDCConnector(StreamingConnector):
    """Consumes Debezium topics, drift-checks each message, and hands the
    neutral event to a handler.

    Delivery is at-least-once. An offset is committed only after the handler
    returns, so a crash replays the message rather than losing it; making the
    replay harmless is the handler's job (M7W26T4's upsert).

    A halt is table-scoped (CDC Design Note Section 3.4). Debezium writes one
    topic per table, so halting a table pauses that topic's partition and
    never commits past the halting message. Other tables keep flowing.
    """

    def __init__(
        self,
        config: StreamingConnectionConfig,
        *,
        state_store: Any = None,
        detector: Optional[SchemaDriftDetector] = None,
        consumer_factory: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> None:
        super().__init__(config)
        self.state_store = state_store
        self.detector = detector or SchemaDriftDetector()
        self._consumer_factory = consumer_factory or _confluent_consumer
        self._stop = threading.Event()
        self.halted: Dict[str, Dict[str, str]] = {}
        self._paused: set = set()

    # -- lifecycle ---------------------------------------------------------

    def restore_state(self) -> None:
        """Reload persisted baselines and halts before the first message."""
        if self.state_store is None:
            return
        for table, entry in self.state_store.load().items():
            if entry.get("baseline"):
                self.detector.restore(table, entry["baseline"])
            if entry.get("halted"):
                # Not paused here: the topic for a table is only known from a
                # message. The uncommitted halting message is redelivered and
                # halts again, so the halt is reproduced rather than assumed.
                self.halted[table] = {
                    "error_code": entry.get("halt_error_code") or "",
                    "reason": entry.get("halt_reason") or "",
                }

    async def subscribe(self, on_message: Handler) -> None:
        """Consume until unsubscribe(). on_message must be synchronous: it
        runs on the consumer's worker thread."""
        await asyncio.to_thread(self.run, on_message)

    async def unsubscribe(self) -> None:
        self._stop.set()
        self.subscribed = False

    def stop(self) -> None:
        self._stop.set()

    def run(self, on_message: Handler) -> None:
        consumer = self._consumer_factory(
            {
                "bootstrap.servers": self.config.bootstrap_servers,
                "group.id": self.config.group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
                "enable.auto.offset.store": False,
            }
        )
        try:
            consumer.subscribe([self.config.topic])
        except Exception as exc:
            raise_streaming_connection_error(
                f"Could not subscribe to {self.config.topic}: {exc}",
                error_code="KAFKA_SUBSCRIBE_FAILED",
            )
        self.subscribed = True
        log.info(
            "subscribed to %s as group %s", self.config.topic, self.config.group_id
        )
        try:
            while not self._stop.is_set():
                msg = consumer.poll(1.0)
                if msg is None:
                    continue
                if self.handle_message(consumer, msg, on_message) == RETRY:
                    time.sleep(RETRY_DELAY_SECONDS)
        finally:
            self.subscribed = False
            consumer.close()

    # -- per message -------------------------------------------------------

    def handle_message(self, consumer: Any, msg: Any, on_message: Handler) -> str:
        error = msg.error()
        if error is not None:
            if _is_partition_eof(error):
                return SKIPPED
            log.warning("kafka error on %s: %s", msg.topic(), error)
            return SKIPPED

        key = (msg.topic(), msg.partition())
        if key in self._paused:
            return SKIPPED

        raw = msg.value()
        if raw is None:
            # tombstones.on.delete=false, so none are expected; nothing to apply.
            consumer.commit(message=msg, asynchronous=False)
            return SKIPPED

        try:
            envelope = json.loads(raw)
        except (TypeError, ValueError) as exc:
            return self._halt(
                consumer, msg, msg.topic(), "CDC_ENVELOPE_MALFORMED", str(exc)
            )

        try:
            table = message_table(envelope)
        except ConnectorError as exc:
            return self._halt(consumer, msg, msg.topic(), exc.error_code, exc.message)

        had_baseline = self.detector.baseline(table) is not None
        try:
            event = self.detector.process(envelope)
        except ConnectorError as exc:
            return self._halt(consumer, msg, table, exc.error_code, exc.message)

        if not had_baseline and self.state_store is not None:
            self.state_store.save_baseline(table, self.detector.baseline(table))

        meta = _message_meta(msg, envelope)
        try:
            on_message(event, meta)
        except ConnectorError as exc:
            if exc.retryable:
                log.warning(
                    "retryable failure on %s, will retry: %s", table, exc.message
                )
                consumer.seek(_topic_partition(msg))
                return RETRY
            return self._halt(consumer, msg, table, exc.error_code, exc.message)
        except Exception as exc:  # an unclassified failure is not safe to skip
            return self._halt(consumer, msg, table, "CDC_HANDLER_FAILED", repr(exc))

        if self.state_store is not None:
            self.state_store.record_event(table, event["ts_ms"], meta.get("lsn"))
            self.state_store.append_event(event, meta.get("lsn"))
        if self.halted.pop(table, None) is not None:
            # A halt restored at startup that no longer reproduces — e.g. a
            # handler failure since fixed. A drift halt cannot reach here: its
            # message keeps failing the restored baseline until reset.
            log.info("halt on %s no longer reproduces; cleared", table)
            if self.state_store is not None:
                self.state_store.clear_halt(table)
        consumer.commit(message=msg, asynchronous=False)
        return HANDLED

    def _halt(self, consumer: Any, msg: Any, table: str, code: str, reason: str) -> str:
        key = (msg.topic(), msg.partition())
        consumer.pause([_topic_partition(msg)])
        self._paused.add(key)
        self.halted[table] = {"error_code": code, "reason": reason}
        if self.state_store is not None:
            self.state_store.record_halt(table, code, reason)
        log.error("halted %s (%s): %s", table, code, reason)
        return HALTED


# -- helpers ---------------------------------------------------------------


def _message_meta(msg: Any, envelope: Dict[str, Any]) -> Dict[str, Any]:
    payload = envelope.get("payload") if "payload" in envelope else envelope
    source = (payload or {}).get("source") or {}
    return {
        "topic": msg.topic(),
        "partition": msg.partition(),
        "offset": msg.offset(),
        "lsn": source.get("lsn"),
    }


def _is_partition_eof(error: Any) -> bool:
    try:
        from confluent_kafka import KafkaError
    except ImportError:  # pragma: no cover
        return False
    return error.code() == KafkaError._PARTITION_EOF


def _topic_partition(msg: Any) -> Any:
    from confluent_kafka import TopicPartition

    return TopicPartition(msg.topic(), msg.partition(), msg.offset())


def _confluent_consumer(settings: Dict[str, Any]) -> Any:
    from confluent_kafka import Consumer

    return Consumer(settings)


# -- CLI -------------------------------------------------------------------


def _load_dotenv() -> None:
    # M7W26T1 Finding 6: host-run scripts never loaded .env. Values already in
    # the environment win, so an exported variable still overrides the file.
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def _log_event(event: Dict[str, Any], meta: Dict[str, Any], suffix: str = "") -> None:
    row = event["after"] or event["before"] or {}
    log.info(
        "%s %s id=%s ts_ms=%s lsn=%s%s",
        event["op"],
        event["table"],
        row.get("id"),
        event["ts_ms"],
        meta.get("lsn"),
        suffix,
    )


def _log_handler(event: Dict[str, Any], meta: Dict[str, Any]) -> None:
    """--log-only: consume and log without writing to the warehouse."""
    _log_event(event, meta)


def _state_store(state_ref: str) -> Any:
    from services.cdc.state_store import CDCStateStore
    from services.etl_engine.connection_resolver import resolve_connection

    layer, _ = resolve_connection("postgresql", state_ref)
    store = CDCStateStore(layer)
    store.ensure_schema()
    return store


def _warehouse_handler(warehouse_ref: str) -> Handler:
    from services.cdc.warehouse_sink import WarehouseSink
    from services.etl_engine.connection_resolver import resolve_connection

    # Its own connection, separate from the state store's, so a failed write
    # here never rolls back or blocks a state update there.
    layer, _ = resolve_connection("postgresql", warehouse_ref)
    sink = WarehouseSink(layer)
    sink.ensure_schema()

    def handle(event: Dict[str, Any], meta: Dict[str, Any]) -> None:
        affected = sink.apply(event, meta)
        _log_event(
            event, meta, " -> warehouse" if affected else " -> unchanged (not newer)"
        )

    return handle


def main(argv: Optional[list] = None) -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(description="SUBOP CDC Kafka consumer")
    parser.add_argument(
        "--bootstrap",
        default=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    )
    parser.add_argument(
        "--pattern", default=os.environ.get("KAFKA_TOPIC_CDC_PATTERN", DEFAULT_PATTERN)
    )
    parser.add_argument(
        "--group", default=os.environ.get("KAFKA_CDC_CONSUMER_GROUP", DEFAULT_GROUP)
    )
    parser.add_argument("--state-ref", default=DEFAULT_STATE_REF)
    parser.add_argument("--warehouse-ref", default=DEFAULT_STATE_REF)
    parser.add_argument(
        "--log-only", action="store_true", help="do not write to the warehouse"
    )
    parser.add_argument("--reset-table", metavar="SCHEMA.TABLE")
    parser.add_argument("--show-state", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    store = _state_store(args.state_ref)

    if args.reset_table:
        store.reset(args.reset_table)
        print(f"reset {args.reset_table}: baseline and halt cleared")
        return 0
    if args.show_state:
        for table, entry in store.load().items():
            print(table, json.dumps(entry, default=str))
        return 0

    handler = _log_handler if args.log_only else _warehouse_handler(args.warehouse_ref)
    connector = KafkaCDCConnector(
        StreamingConnectionConfig(args.bootstrap, args.pattern, args.group),
        state_store=store,
    )
    connector.restore_state()
    if connector.halted:
        log.warning("halted at startup: %s", sorted(connector.halted))
    try:
        connector.run(handler)
    except KeyboardInterrupt:
        connector.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
