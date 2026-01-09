"""
Field mismatch detection and scoring adjustments
Prevents false matches between completely different professions (e.g., accountant vs engineer)

Uses 3-Tier Hybrid Detection:
- Tier 1: Industry-based field mapping (most reliable)
- Tier 2: Resume section parsing for actual job titles
- Tier 3: Keyword-based detection (fallback)
"""
import re
from utils.extractor import INDUSTRY_KEYWORDS, detect_industry


# TIER 1: Industry-to-Field Mapping
# Maps detect_industry() results to professional field categories
INDUSTRY_TO_FIELD_MAP = {
    'finance': 'accounting',
    'hr': 'hr',
    'technology': 'software',
    'engineering': 'engineering',
    'healthcare': 'healthcare',
    'legal': 'legal',
    'marketing': 'marketing',
    'sales': 'sales',
    'operations': 'operations',
    'creative': 'creative',
    'education': 'education',
    'athletics': 'athletics',
}


def detect_field_from_industry(text):
    """
    TIER 1: Use existing industry detection to determine professional field

    This is the most reliable method as it uses keyword density scoring
    across the full document rather than simple keyword matching.

    Args:
        text: Resume or JD text

    Returns:
        Set of field categories (e.g., {'hr', 'accounting'})
    """
    industries = detect_industry(text)

    if not industries:
        return set()

    # Map top industries to field categories
    fields = set()
    for industry, score in industries[:3]:  # Top 3 industries
        if industry in INDUSTRY_TO_FIELD_MAP:
            fields.add(INDUSTRY_TO_FIELD_MAP[industry])
        else:
            # Fallback: use industry name as field
            fields.add(industry)

    # GENERALIZED FIELD PRIORITY SYSTEM
    # Remove secondary fields ('hr', 'accounting') when they conflict with primary professions
    # This handles ALL cases: benefits sections triggering 'hr', budgets triggering 'accounting', etc.

    if len(fields) > 1:
        text_lower = text.lower()

        # Define PRIMARY profession keywords (actual job functions, not support activities)
        # These take priority over 'hr' and 'accounting' which often come from benefits/budget sections
        primary_profession_keywords = {
            'legal': [
                'paralegal', 'attorney', 'lawyer', 'legal counsel', 'litigation',
                'law firm', 'legal assistant', 'legal secretary', 'court', 'trial',
                'discovery', 'deposition', 'subpoena', 'plaintiff', 'defendant', 'legal compliance'
            ],
            'healthcare': [
                'nurse', 'physician', 'doctor', 'medical', 'clinical', 'patient care',
                'healthcare provider', 'registered nurse', 'nurse practitioner', 'surgery',
                'diagnosis', 'treatment', 'hospital', 'clinic'
            ],
            'engineering': [
                'structural engineer', 'civil engineer', 'mechanical engineer',
                'electrical engineer', 'chemical engineer', 'engineering design',
                'cad', 'blueprints', 'construction', 'infrastructure', 'hvac'
            ],
            'software': [
                'software engineer', 'software developer', 'programmer', 'coding',
                'full stack', 'backend', 'frontend', 'react', 'python', 'java',
                'api', 'database', 'devops', 'git', 'agile development'
            ],
            'sales': [
                'sales representative', 'sales associate', 'account executive',
                'business development', 'sales quota', 'cold calling', 'lead generation',
                'sales pipeline', 'crm', 'sales manager', 'revenue target'
            ],
            'marketing': [
                'marketing manager', 'marketing coordinator', 'brand manager',
                'digital marketing', 'seo', 'content marketing', 'social media marketing',
                'campaign management', 'market research', 'marketing analytics'
            ],
            'operations': [
                'operations manager', 'supply chain', 'logistics', 'procurement',
                'inventory management', 'warehouse', 'distribution', 'process improvement'
            ],
            'creative': [
                'graphic designer', 'art director', 'creative director', 'ux designer',
                'ui designer', 'illustrator', 'photoshop', 'video editing', 'branding'
            ],
            'athletics': [
                'athletic director', 'athletics director', 'head coach', 'assistant coach',
                'athletic administrator', 'sports director', 'strength coach', 'recruiting coordinator'
            ],
            'education': [
                'teacher', 'professor', 'instructor', 'curriculum', 'classroom',
                'lesson plan', 'student assessment', 'educational coordinator', 'principal', 'dean'
            ],
            'accounting': [
                'controller', 'accountant', 'cpa', 'certified public accountant',
                'accounts payable', 'accounts receivable', 'financial statements',
                'balance sheet', 'income statement', 'cash flow', 'general ledger',
                'journal entries', 'gaap', 'financial reporting', 'audit',
                'bookkeeping', 'reconciliation', 'accrual accounting', 'tax preparation'
            ]
        }

        # SPECIAL CASE: HR/Compensation professionals (accounting + hr)
        # If both are present, prioritize HR if HR-specific keywords are found
        if 'accounting' in fields and 'hr' in fields:
            hr_profession_keywords = [
                'compensation', 'total rewards', 'benefits administration', 'payroll',
                'hr manager', 'human resources', 'talent acquisition', 'recruiting',
                'people operations', 'employee relations', 'performance management',
                'onboarding', 'offboarding', 'hr compliance', 'workforce planning'
            ]
            if any(keyword in text_lower for keyword in hr_profession_keywords):
                fields.discard('accounting')  # This is an HR professional, not an accountant

        # GENERALIZED: Remove 'hr' when it conflicts with primary professions
        # (hr often appears from benefits sections in job postings, not the actual role)
        if 'hr' in fields:
            for profession, keywords in primary_profession_keywords.items():
                if profession in fields and profession != 'hr':
                    # Check if this is truly a primary profession role
                    if any(keyword in text_lower for keyword in keywords):
                        fields.discard('hr')  # Remove HR, it's from benefits section
                        break

        # GENERALIZED: Remove 'accounting' when it conflicts with primary professions
        # (accounting often appears from budget/financial discussions, not the actual role)
        if 'accounting' in fields:
            for profession, keywords in primary_profession_keywords.items():
                if profession in fields and profession != 'accounting':
                    # Check if this is truly a primary profession role
                    if any(keyword in text_lower for keyword in keywords):
                        fields.discard('accounting')  # Remove accounting, it's from financial discussions
                        break

        # GENERALIZED: Remove 'software' when it conflicts with primary professions
        # (software often appears from mentions of using software tools, not actual software engineering)
        if 'software' in fields:
            for profession, keywords in primary_profession_keywords.items():
                if profession in fields and profession != 'software':
                    # Check if this is truly a primary profession role
                    if any(keyword in text_lower for keyword in keywords):
                        fields.discard('software')  # Remove software, it's from tool/system mentions
                        break

    return fields


