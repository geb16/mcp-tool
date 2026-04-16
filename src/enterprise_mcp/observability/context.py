from contextvars import ContextVar
from dataclasses import dataclass

request_id_var: ContextVar[str] = ContextVar("request_id", default="")
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="")
role_var: ContextVar[str] = ContextVar("role", default="")
principal_var: ContextVar[str] = ContextVar("principal", default="")


@dataclass(slots=True) 
class RequestContext:
    request_id: str
    trace_id: str
    tenant_id: str
    role: str
    principal: str


def get_request_context() -> RequestContext:
    return RequestContext(
        request_id=request_id_var.get(),
        trace_id=trace_id_var.get(),
        tenant_id=tenant_id_var.get(),
        role=role_var.get(),
        principal=principal_var.get(),
    )


def clear_request_context() -> None: # This can be called at the end of request processing to ensure no context leaks between requests in async environments. 
    request_id_var.set("")
    trace_id_var.set("")
    tenant_id_var.set("")
    role_var.set("")
    principal_var.set("")
