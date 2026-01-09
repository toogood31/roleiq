"""
Post-extraction skill filtering
Removes phrases that aren't actually skills
"""
import re
from typing import Set

# ========== UNIVERSAL FILTERS (Work across ALL industries) ==========

# Phrases that should never be treated as skills
NOISE_PATTERNS = [
    # Determiners/demonstratives (universal filter)
    r'^(these|those|that|this)\s+',  # "these opportunities", "those skills"

    # Quantifiers (universal filter)
    r'^(each|every|all|whole|entire|some|any|many)\s+',  # "each individual student"

    # Temporal/contextual terms (universal filter)
    r'\b(basis|schedule|opportunity|opportunities|success|accolades|achievements?)$',
    r'^(case|daily|weekly|monthly|seasonal?|annual)\s+',  # "case basis", "daily schedule"

    # Generic outcome/result phrases (universal filter)
    r'^\w+\s+(success|achievement|outcome|result|goal)s?$',  # "academic success", "student achievement"

    # Generic organizational terms (universal filter)
    r'^\w+\s+(budget|schedule|plan|program|event|meeting|conference)s?$',  # "department budget", "game schedule"

    # Articles + role titles (not skills)
    r'^an?\s+\w+\s+(administrator|coordinator|director|manager|specialist|analyst)',

    # Job titles (universal filter) - catch at beginning or end
    r'^(analyst|administrator|coordinator|director|manager|specialist|officer|executive|lead|supervisor)\s+',
    r'\s+(analyst|administrator|coordinator|director|manager|specialist|officer|executive|lead|supervisor)$',
    r'^(senior|junior|lead|staff|principal|associate|assistant)\s+',  # "senior analyst", "lead developer"

    # Education-specific patterns
    r'\w+\s+(student|teacher|school|program)$',  # "middle school", "social studies teacher"
    r'^(elementary|middle|high)\s+school',
    r'^individual\s+\w+$',  # "individual student"
    r'^\w+\s+athlete$',  # "student athlete"
    r'^\w+\s+(education|learning)$',  # "special education"
]

# Educational context terms (not skills)
EDUCATION_CONTEXT = {
    'elementary school', 'middle school', 'high school', 'special education',
    'individualized education plans', 'classified students', 'social studies teacher',
    'individual student', 'each individual student', 'whole student athlete',
    'entire high school program', 'an athletic administrator', 'student athlete',
    'individual students', 'entire student', 'each student', 'jv', 'varsity',
    'athletic events', 'school coaches', 'academic coordinator', 'track program responsibilities',
    'student athlete strength', 'student well-being', 'student success',
    'student engagement', 'student involvement', 'student learning'
}

# ========== UNIVERSAL NON-SKILLS (Apply to ALL industries) ==========

# Vague single words that are never skills (universal)
VAGUE_SINGLE_WORDS = {
    'basis', 'schedule', 'schedules', 'opportunity', 'opportunities',
    'success', 'accolades', 'achievement', 'achievements', 'outcome', 'outcomes',
    'result', 'results', 'goal', 'goals', 'event', 'events', 'meeting', 'meetings',
    'alignment', 'support', 'effectiveness', 'consistency', 'organization'
}

# Generic descriptors that aren't skills
GENERIC_DESCRIPTORS = {
    # Universal non-skills
    'these opportunities', 'those opportunities', 'case basis', 'daily basis',
    'season accolades', 'game schedules', 'academic success', 'department budget',
    'strategic support', 'global alignment', 'alignment consistency',
    'alignment consistency organization',

    # Malformed concatenated text (extraction errors)
    'companys total compensation programsglobal alignment',
    'programsglobal alignment',  # Partial malformed match

    # Job titles (compensation/HR specific)
    'compensation analyst', 'compensation administrator', 'compensation manager',
    'compensation specialist', 'compensation director',

    # Education-specific
    'consistent parent contact', 'parent contact', 'potential participation',
    'corrective strategies', 'summer utilization', 'unit outcomes',
    'performance indicators', 'campus engagement', 'budget projections',
    'budget requests', 'foundation accounts', 'conference regulations',
    'cooperative working relationships', 'interpersonal relations'
}


def is_valid_skill(skill: str) -> bool:
    """Check if extracted phrase is actually a skill"""
    skill_lower = skill.lower().strip()

    # Remove educational context
    if skill_lower in EDUCATION_CONTEXT:
        return False

    # Remove generic descriptors
    if skill_lower in GENERIC_DESCRIPTORS:
        return False

    # Filter vague single words (universal filter)
    if skill_lower in VAGUE_SINGLE_WORDS:
        return False

    # Filter noise patterns
    for pattern in NOISE_PATTERNS:
        if re.match(pattern, skill_lower):
            return False

    # Must be at least 3 characters
    if len(skill_lower) < 3:
        return False

    # Filter out phrases with too many words (likely not a skill)
    word_count = len(skill_lower.split())
    if word_count > 5:
        return False

    # Detect malformed text (words mashed together without spaces)
    # Look for patterns like "programsglobal" where lowercase is followed by uppercase-origin word
    # Also check for excessive length of individual "words" (likely concatenated)
    words = skill_lower.split()
    for word in words:
        # If a single "word" is longer than 20 chars, likely malformed
        if len(word) > 20:
            return False

        # Check for telltale signs of concatenation like "programsglobal" or "companyscompensation"
        # These would have multiple root words without proper spacing
        if len(word) > 15:  # Only check longer words
            # Simple heuristic: if word has repeated common patterns, might be concatenated
            common_endings = ['tion', 'ment', 'ness', 'ship', 'ing', 'ed', 'er', 'or', 'ist', 'ism']
            ending_count = sum(1 for ending in common_endings if ending in word)
            if ending_count > 1:  # More than one ending pattern suggests concatenation
                return False

    return True


def filter_skills(skills: Set[str]) -> Set[str]:
    """Remove non-skill phrases from extracted skills"""
    return {s for s in skills if is_valid_skill(s)}
