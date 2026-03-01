from typing import Generator

from app.core import database


def get_session() -> Generator:
    session = database.SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
