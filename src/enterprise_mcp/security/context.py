"""Security context accessors.

The helpers in this module read tenant and role values from the request-scoped
observability context.
"""

from enterprise_mcp.observability.context import get_request_context


def current_tenant_id(default: str) -> str:
    """Return current tenant ID or a provided default.

    Args:
        default: Fallback tenant identifier.

    Returns:
        Active tenant ID when present; otherwise ``default``.
    """
    tenant_id = get_request_context().tenant_id
    return tenant_id or default


def current_role(default: str = "viewer") -> str:
    """Return current request role or a fallback value.

    Args:
        default: Role used when context is empty.

    Returns:
        Active role string.
    """
    role = get_request_context().role
    return role or default
