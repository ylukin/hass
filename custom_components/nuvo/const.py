"""Constants for the Nuvo Multi-Zone Amplifier integration."""

DOMAIN = "nuvo"

# Configuration keys
CONF_NAME = "name"  # Device name
CONF_ZONES = "zones"
CONF_SOURCES = "sources"

# Zone and source IDs (1-6 for E6G)
ZONE_IDS = [1, 2, 3, 4, 5, 6]
SOURCE_IDS = [1, 2, 3, 4, 5, 6]

# Services
SERVICE_SNAPSHOT = "snapshot"
SERVICE_RESTORE = "restore"

# Defaults
DEFAULT_PORT = 4999
DEFAULT_NAME = "Nuvo E6G"

# Data keys
NUVO_CONNECTION = "connection"
