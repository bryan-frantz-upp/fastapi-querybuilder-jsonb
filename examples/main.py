from fastapi import FastAPI, Depends
from sqlalchemy import String, ForeignKey, create_engine
from sqlalchemy.orm import relationship, sessionmaker, Session, declarative_base
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi_filter_sort.dependencies import QueryBuilder
import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

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
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    # deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

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
            User(name="Alice", email="alice@example.com", role=admin),
            User(name="Bob", email="bob@example.com", role=user),
            User(name="Carol", email="carol@example.com", role=manager),
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
