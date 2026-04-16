"""Prometheus metrics and instrumentation helpers.

Defines counters/histograms used across HTTP transport, tools, cache events,
and rate-limiting decisions.
"""

import time
from contextlib import contextmanager

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

HTTP_REQUEST_COUNT = Counter(
    "mcp_http_requests_total",
    "Total HTTP requests received by the MCP service.",
    ["method", "path", "status"],
)

HTTP_REQUEST_LATENCY = Histogram(
    "mcp_http_request_latency_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
)

TOOL_CALL_COUNT = Counter(
    "mcp_tool_calls_total",
    "Total tool invocations.",
    ["tool", "status"],
)

TOOL_CALL_LATENCY = Histogram(
    "mcp_tool_call_latency_seconds",
    "Tool latency in seconds.",
    ["tool"],
)

CACHE_EVENTS = Counter(
    "mcp_cache_events_total",
    "Cache hit/miss events.",
    ["tool", "event"],
)

RATE_LIMIT_EVENTS = Counter(
    "mcp_rate_limit_events_total",
    "Rate limiting events.",
    ["result"],
)

@contextmanager
def track_tool_latency(tool_name: str):
    """Measure and publish tool call latency.

    Args:
        tool_name: Tool identifier used for histogram label.
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        TOOL_CALL_LATENCY.labels(tool=tool_name).observe(time.perf_counter() - start)


def metrics_response() -> tuple[bytes, str]:
    """Build HTTP response payload for Prometheus scraping.

    Returns:
        Tuple of encoded metrics payload and content-type header value.
    """
    return generate_latest(), CONTENT_TYPE_LATEST
