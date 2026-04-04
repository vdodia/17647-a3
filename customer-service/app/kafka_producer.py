"""
kafka_producer.py – Publishes customer-registered events to Kafka.
"""
import json
import logging
from kafka import KafkaProducer
from app import config

logger = logging.getLogger(__name__)

_producer = None


def _get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=config.KAFKA_BROKERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=3,
        )
    return _producer


def publish_customer_event(customer_data: dict) -> None:
    """Fire-and-forget publish of a customer-registered domain event."""
    try:
        producer = _get_producer()
        producer.send(config.KAFKA_TOPIC, value=customer_data)
        producer.flush(timeout=5)
        logger.info("Published customer event for userId=%s", customer_data.get("userId"))
    except Exception:
        logger.exception("Failed to publish customer event to Kafka")
