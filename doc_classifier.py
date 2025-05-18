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
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import logging
import google.generativeai as genai
import json
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from models import Base, Document, Field
from sqlalchemy.sql import text
from datetime import datetime
import re

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
        logger.info("Converting image for Gemini processing...")
        pil_img = Image.fromarray(img_array).convert("RGB")
        buffer = io.BytesIO()
        pil_img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()
        logger.info(f"Image converted, size: {len(image_bytes)} bytes")

        model = genai.GenerativeModel("gemini-1.5-flash")
        logger.info("Sending image to Gemini for classification...")
        
        classification_prompt = "You are an immigration document classifier. Only reply with one of: passport, driver_license, or ead_card."
        logger.info(f"Using classification prompt: {classification_prompt}")
        
        response = model.generate_content([
            classification_prompt,
            {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode('utf-8')}
        ])
        raw_response = response.text.strip()
        logger.info(f"Raw Gemini classification response: '{raw_response}'")
        
        document_type = raw_response.lower()
        final_type = document_type if document_type in DOCUMENT_TYPES else "unknown"
        logger.info(f"Final document type determined: '{final_type}' (original response: '{raw_response}')")
        
        return final_type
    except Exception as e:
        logger.error(f"Document classification error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Document classification failed: {str(e)}")

def extract_fields_with_gemini(img_array: np.ndarray, doc_type: str) -> Dict[str, Any]:
    try:
        logger.info(f"Starting field extraction for document type: {doc_type}")
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
        logger.info(f"Using prompt for document type '{doc_type}': {prompt}")

        logger.info("Sending image to Gemini for field extraction...")
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode('utf-8')}
        ])
        text = response.text.strip()
        logger.info(f"Raw Gemini field extraction response: {text}")

        try:
            parsed_json = json.loads(text)
            logger.info(f"Successfully parsed JSON response: {json.dumps(parsed_json, indent=2)}")
            return parsed_json
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Raw text that failed to parse: {text}")
            return {"raw_output": text}
    except Exception as e:
        logger.error(f"Field extraction error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Field extraction failed: {str(e)}")

def convert_date_to_standard_format(date_str: str) -> str:
    """Convert various date formats to YYYY-MM-DD."""
    try:
        # Try parsing with various formats
        for fmt in [
            "%d %b %Y",  # 03 Oct 1955
            "%b %d %Y",  # Oct 03 1955
            "%Y-%m-%d",  # Already in correct format
            "%m/%d/%Y",  # 10/03/1955
            "%d/%m/%Y",  # 03/10/1955
        ]:
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return date_str  # Return original if no format matches
    except Exception:
        return date_str  # Return original on any error

@app.post("/classify-document", response_model=Dict[str, Any])
async def classify_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        logger.info(f"Starting document classification for file: {file.filename}")
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

        logger.info("Starting Gemini document classification...")
        doc_type = process_image_with_gemini(img_array)
        logger.info(f"Document classified as type: '{doc_type}'")
        
        fields = extract_fields_with_gemini(img_array, doc_type)
        logger.info("Fields extracted successfully")

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

        # Convert dates to standard format
        date_fields = ["date_of_birth", "issue_date", "expiration_date", "card_expires_date"]
        for field in date_fields:
            if field in field_data and field_data[field]:
                field_data[field] = convert_date_to_standard_format(field_data[field])

        logger.info(f"Creating document record with type: '{doc_type}'")
        doc_record = Document(
            filename=file.filename,
            content_type=file.content_type,
            file_blob=file_bytes,
            document_type=doc_type
        )
        
        # Explicitly set document type again to ensure it's set
        doc_record.document_type = doc_type
        
        logger.info("About to add document to database session")
        db.add(doc_record)
        logger.info("About to commit database transaction")
        try:
            db.commit()
            logger.info(f"Database commit complete. Document ID: {doc_record.id}, Type: '{doc_record.document_type}'")
            
            # Verify the document was saved with correct type
            db.refresh(doc_record)
            saved_doc = db.query(Document).filter(Document.id == doc_record.id).first()
            if saved_doc.document_type != doc_type:
                logger.error(f"Document type mismatch - Expected: '{doc_type}', Got: '{saved_doc.document_type}'")
                # Force update if needed
                db.execute(
                    text("UPDATE documents SET document_type = :type WHERE id = :id"),
                    {"type": doc_type, "id": doc_record.id}
                )
                db.commit()
                logger.info("Forced document type update complete")
            else:
                logger.info(f"Document type verified correct in database: '{saved_doc.document_type}'")
        except Exception as e:
            logger.error(f"Error during database commit: {str(e)}")
            db.rollback()
            raise

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

# Add validation rules
FIELD_VALIDATIONS = {
    "date_of_birth": {
        "pattern": r"^\d{4}-\d{2}-\d{2}$",
        "validate": lambda value: bool(re.match(r"^\d{4}-\d{2}-\d{2}$", value)) and 
                                datetime.strptime(value, "%Y-%m-%d") < datetime.now()
    },
    "issue_date": {
        "pattern": r"^\d{4}-\d{2}-\d{2}$",
        "validate": lambda value: bool(re.match(r"^\d{4}-\d{2}-\d{2}$", value))
    },
    "expiration_date": {
        "pattern": r"^\d{4}-\d{2}-\d{2}$",
        "validate": lambda value: bool(re.match(r"^\d{4}-\d{2}-\d{2}$", value)) and 
                                datetime.strptime(value, "%Y-%m-%d") > datetime.now()
    },
    "full_name": {
        "pattern": r"^[A-Za-z\s\-']+$",
        "validate": lambda value: bool(re.match(r"^[A-Za-z\s\-']+$", value)) and len(value.strip()) >= 2
    },
    "country": {
        "pattern": r"^[A-Za-z\s\-']+$",
        "validate": lambda value: bool(re.match(r"^[A-Za-z\s\-']+$", value)) and len(value.strip()) >= 2
    }
}

def validate_field_value(key: str, value: str) -> tuple[bool, Optional[str]]:
    """Validate a field value based on its key."""
    if key not in FIELD_VALIDATIONS:
        return True, None
    
    validation = FIELD_VALIDATIONS[key]
    try:
        if validation["validate"](value):
            return True, None
        
        if "date" in key:
            return False, f"Invalid date format. Must be YYYY-MM-DD"
        return False, f"Invalid format for {key}"
    except ValueError as e:
        return False, str(e)

@app.put("/update-field")
def update_field(data: FieldUpdateRequest, db: Session = Depends(get_db)):
    # Validate the field value
    is_valid, error_message = validate_field_value(data.key, data.value)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)
    
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

    try:
        db.commit()
        return {"message": "Field updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update field: {str(e)}")


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
    document_type: Optional[str]
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
