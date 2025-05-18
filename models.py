from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, LargeBinary, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow)
    file_blob = Column(LargeBinary, nullable=False)

    fields = relationship("Field", back_populates="document", cascade="all, delete-orphan")

class Field(Base):
    __tablename__ = "fields"

    document_id = Column(Integer, ForeignKey("documents.id"), primary_key=True)
    key = Column(String, primary_key=True)
    value = Column(Text)
    is_corrected = Column(Integer, default=0)
    updated_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("Document", back_populates="fields") 