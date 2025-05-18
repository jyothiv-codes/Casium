from sqlalchemy import create_engine
from models import Base

# Create database engine
DATABASE_URL = "sqlite:///./documents.db"
engine = create_engine(DATABASE_URL)

def init_db():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully with all tables and columns.")

if __name__ == "__main__":
    init_db() 