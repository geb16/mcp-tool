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

# what is @contextmanager?
# Anwer: @contextmanager is a decorator in Python that allows you to define a context manager using a generator function. 
# context manager is an object that defines the runtime context to be established when executing a with statement. 
# The @contextmanager decorator simplifies the process of creating context managers by allowing you to write setup and 
# teardown code in a single function, using yield to separate the two phases. When the with block is entered, the code 
# before yield is executed (setup), and when the block is exited, the code after yield is executed (teardown), even 
# if an exception occurs.

@contextmanager 
def track_tool_latency(tool_name: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        TOOL_CALL_LATENCY.labels(tool=tool_name).observe(time.perf_counter() - start)


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
