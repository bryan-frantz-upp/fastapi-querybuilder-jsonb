from fastapi import FastAPI, Depends
from sqlalchemy import String, ForeignKey, create_engine
from sqlalchemy.orm import relationship, sessionmaker, Session, declarative_base
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi_filter_sort.dependencies import QueryBuilder
import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from enum import Enum

# ───── App & DB Setup ───────────────────────────

DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ───── Models ────────────────────────────────────

class StatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    age: Mapped[int] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    status: Mapped[StatusEnum] = mapped_column(String, default=StatusEnum.ACTIVE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(datetime.timezone.utc))

    role: Mapped["Role"] = relationship("Role", back_populates="users")

    role = relationship("Role", back_populates="users", lazy="selectin")


# ───── Lifespan / Seed Data ─────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Seed roles and users (sync mode)
    db = Session(bind=engine)

    if not db.query(Role).first():
        admin = Role(name="admin")
        user = Role(name="user")
        manager = Role(name="manager")
        db.add_all([admin, user, manager])
        db.commit()

        # Seed users with mapped roles
        db.add_all([
            User(name="Alice", email="alice@example.com", role=admin, status=StatusEnum.ACTIVE, age=30, is_active=True),
            User(name="Bob", email="bob@example.com", role=user, status=StatusEnum.INACTIVE, age=25, is_active=False),
            User(name="Carol", email="carol@example.com", role=manager, status=StatusEnum.SUSPENDED, age=40, is_active=False),
            User(name="Dave", email="dave@example.com", role=admin, status=StatusEnum.ACTIVE, age=35, is_active=True),
            User(name="Eve", email="eve@example.com", role=user, status=StatusEnum.ACTIVE, age=28, is_active=True),
        ])
        db.commit()

    db.close()
    yield


# ───── FastAPI App ───────────────────────────────

app = FastAPI(lifespan=lifespan)


@app.get("/users")
def get_users(query = QueryBuilder(User), session: AsyncSession = Depends(get_db),):
    data  = session.execute(query).scalars().all()
    return data


# ───── Run Server ────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
