from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Depends
import sqlalchemy
from fastapi_querybuilder_jsonb.dependencies import QueryBuilder
from fastapi_pagination import Page, add_pagination
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import String, ForeignKey, select, JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column, relationship, declarative_base
import uvicorn

from examples.schemas import StatusEnum, UserResponse

# ───── App & DB Setup ───────────────────────────

DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


async def get_db():
    async with SessionLocal() as session:
        yield session


# ───── Models ────────────────────────────────────

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
    status: Mapped[StatusEnum] = mapped_column(
        sqlalchemy.Enum(StatusEnum), 
        default=StatusEnum.ACTIVE, 
        nullable=False
    )
    attributes: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    role: Mapped["Role"] = relationship("Role", back_populates="users", lazy="selectin")


# ───── Lifespan / Seed Data ─────────────────────

@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        result = await session.execute(select(Role))
        if not result.scalars().first():
            admin = Role(name="admin")
            user = Role(name="user")
            manager = Role(name="manager")
            session.add_all([admin, user, manager])
            await session.commit()

            session.add_all([
                User(name="Alice", email="alice@example.com", role=admin,
                     status=StatusEnum.ACTIVE, age=30, is_active=True,
                     attributes={"hair": "Brown", "score": 85, "city": "NYC"}),
                User(name="Bob", email="bob@example.com", role=user,
                     status=StatusEnum.INACTIVE, age=25, is_active=False,
                     attributes={"hair": "Blonde", "score": 70, "city": "LA"}),
                User(name="Carol", email="carol@example.com", role=manager,
                     status=StatusEnum.SUSPENDED, age=40, is_active=False,
                     attributes={"hair": "Black", "score": 95, "city": "Chicago"}),
                User(name="Dave", email="dave@example.com", role=admin,
                     status=StatusEnum.ACTIVE, age=35, is_active=True,
                     attributes={"hair": "Brown", "score": 88, "city": "Boston"}),
                User(name="Eve", email="eve@example.com", role=user,
                     status=StatusEnum.ACTIVE, age=28, is_active=True,
                     attributes={"hair": "Red", "score": 92, "city": "Seattle"}),
            ])
            await session.commit()

    yield

# ───── FastAPI App ───────────────────────────────

app = FastAPI(lifespan=lifespan)


@app.get("/users")
async def get_users(query=QueryBuilder(User), session: AsyncSession = Depends(get_db)):
    result = await session.execute(query)
    return result.scalars().all()


@app.get("/users/paginated", response_model=Page[UserResponse])
async def get_users_paginated(query=QueryBuilder(User), session: AsyncSession = Depends(get_db)):
    return await paginate(session, query)


# ───── Example Endpoints for $path_* Operators ──────

@app.get("/users/path-examples")
async def get_users_path_examples(session: AsyncSession = Depends(get_db)):
    """
    Examples of using $path_* operators on JSON columns:

    1. $path_eq: Find users with attributes.hair == "Brown"
       GET /users?attributes=$path_eq:{"hair":"Brown"}

    2. $path_in: Find users with attributes.hair in ["Brown", "Blonde"]
       GET /users?attributes=$path_in:{"path":"hair","values":["Brown","Blonde"]}

    3. $path_gt: Find users with attributes.score > 85
       GET /users?attributes=$path_gt:{"path":"score","value":85}

    4. $path_gte: Find users with attributes.score >= 85
       GET /users?attributes=$path_gte:{"path":"score","value":85}

    5. $path_lt: Find users with attributes.score < 90
       GET /users?attributes=$path_lt:{"path":"score","value":90}

    6. $path_lte: Find users with attributes.score <= 90
       GET /users?attributes=$path_lte:{"path":"score","value":90}
    """
    return {
        "message": "Use QueryBuilder with the query parameters shown in the docstring",
        "examples": [
            {"description": "Users with brown hair", "query": "?attributes=$path_eq:{\"hair\":\"Brown\"}"},
            {"description": "Users with brown or blonde hair", "query": "?attributes=$path_in:{\"path\":\"hair\",\"values\":[\"Brown\",\"Blonde\"]}"},
            {"description": "Users with score > 85", "query": "?attributes=$path_gt:{\"path\":\"score\",\"value\":85}"},
            {"description": "Users with score >= 85", "query": "?attributes=$path_gte:{\"path\":\"score\",\"value\":85}"},
            {"description": "Users with score < 90", "query": "?attributes=$path_lt:{\"path\":\"score\",\"value\":90}"},
            {"description": "Users with score <= 90", "query": "?attributes=$path_lte:{\"path\":\"score\",\"value\":90}"},
        ]
    }


add_pagination(app)

# ───── Run Server ────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
