"""
Streaming Data Processor

Simulates a near-real-time streaming pipeline using micro-batch processing.
In production, replace with PySpark Structured Streaming or Kafka consumers.

Architecture:
  Raw events → Bronze streaming table → Silver transformation → Gold aggregation
  
Supported event types:
  - TRANSACTION:  Billing transaction events
  - CUSTOMER_UPDATE: CRM customer update events
  - ANOMALY_SIGNAL: Pre-flagged anomaly events from upstream systems

The StreamProcessor polls a "hot folder" (data/streaming/incoming/) every
N seconds, simulating micro-batch ingestion without requiring Kafka in local mode.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class StreamEvent:
    """Represents a single streaming event."""

    def __init__(
        self,
        event_type: str,
        payload: dict,
        source_system: str,
        event_id: Optional[str] = None,
    ):
        self.event_id = event_id or uuid.uuid4().hex
        self.event_type = event_type
        self.payload = payload
        self.source_system = source_system
        self.received_at = datetime.now(timezone.utc).isoformat()
        self.processed = False
        self.processing_error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source_system": self.source_system,
            "payload": self.payload,
            "received_at": self.received_at,
            "processed": self.processed,
            "processing_error": self.processing_error,
        }


class StreamProcessor:
    """
    Micro-batch stream processor that watches a hot folder for incoming JSON events.
    Each batch is processed through the Silver transformation pipeline.
    
    Production note: Replace poll_interval logic with:
        PySpark: spark.readStream.format("delta") or kafka source
        Cloud:   AWS Kinesis / Azure Event Hub / GCP Pub/Sub
    """

    def __init__(
        self,
        incoming_dir: Path,
        processed_dir: Path,
        error_dir: Path,
        batch_size: int = 50,
        poll_interval_seconds: float = 5.0,
    ):
        self.incoming_dir = Path(incoming_dir)
        self.processed_dir = Path(processed_dir)
        self.error_dir = Path(error_dir)
        self.batch_size = batch_size
        self.poll_interval = poll_interval_seconds

        self.incoming_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.error_dir.mkdir(parents=True, exist_ok=True)

        self._handlers: dict[str, Callable] = {}
        self._running = False
        self._total_processed = 0
        self._total_errors = 0

    def register_handler(self, event_type: str, handler: Callable[[StreamEvent], None]):
        """Register a callback handler for a specific event type."""
        self._handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")

    def emit_event(self, event: StreamEvent) -> Path:
        """Write an event to the incoming hot folder for async processing."""
        path = self.incoming_dir / f"{event.event_id}.json"
        with open(path, "w") as f:
            json.dump(event.to_dict(), f, indent=2)
        return path

    def emit_transaction(self, transaction: dict, source: str = "billing") -> Path:
        """Helper to emit a billing transaction event."""
        return self.emit_event(StreamEvent(
            event_type="TRANSACTION",
            payload=transaction,
            source_system=source,
        ))

    def emit_customer_update(self, customer: dict, source: str = "crm") -> Path:
        """Helper to emit a CRM customer update event."""
        return self.emit_event(StreamEvent(
            event_type="CUSTOMER_UPDATE",
            payload=customer,
            source_system=source,
        ))

    def process_batch(self, max_events: Optional[int] = None) -> dict:
        """
        Process one micro-batch from the hot folder.
        
        Returns batch statistics dict.
        """
        files = sorted(self.incoming_dir.glob("*.json"))[: max_events or self.batch_size]
        batch_stats = {
            "batch_id": uuid.uuid4().hex[:8],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "files_found": len(files),
            "processed": 0,
            "errors": 0,
            "event_types": {},
        }

        events_batch: list[dict] = []

        for file in files:
            try:
                with open(file) as f:
                    data = json.load(f)

                event = StreamEvent(
                    event_type=data.get("event_type", "UNKNOWN"),
                    payload=data.get("payload", {}),
                    source_system=data.get("source_system", "unknown"),
                    event_id=data.get("event_id"),
                )

                # Route to handler
                handler = self._handlers.get(event.event_type)
                if handler:
                    handler(event)
                    event.processed = True
                else:
                    logger.debug(f"No handler for event type: {event.event_type}")
                    event.processed = True  # Mark as processed to avoid re-processing

                # Move to processed dir
                file.rename(self.processed_dir / file.name)
                batch_stats["processed"] += 1
                event_type = event.event_type
                batch_stats["event_types"][event_type] = batch_stats["event_types"].get(event_type, 0) + 1
                events_batch.append(event.to_dict())

            except Exception as e:
                logger.error(f"Error processing event file {file.name}: {e}")
                try:
                    file.rename(self.error_dir / file.name)
                except Exception:
                    pass
                batch_stats["errors"] += 1

        self._total_processed += batch_stats["processed"]
        self._total_errors += batch_stats["errors"]
        batch_stats["ended_at"] = datetime.now(timezone.utc).isoformat()

        if batch_stats["processed"] > 0:
            logger.info(
                f"Batch {batch_stats['batch_id']}: "
                f"processed={batch_stats['processed']}, errors={batch_stats['errors']}"
            )

        return batch_stats, events_batch

    def run_once(self) -> dict:
        """Process one batch and return stats. Useful for scheduled batch invocation."""
        stats, events = self.process_batch()
        return stats

    def run_continuous(self, duration_seconds: Optional[float] = None):
        """
        Run continuous micro-batch processing (blocking).
        
        Args:
            duration_seconds: Stop after this many seconds. None = run forever.
        """
        self._running = True
        start = time.time()
        logger.info(f"Stream processor started. Poll interval: {self.poll_interval}s")

        try:
            while self._running:
                self.process_batch()
                if duration_seconds and (time.time() - start) >= duration_seconds:
                    logger.info(f"Stream processor stopping after {duration_seconds}s")
                    break
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Stream processor interrupted by user")
        finally:
            self._running = False
            logger.info(
                f"Stream processor stopped. Total processed: {self._total_processed}, "
                f"errors: {self._total_errors}"
            )

    def stop(self):
        """Signal the continuous run loop to stop."""
        self._running = False

    def get_stats(self) -> dict:
        return {
            "total_processed": self._total_processed,
            "total_errors": self._total_errors,
            "is_running": self._running,
            "poll_interval_seconds": self.poll_interval,
        }


def generate_sample_stream_events(count: int = 20, seed: int = 42) -> list[StreamEvent]:
    """
    Generate sample streaming events for demo/testing purposes.
    Includes normal transactions and injected anomalies.
    """
    import random
    rng = random.Random(seed)
    statuses = ["completed", "pending", "failed", "refunded"]
    events = []

    for i in range(count):
        is_anomaly = rng.random() < 0.15

        if is_anomaly:
            # Anomalous transaction: GHOST customer or extreme amount
            tx = {
                "transaction_id": f"STR{uuid.uuid4().hex[:8].upper()}",
                "customer_id": f"GHOST{rng.randint(1000, 9999)}",
                "amount": rng.uniform(5000, 50000),
                "transaction_date": datetime.now(timezone.utc).date().isoformat(),
                "status": rng.choice(statuses),
                "_is_anomaly": True,
            }
        else:
            tx = {
                "transaction_id": f"STR{uuid.uuid4().hex[:8].upper()}",
                "customer_id": f"CRM{rng.randint(1, 10500):06d}",
                "amount": round(rng.uniform(10, 2000), 2),
                "transaction_date": datetime.now(timezone.utc).date().isoformat(),
                "status": rng.choice(statuses),
                "_is_anomaly": False,
            }

        events.append(StreamEvent(
            event_type="TRANSACTION",
            payload=tx,
            source_system="billing",
        ))

    return events
