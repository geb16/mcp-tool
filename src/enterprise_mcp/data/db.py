from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, String, UniqueConstraint, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from enterprise_mcp.config import settings


class Base(DeclarativeBase):
    pass


class OrderRow(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("tenant_id", "order_id", name="uq_orders_tenant_order"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    order_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32))
    tracking: Mapped[str | None] = mapped_column(String(128), nullable=True)
    refundable: Mapped[bool] = mapped_column(Boolean, default=False)
    amount_gbp: Mapped[float] = mapped_column(Float)


class RefundRequestRow(Base):
    __tablename__ = "refund_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    refund_request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    order_id: Mapped[str] = mapped_column(String(64), index=True)
    reason: Mapped[str] = mapped_column(String(512))
    approved_by_human: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


engine = create_engine(settings.database_url, echo=settings.db_echo_sql, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def session_scope() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database() -> None:
    Base.metadata.create_all(bind=engine)
    if not settings.seed_demo_data:
        return

    with session_scope() as session:
        existing = session.scalar(select(OrderRow.id).limit(1))
        if existing:
            return

        session.add_all(
            [
                OrderRow(
                    tenant_id=settings.default_tenant_id,
                    order_id="ORD-1001",
                    status="shipped",
                    tracking="TRK123456",
                    refundable=False,
                    amount_gbp=49.99,
                ),
                OrderRow(
                    tenant_id=settings.default_tenant_id,
                    order_id="ORD-1002",
                    status="delivered",
                    tracking="TRK999888",
                    refundable=True,
                    amount_gbp=129.00,
                ),
            ]
        )
