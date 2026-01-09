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
    """
    Parse document and return RAW text without cleaning.

    IMPORTANT: Do NOT apply clean_text() here - it removes punctuation
    which destroys sentence boundaries needed for extract_sections().
    Cleaning should only be done for specific operations that need it.
    """
    if file_path.endswith('.pdf'):
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
        return text  # Return RAW text, don't clean it
    elif file_path.endswith('.docx'):
        doc = Document(file_path)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text  # Return RAW text, don't clean it
    else:
        raise ValueError("Unsupported file type")

def extract_sections(text):
    """
    Extract resume sections using two-pass parsing to handle out-of-order sections.

    PASS 1: Identify all section headers and their positions
    PASS 2: Assign each line to the section whose header it follows

    This approach handles resumes where EDUCATION appears before EXPERIENCE,
    or where skills/experience keywords appear in content (not as headers).
    """
    sections = {"experience": [], "skills": [], "education": [], "other": []}

    # More comprehensive section header patterns
    experience_keywords = ['work history', 'employment history', 'professional background',
                          'work experience', 'career history', 'professional experience']
    skills_keywords = ['technical skills', 'core competencies', 'computer skills',
                      'proficiencies', 'capabilities']
    education_keywords = ['education', 'academic background', 'academic credentials',
                         'degrees', 'certifications and training']

    # Split by newlines
    lines = text.split('\n')

    # PASS 1: Find all section headers and their positions
    section_headers = []  # List of (line_index, section_name, is_definite_header)

    for i, line in enumerate(lines):
        line_text = line.strip()
        if not line_text:
            continue

        line_lower = line_text.lower()

        # Detect definite section headers (short lines that are just the section name)
        is_short_header = len(line_text) < 50  # Section headers are usually short

        # Check for experience section (but exclude "Experience with..." - that's content, not a header)
        if any(keyword in line_lower for keyword in experience_keywords):
            section_headers.append((i, "experience", True))
        elif line_lower.strip() == 'experience' or (is_short_header and 'experience' in line_lower and ':' not in line_lower):
            # Standalone "experience" or short lines with "experience" (not followed by content)
            section_headers.append((i, "experience", True))
        # Skills section
        elif any(keyword in line_lower for keyword in skills_keywords):
            section_headers.append((i, "skills", True))
        # Education section
        elif any(keyword in line_lower for keyword in education_keywords):
            section_headers.append((i, "education", True))

    # PASS 2: Assign lines to sections based on which header they follow
    if section_headers:
        # Sort headers by position
        section_headers.sort(key=lambda x: x[0])

        # Assign lines to sections
        for i, line in enumerate(lines):
            line_text = line.strip()
            if not line_text:
                continue

            # Determine which section this line belongs to
            current_section = "other"
            for j in range(len(section_headers) - 1, -1, -1):
                header_idx, section_name, is_definite = section_headers[j]
                if i > header_idx:  # This line comes after this header
                    current_section = section_name
                    break

            # Skip the header line itself
            is_header_line = any(i == h[0] for h in section_headers)
            if not is_header_line:
                sections[current_section].append(line_text)
    else:
        # No section headers found - treat entire document as experience
        sections["experience"] = [line.strip() for line in lines if line.strip()]

    # Fallback: If no experience section found, treat entire document as experience
    if not sections["experience"]:
        sections["experience"] = [line.strip() for line in lines if line.strip()]

    return sections
