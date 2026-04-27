"""Utilities for posting commands to the Divoom local device API."""

import requests
from .config import Config


def get_device_ip():
    """Return the configured device IP as a trimmed string."""
    return (Config.get_device_ip() or "").strip()


def post_device_command(payload, ip=None, timeout=8):
    """POST a JSON command payload to the device `/post` endpoint.

    Args:
        payload: Dict payload expected by the Divoom device API.
        ip: Optional explicit device IP. If omitted, reads from settings.
        timeout: Request timeout in seconds.

    Returns:
        requests.Response object.

    Raises:
        ValueError: If no device IP is available.
        requests.RequestException: If the network request fails.
    """
    device_ip = (ip or get_device_ip() or "").strip()
    if not device_ip:
        raise ValueError("No device IP configured.")
    return requests.post(f"http://{device_ip}/post", json=payload, timeout=timeout)
