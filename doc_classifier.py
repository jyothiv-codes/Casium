from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import io
import base64
from PIL import Image
import pdf2image
import tempfile
import numpy as np
from typing import List, Dict, Any
from dotenv import load_dotenv
import logging
import google.generativeai as genai
import json
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from models import Base, Document, Field

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize FastAPI app
app = FastAPI(title="Immigration Document Classifier")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = "sqlite:///./documents.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DOCUMENT_TYPES = ["passport", "driver_license", "ead_card"]

passport_prompt = """Extract the fields from the passport image and return them in the following JSON format:
{
  "document_type": "passport",
  "document_content": {
    "full_name": "...",
    "date_of_birth": "...",
    "country": "...",
    "issue_date": "...",
    "expiration_date": "..."
  }
}"""

driver_license_prompt = """Extract the fields from the driver's license image and return them in the following JSON format:
{
  "document_type": "driver_license",
  "document_content": {
    "license_number": "...",
    "first_name": "...",
    "last_name": "...",
    "date_of_birth": "...",
    "issue_date": "...",
    "expiration_date": "..."
  }
}"""

ead_card_prompt = """Extract the fields from the image and return them in the following JSON format:
{
  "document_type": "ead_card",
  "document_content": {
    "card_number": "...",
    "category": "...",
    "card_expires_date": "...",
    "first_name": "...",
    "last_name": "..."
  }
}"""

def extract_images_from_pdf(pdf_bytes: bytes) -> List[np.ndarray]:
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf.write(pdf_bytes)
            temp_pdf_path = temp_pdf.name
        images = pdf2image.convert_from_path(temp_pdf_path)
        os.unlink(temp_pdf_path)
        return [np.array(img) for img in images]
    except Exception as e:
        logger.error(f"PDF extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

def process_image_with_gemini(img_array: np.ndarray) -> str:
    try:
        pil_img = Image.fromarray(img_array).convert("RGB")
        buffer = io.BytesIO()
        pil_img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([
            "You are an immigration document classifier. Only reply with one of: passport, driver_license, or ead_card.",
            {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode('utf-8')}
        ])
        document_type = response.text.strip().lower()
        logger.info(f"Gemini response: {document_type}")
        return document_type if document_type in DOCUMENT_TYPES else "unknown"
    except Exception as e:
        logger.error(f"Gemini classification error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document classification failed: {str(e)}")

def extract_fields_with_gemini(img_array: np.ndarray, doc_type: str) -> Dict[str, Any]:
    try:
        pil_img = Image.fromarray(img_array).convert("RGB")
        buffer = io.BytesIO()
        pil_img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()

        model = genai.GenerativeModel("gemini-1.5-flash")

        prompts = {
            "passport": passport_prompt,
            "driver_license": driver_license_prompt,
            "ead_card": ead_card_prompt
        }

        prompt = prompts.get(doc_type, "Extract key fields as JSON.")

        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode('utf-8')}
        ])
        text = response.text.strip()
        logger.info(f"Gemini field response: {text}")

        try:
            return json.loads(text)
        except Exception:
            return {"raw_output": text}
    except Exception as e:
        logger.error(f"Gemini field extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Field extraction failed: {str(e)}")

@app.post("/classify-document", response_model=Dict[str, Any])
async def classify_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        file_content = await file.read()
        file_bytes = bytes(file_content)
        file_extension = os.path.splitext(file.filename)[1].lower()

        if file_extension == ".pdf":
            images = extract_images_from_pdf(file_content)
            if not images:
                raise HTTPException(status_code=400, detail="Could not extract images from PDF")
            img_array = images[0]
        else:
            try:
                image = Image.open(io.BytesIO(file_content))
                img_array = np.array(image)
            except Exception as e:
                logger.exception("Image file error")
                raise HTTPException(status_code=400, detail=f"Invalid image file: {repr(e)}")

        doc_type = process_image_with_gemini(img_array)
        fields = extract_fields_with_gemini(img_array, doc_type)

        field_data = {}
        raw_json_output = ""

        if "raw_output" in fields:
            raw_json_output = fields["raw_output"]
            try:
                cleaned = raw_json_output.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(cleaned)
                field_data = parsed.get("document_content", parsed)
            except Exception as e:
                logger.error("Failed to parse raw_output:", exc_info=e)
                field_data = {}
        else:
            field_data = fields.get("document_content", fields)

        doc_record = Document(
            filename=file.filename,
            content_type=file.content_type,
            file_blob=file_bytes
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)

        for key, value in field_data.items():
            if value is not None:
                db.add(Field(
                    document_id=doc_record.id,
                    key=key,
                    value=str(value)
                ))

        if raw_json_output and not field_data:
            db.add(Field(
                document_id=doc_record.id,
                key="raw_output",
                value=raw_json_output
            ))

        db.commit()

        return {
            "document_id": doc_record.id,
            "document_type": doc_type,
            "fields": field_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


from pydantic import BaseModel

class FieldUpdateRequest(BaseModel):
    document_id: int
    key: str
    value: str
@app.put("/update-field")
def update_field(data: FieldUpdateRequest, db: Session = Depends(get_db)):
    field = db.query(Field).filter_by(document_id=data.document_id, key=data.key).first()
    
    if field:
        field.value = data.value
        field.is_corrected = 1
    else:
        # Create new field if it doesn't exist
        field = Field(
            document_id=data.document_id,
            key=data.key,
            value=data.value,
            is_corrected=1
        )
        db.add(field)

    db.commit()
    return {"message": "Field updated successfully"}


from fastapi import Query
from pydantic import BaseModel
from typing import List, Optional

class FieldOut(BaseModel):
    key: str
    value: str

class DocumentOut(BaseModel):
    id: int
    filename: str
    content_type: Optional[str]
    fields: List[FieldOut] = []

    class Config:
        orm_mode = True

@app.get("/documents", response_model=List[DocumentOut])
def get_documents(db: Session = Depends(get_db), limit: int = Query(5, ge=1, le=100)):
    documents = db.query(Document).order_by(Document.id.desc()).limit(limit).all()

    # For each document, load its fields
    for doc in documents:
        # Eager load fields for each document
        doc.fields = db.query(Field).filter(Field.document_id == doc.id).all()
    return documents

@app.get("/documents/{document_id}")
def get_document(document_id: int, db: Session = Depends(get_db)):
    try:
        logger.info(f"Attempting to fetch document {document_id}")
        
        # Query the document
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            logger.error(f"Document {document_id} not found in database")
            raise HTTPException(status_code=404, detail="Document not found")
        
        logger.info(f"Found document: id={document.id}, filename={document.filename}, content_type={document.content_type}")
        
        if not document.file_blob:
            logger.error(f"Document {document_id} has no file blob")
            raise HTTPException(status_code=404, detail="Document content not found")
        
        logger.info(f"Document {document_id} blob size: {len(document.file_blob)} bytes")

        # Return the file blob with the correct content type
        return Response(
            content=document.file_blob,
            media_type=document.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'inline; filename="{document.filename}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving document")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("doc_classifier:app", host="0.0.0.0", port=8000, reload=True)
