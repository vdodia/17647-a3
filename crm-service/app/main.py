"""
main.py – CRM service: Kafka consumer that sends welcome emails to new customers.

Uses AWS SES for email delivery. The EKS node's IAM role (LabRole) provides
credentials automatically via the instance metadata service -- no secrets needed.
"""
import json
import logging

import boto3
from kafka import KafkaConsumer
from app import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ses_client = boto3.client("ses", region_name=config.AWS_REGION)


def send_email(to_address: str, subject: str, body: str) -> None:
    ses_client.send_email(
        Source=config.SES_SENDER,
        Destination={"ToAddresses": [to_address]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": body}},
        },
    )
    logger.info("Email sent via SES to %s", to_address)


def handle_customer_event(message_value: dict) -> None:
    customer_name = message_value.get("name", "Customer")
    customer_email = message_value.get("userId")

    if not customer_email:
        logger.warning("Customer event missing userId (email); skipping")
        return

    subject = "Activate your book store account"
    body = (
        f"Dear {customer_name},\n"
        f"Welcome to the Book store created by {config.ANDREW_ID}.\n"
        "Exceptionally this time we won't ask you to click a link to activate your account."
    )

    try:
        send_email(customer_email, subject, body)
    except Exception:
        logger.exception("Failed to send email to %s", customer_email)


def main() -> None:
    logger.info(
        "CRM service starting – consuming from topic '%s' on brokers %s",
        config.KAFKA_TOPIC,
        config.KAFKA_BROKERS,
    )

    consumer = KafkaConsumer(
        config.KAFKA_TOPIC,
        bootstrap_servers=config.KAFKA_BROKERS,
        group_id=config.KAFKA_GROUP_ID,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    logger.info("CRM consumer connected, waiting for messages...")
    for message in consumer:
        logger.info("Received customer event: %s", message.value)
        handle_customer_event(message.value)


if __name__ == "__main__":
    main()
