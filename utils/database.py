"""
Database operations for RoleSynch
Handles storing and retrieving analysis history from Firestore
"""

import streamlit as st
from datetime import datetime
from firebase_admin import firestore as fb_firestore
from utils.auth import db, is_authenticated


def save_analysis(resume_filename, jd_filename, similarity_score, results_dict, pdf_bytes=None):
    """
    Save an analysis to the user's history

    Args:
        resume_filename: Name of the uploaded resume file
        jd_filename: Name of the uploaded job description file
        similarity_score: Overall similarity score (0-100)
        results_dict: Complete analysis results dictionary
        pdf_bytes: Optional PDF report as bytes

    Returns:
        bool: True if saved successfully, False otherwise
    """
    if not is_authenticated() or not db:
        return False

    try:
        user_id = st.session_state.get('user_id')
        if not user_id:
            return False

        # Create analysis document - store RoleIQ format data for PDF regeneration
        analysis_data = {
            'user_id': user_id,
            'timestamp': datetime.now(),
            'resume_filename': resume_filename,
            'jd_filename': jd_filename,
            'similarity_score': similarity_score,
            # Store RoleIQ-style data (used for PDF generation)
            'summary': results_dict.get('summary', 'Analysis complete.'),
            'skill_matches': results_dict.get('skill_matches', []),
            'skill_gaps': results_dict.get('skill_gaps', []),
            'related_skills': results_dict.get('related_skills', []),
            'years_resume': results_dict.get('years_resume', 0),
            'years_required': results_dict.get('years_required', '0'),
            'skill_match_table': results_dict.get('skill_match_table', []),
            'recommendations': results_dict.get('recommendations', []),
            # Also store legacy format for backwards compatibility with existing UI display
            'skill_match': {
                'matches': results_dict.get('skill_matches', []),
                'gaps': results_dict.get('skill_gaps', []),
                'similar': results_dict.get('related_skills', [])
            }
        }

        # Add PDF bytes if provided
        if pdf_bytes:
            analysis_data['pdf_report'] = pdf_bytes

        # Add to Firestore
        doc_ref = db.collection('analyses').add(analysis_data)

        return True

    except Exception as e:
        return False


def get_user_analyses(user_id=None, limit=20):
    """
    Get analysis history for a user

    Args:
        user_id: User ID (defaults to current user)
        limit: Maximum number of analyses to return

    Returns:
        list: List of analysis dictionaries, ordered by timestamp (most recent first)
    """
    if not user_id:
        user_id = st.session_state.get('user_id')

    if not user_id or not db:
        return []

    try:
        # Query analyses for this user
        analyses_ref = db.collection('analyses') \
            .where('user_id', '==', user_id)

        analyses = []
        for doc in analyses_ref.stream():
            analysis_data = doc.to_dict()
            analysis_data['id'] = doc.id
            analyses.append(analysis_data)

        # Sort by timestamp in Python instead of Firestore (to avoid index requirement)
        from datetime import datetime
        analyses.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)

        # Apply limit after sorting
        return analyses[:limit]

    except Exception as e:
        print(f"Error retrieving analyses: {e}")
        return []


def get_analysis_by_id(analysis_id):
    """
    Get a specific analysis by its ID

    Args:
        analysis_id: Analysis document ID

    Returns:
        dict: Analysis data or None if not found
    """
    if not db:
        return None

    try:
        doc = db.collection('analyses').document(analysis_id).get()
        if doc.exists:
            analysis_data = doc.to_dict()
            analysis_data['id'] = doc.id
            return analysis_data
        return None

    except Exception as e:
        print(f"Error retrieving analysis: {e}")
        return None


def delete_analysis(analysis_id):
    """
    Delete an analysis from the database

    Args:
        analysis_id: Analysis document ID

    Returns:
        bool: True if deleted successfully, False otherwise
    """
    if not is_authenticated() or not db:
        return False

    try:
        # Verify the analysis belongs to the current user
        analysis = get_analysis_by_id(analysis_id)
        if not analysis:
            return False

        current_user_id = st.session_state.get('user_id')
        if analysis.get('user_id') != current_user_id:
            return False

        # Delete the analysis
        db.collection('analyses').document(analysis_id).delete()
        return True

    except Exception as e:
        print(f"Error deleting analysis: {e}")
        return False


