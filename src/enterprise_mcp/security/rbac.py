from enterprise_mcp.config import settings
from enterprise_mcp.security.context import current_role


class AuthorizationError(PermissionError):
    pass


def ensure_tool_access(*, tool_name: str, write: bool) -> None:
    role = current_role()
    if write:
        if role not in settings.write_roles:
            raise AuthorizationError(f"Role '{role}' cannot execute write tool '{tool_name}'.")
        return

    if role not in settings.read_roles:
        raise AuthorizationError(f"Role '{role}' cannot execute read tool '{tool_name}'.")
