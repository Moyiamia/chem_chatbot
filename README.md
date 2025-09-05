# Chemistry Student Information Assistant

## System Overview

This system implements a document-based question-answering platform designed for chemistry postgraduate students at Durham University. The system enables natural language queries of departmental administrative information through an intelligent PDF processing and retrieval pipeline.

## System Architecture

The system follows a two-stage architecture:

**Document Processing (Admin):**
- PDF upload through Streamlit admin panel
- Text extraction using PyPDF with OCR fallback (Tesseract)
- Text chunking and embedding generation using SentenceTransformer (MiniLM)
- Vector indexing with FAISS (IndexFlatL2)

**QA Inference (Student):**
- User question input via Streamlit interface
- Top-K retrieval from FAISS using the same embedding model
- Answer generation through Gemini API
- Markdown rendering with source linking

## Technology Stack

- **Frontend Framework**: Streamlit
- **Language Model**: Google Gemini 2.5 Flash Lite
- **Vector Database**: FAISS (Facebook AI Similarity Search)
- **Text Embeddings**: HuggingFace all-MiniLM-L6-v2
- **PDF Processing**: pypdf with Tesseract OCR fallback
- **Programming Language**: Python 3.8+

## Installation Requirements

### Software Dependencies
- Python 3.8 or higher
- Google Gemini API key
- Tesseract OCR (optional for image-based PDFs)

### Hardware Specifications
- Minimum 8GB RAM
- 2GB available storage
- Internet connectivity for API calls

## Setup Instructions

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Environment Configuration
Copy the environment template and configure API credentials:
```bash
cp .env.example .env
```

Edit `.env` file:
```
GOOGLE_API_KEY=your_gemini_api_key
ADMIN_PASS=123456
INDEX_DIR=vector_dbs_all
PDF_DIR=pdfs
```

Obtain Google Gemini API key from: https://aistudio.google.com/

### Step 3: Tesseract Installation (Optional)

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

**macOS:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

### Step 4: Configure Tesseract Path
Update tesseract executable path in these files:
- `build_vector_all.py`
- `ocr_improved_split.py`

Modify the path setting:
```python
pytesseract.pytesseract.tesseract_cmd = "/path/to/tesseract"
```

Platform-specific paths:
- Windows: `"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"`
- macOS (Intel): `"/usr/local/bin/tesseract"`
- macOS (Apple Silicon): `"/opt/homebrew/bin/tesseract"`
- Linux: `"/usr/bin/tesseract"`

## System Operation

### Application Startup
```bash
cd new_ui
streamlit run app.py
```

Access the application at: http://localhost:8501

### Administrator Workflow
1. Access "Library Admin" panel in sidebar
2. Enter admin credentials (default password: 123456)
3. Upload PDF documents with source URLs
4. Execute "Save & Build" for incremental indexing
5. Use "Refresh Library" to reload vector database

### Student Interface
Students submit natural language queries through the chat interface. The system retrieves relevant document segments and generates responses with source citations.

## Project Structure
```
CHEM_CHATBOT_PRO/
├── new_ui/                   # Main application directory
│   ├── app.py               # Streamlit frontend application
│   ├── qa_bridge.py         # QA engine interface bridge
│   └── worker.py            # Background processing tasks
├── build_vector_all.py      # Vector database construction
├── qa_engine.py             # Core question-answering engine
├── module_links.py          # Module URL mappings
├── links.json               # Document source URL configuration
├── requirements.txt         # Python package dependencies
├── .env.example             # Environment variables template
├── pdfs/                    # PDF document storage
└── vector_dbs_all/          # FAISS vector database
    ├── index.faiss          # Vector index file
    └── index.pkl            # Metadata storage
```

## Technical Implementation Details

### Text Processing Pipeline
1. **PDF Parsing**: Primary text extraction via pypdf library
2. **OCR Fallback**: Tesseract processing for image-based documents
3. **Text Segmentation**: Paragraph-based chunking with 50+ character threshold
4. **Embedding Generation**: all-MiniLM-L6-v2 model for semantic vectors
5. **Vector Storage**: FAISS IndexFlatL2 for similarity search

### Query Processing
1. **Question Embedding**: Same SentenceTransformer model as document processing
2. **Similarity Search**: Top-K retrieval from FAISS index
3. **Context Assembly**: Retrieved segments with metadata formatting
4. **Response Generation**: Gemini API with citation instructions
5. **Output Formatting**: Markdown rendering with clickable source links

## Troubleshooting

### Common Issues and Solutions

**Error: "Google API key not found"**
Solution: Verify GOOGLE_API_KEY is properly set in .env file

**Error: OCR functionality not working**
Solution: Confirm Tesseract installation and path configuration

**Error: PDF upload fails**
Solution: Check file permissions and available disk space

**Error: Vector database not found**
Solution: Build initial index using "Rebuild Entire Library" function

**Error: Port 8501 unavailable**
Solution: Use alternative port: `streamlit run app.py --port 8502`

## Performance Optimization

### System Tuning
- Allocate sufficient memory (8GB+ recommended)
- Use SSD storage for vector database files
- Consider GPU acceleration for large document collections
- Implement periodic index rebuilding for optimal retrieval performance

### Monitoring
- Track memory usage during PDF processing
- Monitor API response times
- Log vector database query performance
- Review document processing success rates

## Security Considerations

- Secure storage of API credentials in .env file
- Change default admin password in production deployment
- Validate uploaded PDF files for malicious content
- Implement proper access controls for admin functions
- Ensure compliance with data protection regulations

## API Integration

The system integrates with Google Gemini API for natural language generation. API usage includes:
- Question interpretation and context understanding
- Response generation based on retrieved document segments
- Citation formatting and source attribution
- Error handling for API failures

## Maintenance Procedures

### Regular Maintenance
- Backup vector database and document storage
- Update Python dependencies periodically
- Monitor system logs for errors
- Perform full index rebuilds for performance optimization

### Document Management
- Validate source URLs for accessibility
- Remove outdated or irrelevant documents
- Update document metadata as needed
- Maintain consistent naming conventions

## Development Notes

This system was developed as part of academic research at Durham University Department of Chemistry. The implementation focuses on practical deployment and user accessibility while maintaining academic standards for information retrieval and citation.

## License and Attribution

Academic research project developed for Durham University Department of Chemistry. All external libraries and APIs are used in accordance with their respective licenses.