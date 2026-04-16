"""Example OpenAI Responses client for MCP integration testing.

The script demonstrates model-to-MCP tool invocation and explicit approval
handling for sensitive tool calls.
"""

import json

from openai import OpenAI

from enterprise_mcp.config import settings

MODEL = "gpt-5"

client = OpenAI(api_key=settings.openai_api_key)


def ask_agent(user_text: str) -> None:
    """Run one agent turn against local MCP tools.

    Args:
        user_text: End-user prompt sent to the model.
    """
    response = client.responses.create(
        model=MODEL,
        input=user_text,
        tools=[
            {
                "type": "mcp",
                "server_label": "support_tools",
                "server_url": f"http://localhost:{settings.mcp_http_port}/mcp",
                "headers": {
                    "x-api-key": settings.primary_api_key,
                    "x-tenant-id": settings.default_tenant_id,
                    "x-role": "support_manager",
                },
                "allowed_tools": [
                    "get_order_status_tool",
                    "create_refund_request",
                ],
                "require_approval": {
                    "always": {"tool_names": ["create_refund_request"]},
                    "never": {"tool_names": ["get_order_status_tool"]},
                },
            }
        ],
    )

    pending_approval_id = None

    for item in response.output:
        item_type = getattr(item, "type", None)

        if item_type == "mcp_call" and getattr(item, "approval_request_id", None):
            pending_approval_id = item.approval_request_id
            print("Approval required for MCP tool call.")
            print(f"Tool: {item.name}")
            print(f"Arguments: {json.dumps(item.arguments)}")

    if pending_approval_id:
        decision = input("Approve tool call? [y/N]: ").strip().lower() == "y"

        approved_response = client.responses.create(
            model=MODEL,
            previous_response_id=response.id,
            input=[
                {
                    "type": "mcp_approval_response",
                    "approval_request_id": pending_approval_id,
                    "approve": decision,
                    "reason": "Approved by operator" if decision else "Rejected by operator",
                }
            ],
        )
        print(approved_response.output_text)
    else:
        print(response.output_text)


if __name__ == "__main__":
    ask_agent(
        "Customer wants a refund for order ORD-1002 because the wrong item arrived. "
        "Check eligibility and proceed if allowed."
    )