def extract_job_titles_from_resume(resume_text):
    """
    TIER 2: Parse actual job titles from resume structure

    Looks for common resume section headers and extracts titles that follow.

    Args:
        resume_text: Full resume text

    Returns:
        Set of field categories based on extracted titles
    """
    resume_lower = resume_text.lower()

    # Find work experience section
    experience_patterns = [
        r'(?:work\s+)?experience[:\s]+(.*?)(?:education|skills|certifications|$)',
        r'employment\s+history[:\s]+(.*?)(?:education|skills|certifications|$)',
        r'professional\s+experience[:\s]+(.*?)(?:education|skills|certifications|$)',
    ]

    experience_section = ""
    for pattern in experience_patterns:
        match = re.search(pattern, resume_lower, re.DOTALL | re.IGNORECASE)
        if match:
            experience_section = match.group(1)[:2000]  # First 2000 chars
            break

    if not experience_section:
        # Fallback: use first 40% of resume
        experience_section = resume_lower[:len(resume_lower) * 2 // 5]

    # Job title categories with WORD-BOUNDARY matching to avoid false matches
    # Use \b to ensure we only match complete words/phrases
    title_categories = {
        'accounting': [r'\baccountant\b', r'\bbookkeeper\b', r'\bcontroller\b', r'\bcpa\b', r'\baccounts payable\b', r'\baccounts receivable\b', r'\bfinancial analyst\b'],
        'engineering': [r'\bstructural engineer\b', r'\bcivil engineer\b', r'\bmechanical engineer\b', r'\belectrical engineer\b', r'\bchemical engineer\b', r'\barchitect\b'],
        'software': [r'\bsoftware engineer\b', r'\bsoftware developer\b', r'\bprogrammer\b', r'\bsoftware architect\b', r'\btech lead\b', r'\bfull stack\b', r'\bbackend developer\b', r'\bfrontend developer\b'],
        'sales': [r'\bsales representative\b', r'\bsales associate\b', r'\baccount executive\b', r'\bbusiness development\b', r'\bsales manager\b', r'\bsales director\b'],
        'marketing': [r'\bmarketing manager\b', r'\bmarketing coordinator\b', r'\bbrand manager\b', r'\bmarketing director\b', r'\bdigital marketing\b', r'\bmarketing specialist\b'],
        'hr': [r'\brecruiter\b', r'\bhr manager\b', r'\btalent acquisition\b', r'\bpeople operations\b', r'\bhuman resources\b', r'\bcompensation\b', r'\bbenefits\b', r'\bhr\b'],
        'operations': [r'\boperations manager\b', r'\bsupply chain\b', r'\blogistics\b', r'\bprocurement\b'],
        'legal': [r'\battorney\b', r'\blawyer\b', r'\blegal counsel\b', r'\bparalegal\b'],
        'healthcare': [r'\bregistered nurse\b', r'\bnurse practitioner\b', r'\bphysician\b', r'\bdoctor\b', r'\bhealthcare admin\b', r'\bmedical assistant\b', r'\bhealthcare provider\b'],
        'creative': [r'\bdesigner\b', r'\bart director\b', r'\bcreative director\b', r'\bux designer\b'],
        'athletics': [r'\bathletic director\b', r'\bathletics director\b', r'\bhead coach\b', r'\bassistant coach\b', r'\bathletic administrator\b', r'\bsports director\b'],
        'education': [r'\bteacher\b', r'\bprofessor\b', r'\binstructor\b', r'\bacademic coordinator\b', r'\beducation coordinator\b', r'\bprincipal\b', r'\bdean\b'],
    }

    detected_fields = set()
    for category, title_patterns in title_categories.items():
        for pattern in title_patterns:
            if re.search(pattern, experience_section):
                detected_fields.add(category)
                break  # Only need one match per category

    return detected_fields


def detect_field_mismatch(resume_industries, jd_industries, resume_text, jd_text):
    """
    Detect if resume and JD are from completely different professional fields.

    Returns:
        dict with:
        - is_mismatch: bool
        - severity: 'CRITICAL', 'MODERATE', 'MINOR', or 'NONE'
        - score_cap: maximum allowed score (0-100)
        - explanation: str describing the mismatch
    """
    # Get primary industries
    resume_primary = resume_industries[0][0] if resume_industries else 'general'
    jd_primary = jd_industries[0][0] if jd_industries else 'general'

    # Critical mismatches - completely incompatible fields
    critical_incompatibilities = [
        ('finance', 'technology'),
        ('finance', 'engineering'),
        ('finance', 'healthcare'),
        ('finance', 'creative'),
        ('technology', 'finance'),
        ('technology', 'healthcare'),
        ('technology', 'engineering'),
        ('engineering', 'finance'),
        ('engineering', 'technology'),
        ('engineering', 'marketing'),
        ('engineering', 'sales'),
        ('engineering', 'healthcare'),
        ('healthcare', 'technology'),
        ('healthcare', 'finance'),
        ('healthcare', 'engineering'),
        ('creative', 'technology'),
        ('creative', 'finance'),
        ('creative', 'engineering'),
        ('legal', 'technology'),
        ('legal', 'healthcare'),
        ('legal', 'engineering'),
    ]

    # Check for critical mismatch
    if (resume_primary, jd_primary) in critical_incompatibilities:
        return {
            'is_mismatch': True,
            'severity': 'CRITICAL',
            'score_cap': 15,
            'explanation': f"Resume shows {resume_primary} background, but JD requires {jd_primary} field. These are fundamentally different professions."
        }

    # Check for job title mismatch
    resume_title_mismatch = detect_job_title_mismatch(resume_text, jd_text)

    if resume_title_mismatch['is_mismatch'] and resume_title_mismatch['severity'] == 'CRITICAL':
        return {
            'is_mismatch': True,
            'severity': 'CRITICAL',
            'score_cap': 15,
            'explanation': resume_title_mismatch['explanation']
        }

    # Moderate mismatches - related but different specializations
    if resume_primary != jd_primary and resume_primary != 'general' and jd_primary != 'general':
        # Check if there's ANY industry overlap
        resume_industries_set = set([ind[0] for ind in resume_industries])
        jd_industries_set = set([ind[0] for ind in jd_industries])

        if len(resume_industries_set & jd_industries_set) == 0:
            # No overlap at all
            return {
                'is_mismatch': True,
                'severity': 'MODERATE',
                'score_cap': 40,
                'explanation': f"Resume shows {resume_primary} background, JD is {jd_primary}. Related but different specializations."
            }

    # No significant mismatch
    return {
        'is_mismatch': False,
        'severity': 'NONE',
        'score_cap': 100,
        'explanation': ''
    }


def detect_job_title_mismatch(resume_text, jd_text):
    """
    3-Tier Hybrid job title/field detection and mismatch checking

    Uses three complementary approaches:
    - TIER 1: Industry-based field mapping (most reliable)
    - TIER 2: Resume section parsing for actual job titles
    - TIER 3: Keyword-based detection (fallback)

    Returns:
        dict with is_mismatch, severity, explanation
    """
    # TIER 1: Use industry detection (most reliable)
    resume_fields_tier1 = detect_field_from_industry(resume_text)
    jd_fields_tier1 = detect_field_from_industry(jd_text)

    # TIER 2: Parse job titles from resume structure
    resume_fields_tier2 = extract_job_titles_from_resume(resume_text)
    jd_fields_tier2 = extract_job_titles_from_resume(jd_text)

    # Combine Tier 1 and Tier 2 results (Tier 1 has priority)
    resume_fields = resume_fields_tier1 | resume_fields_tier2
    jd_fields = jd_fields_tier1 | jd_fields_tier2

    # TIER 3: Fallback to keyword matching if needed
    if not resume_fields or not jd_fields:
        # Use simplified keyword detection only as fallback
        resume_lower = resume_text.lower()
        jd_lower = jd_text.lower()

        # Simplified title categories (less broad than before)
        title_categories = {
            'accounting': ['accountant', 'bookkeeper', 'controller', 'cpa'],
            'engineering': ['structural engineer', 'civil engineer', 'mechanical engineer', 'electrical engineer'],
            'software': ['software engineer', 'software developer', 'programmer'],
            'sales': ['sales representative', 'sales associate', 'account executive'],
            'marketing': ['marketing manager', 'marketing coordinator', 'brand manager'],
            'hr': ['recruiter', 'hr manager', 'talent acquisition', 'compensation', 'benefits'],
            'legal': ['attorney', 'lawyer', 'legal counsel', 'paralegal'],
            'healthcare': ['registered nurse', 'nurse practitioner', 'physician', 'doctor'],
        }

        if not resume_fields:
            resume_first_third = resume_lower[:len(resume_lower)//3]
            for category, titles in title_categories.items():
                if any(title in resume_first_third for title in titles):
                    resume_fields.add(category)

        if not jd_fields:
            jd_first_half = jd_lower[:len(jd_lower)//2]
            for category, titles in title_categories.items():
                if any(title in jd_first_half for title in titles):
                    jd_fields.add(category)

    # Check for critical mismatch
    if resume_fields and jd_fields:
        # Define incompatible profession pairs that should NEVER match
        # Even if there's some minor overlap (e.g., HR vs Legal both touch HR, but are incompatible)
        incompatible_pairs = [
            ('accounting', 'legal'), ('legal', 'accounting'),
            ('hr', 'legal'), ('legal', 'hr'),
            ('accounting', 'engineering'), ('engineering', 'accounting'),
            ('accounting', 'software'), ('software', 'accounting'),
            ('hr', 'engineering'), ('engineering', 'hr'),
            ('hr', 'software'), ('software', 'hr'),
            ('legal', 'software'), ('software', 'legal'),
            ('legal', 'engineering'), ('engineering', 'legal'),
            ('legal', 'healthcare'), ('healthcare', 'legal'),
            ('legal', 'sales'), ('sales', 'legal'),
            ('legal', 'marketing'), ('marketing', 'legal'),
            ('healthcare', 'software'), ('software', 'healthcare'),
            ('healthcare', 'engineering'), ('engineering', 'healthcare'),
            ('healthcare', 'accounting'), ('accounting', 'healthcare'),
        ]

        # Check all combinations of resume and JD fields for incompatibilities
        for resume_field in resume_fields:
            for jd_field in jd_fields:
                if (resume_field, jd_field) in incompatible_pairs:
                    resume_cat_str = ', '.join(sorted(resume_fields))
                    jd_cat_str = ', '.join(sorted(jd_fields))
                    return {
                        'is_mismatch': True,
                        'severity': 'CRITICAL',
                        'explanation': f"Candidate's field ({resume_cat_str}) does not match role ({jd_cat_str}). These are different professions."
                    }

        # If no specific incompatibility, check for complete lack of overlap
        if len(resume_fields & jd_fields) == 0:
            # No overlap in job title categories
            resume_cat_str = ', '.join(sorted(resume_fields))
            jd_cat_str = ', '.join(sorted(jd_fields))

            return {
                'is_mismatch': True,
                'severity': 'CRITICAL',
                'explanation': f"Candidate's field ({resume_cat_str}) does not match role ({jd_cat_str}). These are different professions."
            }

    return {
        'is_mismatch': False,
        'severity': 'NONE',
        'explanation': ''
    }


def apply_scoring_penalties(base_score, field_mismatch, education_validation, experience_validation):
    """
    Apply penalties to base score based on hard requirements and field mismatches

    Returns:
        dict with:
        - adjusted_score: final score after penalties
        - penalties_applied: list of penalty descriptions
        - original_score: base score before adjustments
    """
    adjusted_score = base_score
    penalties = []

    # CRITICAL: Field mismatch caps score heavily
    if field_mismatch['is_mismatch']:
        if field_mismatch['severity'] == 'CRITICAL':
            adjusted_score = min(adjusted_score, field_mismatch['score_cap'])
            penalties.append(f"CRITICAL MISMATCH: {field_mismatch['explanation']} (Score capped at {field_mismatch['score_cap']}%)")
        elif field_mismatch['severity'] == 'MODERATE':
            adjusted_score = min(adjusted_score, field_mismatch['score_cap'])
            penalties.append(f"Field mismatch: {field_mismatch['explanation']} (Score capped at {field_mismatch['score_cap']}%)")

    # DEALBREAKER: Education requirement not met
    if education_validation.get('severity') == 'DEALBREAKER':
        adjusted_score = min(adjusted_score, 20)
        degree_gap = education_validation.get('degree_level_gap', {})
        field_gap = education_validation.get('field_of_study_gap', {})

        if degree_gap:
            penalties.append(f"DEALBREAKER: Requires {degree_gap['required']} degree, candidate has {degree_gap['found']} (Score capped at 20%)")
        elif field_gap:
            penalties.append(f"DEALBREAKER: Requires {field_gap['required_field']} degree, not found on resume (Score capped at 20%)")

    # WARNING: Education preferred but not required
    elif education_validation.get('severity') == 'WARNING':
        adjusted_score = adjusted_score * 0.85  # 15% penalty
        penalties.append("Education requirement not fully met (-15%)")

    # DEALBREAKER: Experience requirement not met (3+ year gap)
    if experience_validation.get('severity') == 'DEALBREAKER':
        adjusted_score = min(adjusted_score, 25)
        gap = experience_validation['min_required'] - experience_validation['resume_years']
        penalties.append(f"DEALBREAKER: Requires {experience_validation['min_required']}+ years, candidate has {experience_validation['resume_years']} ({gap} year gap) (Score capped at 25%)")

    # WARNING: Experience gap of 1-2 years
    elif experience_validation.get('severity') == 'WARNING' and not experience_validation.get('meets_minimum'):
        adjusted_score = adjusted_score * 0.90  # 10% penalty
        gap = experience_validation['min_required'] - experience_validation['resume_years']
        penalties.append(f"Experience gap: Requires {experience_validation['min_required']}+ years, candidate has {experience_validation['resume_years']} (-10%)")

    # Overqualification warning
    elif experience_validation.get('overqualified'):
        # Don't penalize, just note it
        penalties.append(f"NOTE: Candidate may be overqualified ({experience_validation['resume_years']} years for {experience_validation['min_required']}+ year role)")

    # Ensure score doesn't go below 0 or above 100
    adjusted_score = max(0, min(100, adjusted_score))

    return {
        'adjusted_score': round(adjusted_score, 1),
        'penalties_applied': penalties,
        'original_score': round(base_score, 1)
    }
