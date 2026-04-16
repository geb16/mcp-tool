from starlette.responses import PlainTextResponse, Response
import uvicorn

from enterprise_mcp.config import settings
from enterprise_mcp.data.db import init_database
from enterprise_mcp.logging import configure_logging
from enterprise_mcp.mcp.common import mcp
from enterprise_mcp.observability.metrics import metrics_response
from enterprise_mcp.portal.http import (
    admin_decide_approval_api,
    admin_page,
    admin_set_role_api,
    admin_state_api,
    customer_chat_api,
    customer_history_api,
    customer_page,
)
from enterprise_mcp.security.middleware import RequestSecurityMiddleware
from enterprise_mcp.trainer.http import trainer_chat, trainer_direct_tool, trainer_page, trainer_state


async def healthz(_request) -> PlainTextResponse:
    return PlainTextResponse("ok")


async def metrics(_request) -> Response:
    payload, content_type = metrics_response()
    return Response(content=payload, media_type=content_type)


def build_http_app():
    app = mcp.streamable_http_app()
    app.add_route("/healthz", healthz, methods=["GET"])
    app.add_route("/metrics", metrics, methods=["GET"])
    app.add_route("/trainer", trainer_page, methods=["GET"])
    app.add_route("/trainer/api/chat", trainer_chat, methods=["POST"])
    app.add_route("/trainer/api/direct-tool", trainer_direct_tool, methods=["POST"])
    app.add_route("/trainer/api/state", trainer_state, methods=["GET"])
    app.add_route("/portal/chat", customer_page, methods=["GET"])
    app.add_route("/portal/admin", admin_page, methods=["GET"])
    app.add_route("/portal/api/customer/chat", customer_chat_api, methods=["POST"])
    app.add_route("/portal/api/customer/history", customer_history_api, methods=["GET"])
    app.add_route("/portal/api/admin/state", admin_state_api, methods=["GET"])
    app.add_route("/portal/api/admin/agent-role", admin_set_role_api, methods=["POST"])
    app.add_route("/portal/api/admin/approvals/{approval_id}/decision", admin_decide_approval_api, methods=["POST"])
    app.add_middleware(RequestSecurityMiddleware)
    return app


if __name__ == "__main__":
    configure_logging()
    init_database()
    uvicorn.run(
        build_http_app(),
        host=settings.mcp_http_host,
        port=settings.mcp_http_port,
        log_level=settings.log_level.lower(),
    )