def get_analysis_stats(user_id=None):
    """
    Get statistics about a user's analyses

    Args:
        user_id: User ID (defaults to current user)

    Returns:
        dict: Statistics including total analyses, average score, etc.
    """
    if not user_id:
        user_id = st.session_state.get('user_id')

    if not user_id or not db:
        return {
            'total_analyses': 0,
            'average_score': 0,
            'highest_score': 0,
            'lowest_score': 0
        }

    try:
        analyses = get_user_analyses(user_id, limit=100)

        if not analyses:
            return {
                'total_analyses': 0,
                'average_score': 0,
                'highest_score': 0,
                'lowest_score': 0
            }

        scores = [a.get('similarity_score', 0) for a in analyses]

        return {
            'total_analyses': len(analyses),
            'average_score': sum(scores) / len(scores) if scores else 0,
            'highest_score': max(scores) if scores else 0,
            'lowest_score': min(scores) if scores else 0,
            'recent_analyses': analyses[:5]  # Most recent 5
        }

    except Exception as e:
        print(f"Error calculating stats: {e}")
        return {
            'total_analyses': 0,
            'average_score': 0,
            'highest_score': 0,
            'lowest_score': 0
        }


def save_resume(filename, file_content, file_type):
    """
    Save a resume file to the user's saved resumes

    Args:
        filename: Name of the resume file
        file_content: Binary content of the file
        file_type: File extension (e.g., '.pdf', '.docx')

    Returns:
        tuple: (success: bool, message: str, resume_id: str or None)
    """
    if not is_authenticated() or not db:
        return False, "Not authenticated", None

    try:
        user_id = st.session_state.get('user_id')
        if not user_id:
            return False, "User ID not found", None

        # Check if user already has a resume with this name
        existing = db.collection('resumes') \
            .where('user_id', '==', user_id) \
            .where('filename', '==', filename) \
            .limit(1) \
            .stream()

        for doc in existing:
            return False, f"A resume named '{filename}' already exists", None

        # Create resume document
        resume_data = {
            'user_id': user_id,
            'filename': filename,
            'file_type': file_type,
            'file_content': file_content,
            'uploaded_at': datetime.now(),
            'last_used': datetime.now()
        }

        # Add to Firestore
        doc_ref = db.collection('resumes').add(resume_data)
        resume_id = doc_ref[1].id

        return True, "Resume saved successfully", resume_id

    except Exception as e:
        print(f"Error saving resume: {e}")
        return False, f"Error saving resume: {str(e)}", None


def get_user_resumes(user_id=None):
    """
    Get all saved resumes for a user

    Args:
        user_id: User ID (defaults to current user)

    Returns:
        list: List of resume dictionaries
    """
    if not user_id:
        user_id = st.session_state.get('user_id')

    if not user_id or not db:
        return []

    try:
        # Query resumes for this user
        resumes_ref = db.collection('resumes') \
            .where('user_id', '==', user_id)

        resumes = []
        for doc in resumes_ref.stream():
            resume_data = doc.to_dict()
            resume_data['id'] = doc.id
            resumes.append(resume_data)

        # Sort by last_used in Python instead of Firestore (to avoid index requirement)
        resumes.sort(key=lambda x: x.get('last_used', datetime.min), reverse=True)

        return resumes

    except Exception as e:
        print(f"Error retrieving resumes: {e}")
        return []


def get_resume_by_id(resume_id):
    """
    Get a specific resume by its ID

    Args:
        resume_id: Resume document ID

    Returns:
        dict: Resume data or None if not found
    """
    if not db:
        return None

    try:
        doc = db.collection('resumes').document(resume_id).get()
        if doc.exists:
            resume_data = doc.to_dict()
            resume_data['id'] = doc.id
            return resume_data
        return None

    except Exception as e:
        print(f"Error retrieving resume: {e}")
        return None


def update_resume_last_used(resume_id):
    """
    Update the last_used timestamp for a resume

    Args:
        resume_id: Resume document ID

    Returns:
        bool: True if updated successfully, False otherwise
    """
    if not is_authenticated() or not db:
        return False

    try:
        db.collection('resumes').document(resume_id).update({
            'last_used': datetime.now()
        })
        return True

    except Exception as e:
        print(f"Error updating resume: {e}")
        return False


