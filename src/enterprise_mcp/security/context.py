from enterprise_mcp.observability.context import get_request_context


def current_tenant_id(default: str) -> str:
    tenant_id = get_request_context().tenant_id
    return tenant_id or default


def current_role(default: str = "viewer") -> str:
    role = get_request_context().role
    return role or default
