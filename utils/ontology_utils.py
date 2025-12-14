import json
import os
import re

def load_job_titles():
    """Load job title taxonomy"""
    ontology_path = 'data/ontologies/job_titles.json'
    if os.path.exists(ontology_path):
        with open(ontology_path, 'r') as f:
            return json.load(f)
    return {}

def load_certifications():
    """Load certification database"""
    ontology_path = 'data/ontologies/certifications.json'
    if os.path.exists(ontology_path):
        with open(ontology_path, 'r') as f:
            return json.load(f)
    return {}

def normalize_job_title(title_text):
    """
    Normalize job title to canonical form using taxonomy
    Returns: (canonical_title, seniority_level, confidence)
    """
    if not title_text:
        return None, None, 0.0

    job_titles = load_job_titles()
    title_lower = title_text.lower().strip()

    best_match = None
    best_confidence = 0.0
    detected_level = None

    for canonical, data in job_titles.items():
        variations = data.get('variations', [])
        level_indicators = data.get('level_indicators', {})

        # Check for exact variation match
        for variation in variations:
            if variation in title_lower:
                confidence = len(variation) / len(title_lower)  # Partial match scoring

                if confidence > best_confidence:
                    best_match = canonical
                    best_confidence = confidence

                    # Detect seniority level
                    for level, keywords in level_indicators.items():
                        for keyword in keywords:
                            if keyword in title_lower:
                                detected_level = level
                                break
                        if detected_level:
                            break

    return best_match, detected_level, best_confidence

def detect_certifications(text, industry=None):
    """
    Detect certifications mentioned in text
    Returns: dict with 'critical' and 'valuable' certifications found
    """
    if not text:
        return {'critical': [], 'valuable': []}

    certifications_db = load_certifications()
    text_lower = text.lower()

    found = {
        'critical': [],
        'valuable': []
    }

    # Determine which industries to search
    industries_to_search = [industry] if industry else certifications_db.keys()

    for industry_name in industries_to_search:
        if industry_name not in certifications_db:
            continue

        industry_certs = certifications_db[industry_name]

        # Check critical certifications
        for cert in industry_certs.get('critical', []):
            if _cert_in_text(cert, text_lower):
                found['critical'].append({
                    'name': cert['name'],
                    'full_name': cert['full_name'],
                    'industry': industry_name
                })

        # Check valuable certifications
        for cert in industry_certs.get('valuable', []):
            if _cert_in_text(cert, text_lower):
                found['valuable'].append({
                    'name': cert['name'],
                    'full_name': cert['full_name'],
                    'industry': industry_name
                })

    # Remove duplicates
    found['critical'] = _dedupe_certs(found['critical'])
    found['valuable'] = _dedupe_certs(found['valuable'])

    return found

def _cert_in_text(cert, text_lower):
    """Check if certification is mentioned in text"""
    # Check main name
    if cert['name'].lower() in text_lower:
        return True

    # Check full name
    if cert['full_name'].lower() in text_lower:
        return True

    # Check aliases
    for alias in cert.get('aliases', []):
        if alias.lower() in text_lower:
            return True

    return False

def _dedupe_certs(cert_list):
    """Remove duplicate certifications"""
    seen = set()
    unique = []
    for cert in cert_list:
        if cert['name'] not in seen:
            seen.add(cert['name'])
            unique.append(cert)
    return unique

def find_certification_gaps(resume_text, jd_text, industry=None):
    """
    Find certification gaps between resume and JD
    Returns: dict with missing critical and valuable certifications
    """
    resume_certs = detect_certifications(resume_text, industry)
    jd_certs = detect_certifications(jd_text, industry)

    # Find what's in JD but not in resume
    resume_cert_names = set(c['name'] for c in resume_certs['critical'] + resume_certs['valuable'])

    missing_critical = [
        cert for cert in jd_certs['critical']
        if cert['name'] not in resume_cert_names
    ]

    missing_valuable = [
        cert for cert in jd_certs['valuable']
        if cert['name'] not in resume_cert_names
    ]

    return {
        'missing_critical': missing_critical,
        'missing_valuable': missing_valuable,
        'has_certifications': len(resume_cert_names) > 0
    }

def match_job_titles(resume_title, jd_title):
    """
    Check if two job titles match using taxonomy
    Returns: (match_score, explanation)
    """
    resume_canonical, resume_level, resume_conf = normalize_job_title(resume_title)
    jd_canonical, jd_level, jd_conf = normalize_job_title(jd_title)

    if not resume_canonical or not jd_canonical:
        # Fallback to simple string matching
        if resume_title and jd_title:
            similarity = len(set(resume_title.lower().split()) & set(jd_title.lower().split())) / len(set(jd_title.lower().split()))
            return similarity, "Basic text match"
        return 0.0, "Unable to normalize titles"

    # Perfect match
    if resume_canonical == jd_canonical:
        if resume_level == jd_level:
            return 1.0, f"Exact match: {resume_canonical} ({resume_level})"
        elif resume_level and jd_level:
            # Check if levels are compatible (e.g., senior vs mid)
            level_hierarchy = ['junior', 'mid', 'senior', 'lead', 'executive']
            if resume_level in level_hierarchy and jd_level in level_hierarchy:
                level_diff = abs(level_hierarchy.index(resume_level) - level_hierarchy.index(jd_level))
                if level_diff == 0:
                    return 1.0, f"Exact match: {resume_canonical} ({resume_level})"
                elif level_diff == 1:
                    return 0.85, f"Close match: {resume_canonical} (one level difference)"
                else:
                    return 0.6, f"Same role, different seniority: {resume_canonical}"
        return 0.9, f"Same role: {resume_canonical}"

    # Different roles
    return 0.0, "Different roles"

def enhance_skill_matching(resume_skills, jd_skills):
    """
    Enhance skill matching by normalizing job titles found in skill lists
    Returns: (additional_matches, additional_gaps)
    """
    job_titles = load_job_titles()

    additional_matches = []
    additional_gaps = []

    # Build a flat list of all title variations
    all_variations = {}
    for canonical, data in job_titles.items():
        for variation in data.get('variations', []):
            all_variations[variation] = canonical

    # Check if any "skills" are actually job title variations
    for resume_skill in resume_skills:
        resume_skill_lower = resume_skill.lower()
        for jd_skill in jd_skills:
            jd_skill_lower = jd_skill.lower()

            # Check if both are job title variations
            resume_canonical = all_variations.get(resume_skill_lower)
            jd_canonical = all_variations.get(jd_skill_lower)

            if resume_canonical and jd_canonical and resume_canonical == jd_canonical:
                if resume_skill not in additional_matches:
                    additional_matches.append(resume_skill)

    return additional_matches, additional_gaps
