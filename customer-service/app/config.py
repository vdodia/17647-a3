"""
config.py – Load all configuration from environment variables.
Never hard-code credentials here.
"""
import os


DB_HOST = os.environ.get("DATABASE_HOST", "db")
DB_PORT = int(os.environ.get("DATABASE_PORT", 3306))
DB_USER = os.environ.get("MYSQL_USER", "bookuser")
DB_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
DB_NAME = os.environ.get("MYSQL_DATABASE", "customers_db")

KAFKA_BROKERS = os.environ.get(
    "KAFKA_BROKERS",
    "98.88.99.206:9092,34.195.107.7:9092,54.221.160.63:9092",
).split(",")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "vdodia.customer.evt")
