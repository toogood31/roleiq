import re
import fitz  # PyMuPDF for PDF
from docx import Document  # For DOCX
from utils.model_cache import load_spacy_model

nlp = load_spacy_model()

def clean_text(text):
    text = re.sub(r'\s+', ' ', text.lower().strip())
    # Preserve hyphens, dashes, and plus signs for year ranges like "5-7+" or "5+"
    text = re.sub(r'[^\w\s\-+]', '', text)
    return text

def parse_document(file_path):
    if file_path.endswith('.pdf'):
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
        return clean_text(text)
    elif file_path.endswith('.docx'):
        doc = Document(file_path)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return clean_text(text)
    else:
        raise ValueError("Unsupported file type")

def extract_sections(text):
    """
    Extract resume sections with improved header detection.
    Handles various section header formats and resume structures.
    """
    doc = nlp(text)
    sections = {"experience": [], "skills": [], "education": [], "other": []}
    current_section = "other"  # Default to "other" instead of None

    # More comprehensive section header patterns
    experience_keywords = ['experience', 'work history', 'employment', 'professional background',
                          'work experience', 'career history', 'employment history']
    skills_keywords = ['skills', 'technical skills', 'core competencies', 'qualifications',
                      'expertise', 'proficiencies', 'capabilities']
    education_keywords = ['education', 'academic background', 'academic credentials',
                         'degrees', 'certifications', 'training']

    for sent in doc.sents:
        sent_text = sent.text.strip().lower()

        # Check if this is a section header
        is_header = False

        # Experience section
        if any(keyword in sent_text for keyword in experience_keywords):
            current_section = "experience"
            is_header = True
        # Skills section
        elif any(keyword in sent_text for keyword in skills_keywords):
            current_section = "skills"
            is_header = True
        # Education section
        elif any(keyword in sent_text for keyword in education_keywords):
            current_section = "education"
            is_header = True

        # Add content to current section (skip section headers)
        if not is_header and sent.text.strip():
            sections[current_section].append(sent.text.strip())

    # Fallback: If no experience section found, treat entire document as experience
    # This helps with resumes that don't have explicit section headers
    if not sections["experience"]:
        sections["experience"] = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    return sections