def delete_resume(resume_id):
    """
    Delete a resume from the database

    Args:
        resume_id: Resume document ID

    Returns:
        bool: True if deleted successfully, False otherwise
    """
    if not is_authenticated() or not db:
        return False

    try:
        # Verify the resume belongs to the current user
        resume = get_resume_by_id(resume_id)
        if not resume:
            return False

        current_user_id = st.session_state.get('user_id')
        if resume.get('user_id') != current_user_id:
            return False

        # Delete the resume
        db.collection('resumes').document(resume_id).delete()
        return True

    except Exception as e:
        print(f"Error deleting resume: {e}")
        return False


# ============== JOB DESCRIPTION FUNCTIONS ==============

def save_job_description(filename, content, extracted_skills=None, title=None):
    """
    Save a job description to the database for analytics and future reference.

    Args:
        filename: Name of the JD file or "Text Input" for pasted text
        content: Full text content of the job description
        extracted_skills: List of skills extracted from the JD
        title: Optional job title (extracted from content if not provided)

    Returns:
        tuple: (success: bool, jd_id: str or None)
    """
    if not db:
        return False, None

    try:
        # Try to extract a title from the content if not provided
        if not title:
            # Look for common patterns like "Job Title:" or first line
            lines = content.strip().split('\n')
            for line in lines[:5]:  # Check first 5 lines
                line = line.strip()
                if line and len(line) < 100:  # Reasonable title length
                    if ':' in line:
                        # Check for patterns like "Job Title: Software Engineer"
                        parts = line.split(':', 1)
                        if parts[0].lower() in ['job title', 'position', 'role', 'title']:
                            title = parts[1].strip()
                            break
                    elif not any(word in line.lower() for word in ['responsibilities', 'requirements', 'qualifications', 'about']):
                        title = line[:80]  # Use first line as title
                        break

            if not title:
                title = filename if filename != "Text Input" else "Untitled JD"

        # Create a content hash to check for duplicates
        import hashlib
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # Check if this JD already exists (by content hash)
        existing = db.collection('job_descriptions').where('content_hash', '==', content_hash).limit(1).stream()

        for doc in existing:
            # JD already exists, increment usage count
            doc_ref = db.collection('job_descriptions').document(doc.id)
            doc_ref.update({
                'usage_count': fb_firestore.Increment(1),
                'last_used': datetime.now()
            })
            return True, doc.id

        # Create new JD document
        jd_data = {
            'filename': filename,
            'title': title,
            'content': content[:50000],  # Limit content size for Firestore
            'content_hash': content_hash,
            'extracted_skills': extracted_skills or [],
            'created_at': datetime.now(),
            'last_used': datetime.now(),
            'usage_count': 1
        }

        # Add to Firestore
        doc_ref = db.collection('job_descriptions').add(jd_data)
        jd_id = doc_ref[1].id

        return True, jd_id

    except Exception as e:
        return False, None


def get_job_description_by_id(jd_id):
    """
    Get a specific job description by its ID

    Args:
        jd_id: Job description document ID

    Returns:
        dict: JD data or None if not found
    """
    if not db:
        return None

    try:
        doc = db.collection('job_descriptions').document(jd_id).get()
        if doc.exists:
            jd_data = doc.to_dict()
            jd_data['id'] = doc.id
            return jd_data
        return None

    except Exception as e:
        print(f"Error retrieving job description: {e}")
        return None


def search_job_descriptions(search_term, limit=20):
    """
    Search job descriptions by title or content

    Args:
        search_term: Text to search for
        limit: Maximum number of results

    Returns:
        list: Matching job descriptions
    """
    if not db:
        return []

    try:
        # Firestore doesn't support full-text search, so we get all and filter
        jds = []
        search_lower = search_term.lower()

        for doc in db.collection('job_descriptions').stream():
            jd_data = doc.to_dict()
            jd_data['id'] = doc.id

            # Search in title and content
            if (search_lower in jd_data.get('title', '').lower() or
                search_lower in jd_data.get('filename', '').lower() or
                search_lower in jd_data.get('content', '')[:500].lower()):
                jds.append(jd_data)

            if len(jds) >= limit:
                break

        return jds

    except Exception as e:
        print(f"Error searching job descriptions: {e}")
        return []
