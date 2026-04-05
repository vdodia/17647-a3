"""
config.py – CRM service configuration from environment variables.
"""
import os

KAFKA_BROKERS = os.environ.get(
    "KAFKA_BROKERS",
    "98.88.99.206:9092,34.195.107.7:9092,54.221.160.63:9092",
).split(",")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "vdodia.customer.evt")
KAFKA_GROUP_ID = os.environ.get("KAFKA_GROUP_ID", "vdodia-crm-group")

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

ANDREW_ID = os.environ.get("ANDREW_ID", "vdodia")
