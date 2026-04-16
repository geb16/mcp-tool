"""Role-based authorization checks.

Enforces role permissions for read and write MCP tool invocations.
"""

from enterprise_mcp.config import settings
from enterprise_mcp.security.context import current_role


class AuthorizationError(PermissionError):
    """Raised when a role is not authorized for the requested tool action."""

    pass


def ensure_tool_access(*, tool_name: str, write: bool) -> None:
    """Validate role access for a tool invocation.

    Args:
        tool_name: Tool identifier.
        write: ``True`` for write tools, ``False`` for read tools/resources.

    Raises:
        AuthorizationError: If the current role is not authorized.
    """
    role = current_role()
    if write:
        if role not in settings.write_roles:
            raise AuthorizationError(f"Role '{role}' cannot execute write tool '{tool_name}'.")
        return

    if role not in settings.read_roles:
        raise AuthorizationError(f"Role '{role}' cannot execute read tool '{tool_name}'.")
