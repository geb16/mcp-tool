DANGEROUS_TOOLS = {
    "create_refund_request",
}

READ_ONLY_TOOLS = {
    "get_order_status_tool",
    "get_return_policy_resource",
}


def is_dangerous_tool(tool_name: str) -> bool:
    return tool_name in DANGEROUS_TOOLS


def is_read_only_tool(tool_name: str) -> bool:
    return tool_name in READ_ONLY_TOOLS
