# Casium - Document Field Extraction and Editing Interface

A modern React and FastAPI application for viewing and editing extracted document fields, with a focus on passport document validation. The application provides a clean, intuitive interface for managing document data with real-time validation and updates.

## Features

### Supported Document Types
- **Passport**
  - Full Name
  - Date of Birth
  - Country
  - Issue Date
  - Expiration Date

- **Driver's License**
  - License Number
  - First Name
  - Last Name
  - Date of Birth
  - Issue Date
  - Expiration Date

- **EAD Card**
  - Card Number
  - Category
  - Card Expires Date
  - First Name
  - Last Name

### Document Field Editing
- Interactive field editing interface with validation
- Real-time field updates
- Responsive UI with modern styling
- Automatic document type detection and display
- Support for multiple document types (passport, driver's license, EAD card)

### Field Validation Rules
- **Date Fields**
  - Date of Birth: Must be a valid date in YYYY-MM-DD format and in the past
  - Issue Date: Must be a valid date in YYYY-MM-DD format
  - Expiration Date: Must be a valid date in YYYY-MM-DD format and in the future

- **Name Fields**
  - Full Name: Must contain only letters, spaces, hyphens, and apostrophes
  - Minimum length of 2 characters

- **Country Field**
  - Must contain only letters, spaces, and hyphens
  - Minimum length of 2 characters

### UI Features
- Clean and intuitive interface
- Field-specific format hints
- Validation error messages
- Edit/Cancel toggle for each field
- Full-width save buttons
- Clear visual hierarchy with proper spacing and borders
- Responsive layout with consistent styling

## Technical Stack

### Frontend
- React with TypeScript
- Modern React Hooks (useState)
- Styled components using inline styles
- Type-safe field validation
- Document type-specific field handling

### Backend
- FastAPI (Python)
- Uvicorn server
- RESTful API endpoints for document operations
- SQLite database with SQLAlchemy ORM
- Google's Gemini AI for document classification and field extraction

## API Endpoints

- `GET /documents` - List all documents
- `GET /documents/{id}` - Fetch a specific document
- `PUT /update-field` - Update document field values
- `POST /classify-document` - Upload and classify a new document

## Getting Started

### Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize the database (first time setup)
python init_db.py

# Start the server
python -m uvicorn doc_classifier:app --reload
```
The server will be available at `http://127.0.0.1:8000`

### Environment Variables
Create a `.env` file in the root directory with:
```
GOOGLE_API_KEY=your_gemini_api_key_here
```

### Frontend Setup
```bash
# Navigate to frontend directory
cd doc-extraction-ui

# Install dependencies
npm install

# Start development server
npm start
```
The application will be available at `http://localhost:3000`

## Development

The application uses a component-based architecture with TypeScript for type safety. The main components include:

- `ExtractedFieldsPanel`: Main component for displaying and editing document fields
- Field validation system with customizable rules
- Real-time validation feedback
- Error handling and user feedback

## Contributing

When contributing to this project, please ensure that:
1. All new fields have appropriate validation rules
2. UI changes maintain the existing style guidelines
3. Type safety is maintained throughout the application
4. Changes are tested with the backend API

## License

This project is licensed under the MIT License - see the LICENSE file for details.