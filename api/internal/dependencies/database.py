from db.database import SessionLocal

def connect_to_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()