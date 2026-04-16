"""Tool risk classification for approval workflows.

The sets in this module define which MCP tools are read-only and which tools
must be treated as sensitive write operations.
"""

DANGEROUS_TOOLS = {
    "create_refund_request",
}

READ_ONLY_TOOLS = {
    "get_order_status_tool",
    "get_return_policy_resource",
}


def is_dangerous_tool(tool_name: str) -> bool:
    """Return whether a tool is classified as dangerous.

    Args:
        tool_name: MCP tool identifier.

    Returns:
        ``True`` when the tool is in the dangerous tool set.
    """
    return tool_name in DANGEROUS_TOOLS


def is_read_only_tool(tool_name: str) -> bool:
    """Return whether a tool is classified as read-only.

    Args:
        tool_name: MCP tool identifier.

    Returns:
        ``True`` when the tool is in the read-only tool set.
    """
    return tool_name in READ_ONLY_TOOLS
