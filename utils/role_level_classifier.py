"""
Role Level Classification System
Automatically detects if a role is IC, Manager, or Executive level
Adjusts matching expectations based on role level differences
"""
from typing import Tuple, Dict
import re

# Keywords indicating management/leadership roles
MANAGER_KEYWORDS = {
    'manager', 'lead', 'supervisor', 'coordinator', 'head of',
    'team lead', 'tech lead', 'engineering manager', 'product manager',
    'managing', 'leadership', 'manage team', 'direct reports',
    'people management', 'team management', 'staff management'
}

# Keywords indicating executive roles
EXECUTIVE_KEYWORDS = {
    'director', 'vp', 'vice president', 'chief', 'ceo', 'cto', 'cfo', 'coo',
    'executive', 'president', 'head of department', 'c-level', 'c-suite',
    'senior director', 'group director', 'general manager', 'country manager',
    'controller'  # Financial controller is typically executive/senior management
}

# Keywords indicating individual contributor roles
IC_KEYWORDS = {
    'engineer', 'developer', 'analyst', 'specialist', 'consultant',
    'designer', 'researcher', 'scientist', 'associate', 'coordinator',
    'individual contributor', 'ic', 'staff engineer', 'principal engineer',
    'senior engineer', 'junior', 'entry level'
}


def classify_role_level(text: str) -> Tuple[str, float]:
    """
    Classify role level from text (resume or JD)

    Args:
        text: Resume or job description text

    Returns:
        Tuple of (role_level, confidence)
        - role_level: 'ic', 'manager', or 'executive'
        - confidence: 0.0 to 1.0
    """
    text_lower = text.lower()

    # Count keyword matches
    executive_score = sum(1 for kw in EXECUTIVE_KEYWORDS if kw in text_lower)
    manager_score = sum(1 for kw in MANAGER_KEYWORDS if kw in text_lower)
    ic_score = sum(1 for kw in IC_KEYWORDS if kw in text_lower)

    # Strong executive indicators (titles)
    if any(title in text_lower for title in ['chief', 'ceo', 'cto', 'cfo', 'coo', 'vice president', 'vp of']):
        return ('executive', 0.95)

    # Strong manager indicators
    if any(phrase in text_lower for phrase in ['manage team', 'lead team', 'direct reports', 'people management']):
        return ('manager', 0.90)

    # Determine level based on scores
    total_score = executive_score + manager_score + ic_score

    if total_score == 0:
        # No clear indicators, assume IC (most common)
        return ('ic', 0.5)

    # Calculate confidence based on score separation
    max_score = max(executive_score, manager_score, ic_score)
    confidence = min(0.95, 0.6 + (max_score / total_score * 0.35))

    if executive_score >= manager_score and executive_score >= ic_score:
        return ('executive', confidence)
    elif manager_score >= ic_score:
        return ('manager', confidence)
    else:
        return ('ic', confidence)


def get_role_level_expectations(role_level: str) -> Dict[str, any]:
    """
    Get matching expectations for different role levels

    Args:
        role_level: 'ic', 'manager', or 'executive'

    Returns:
        Dict with expectations for this role level
    """
    expectations = {
        'ic': {
            'technical_weight': 0.7,  # Technical skills heavily weighted
            'soft_skills_weight': 0.3,
            'expected_skill_specificity': 'high',  # Expect specific tools/technologies
            'min_technical_match': 0.6,  # Need 60%+ technical match
            'description': 'Individual Contributor - Focus on technical expertise'
        },
        'manager': {
            'technical_weight': 0.4,  # Technical skills less critical
            'soft_skills_weight': 0.6,  # Leadership/management more important
            'expected_skill_specificity': 'medium',  # Mix of specific and broad
            'min_technical_match': 0.4,  # Only 40%+ technical match needed
            'description': 'Manager - Focus on leadership and people management'
        },
        'executive': {
            'technical_weight': 0.2,  # Technical background helpful but not primary
            'soft_skills_weight': 0.8,  # Strategy, vision, leadership paramount
            'expected_skill_specificity': 'low',  # Broad strategic concepts
            'min_technical_match': 0.2,  # Only 20%+ technical match needed
            'description': 'Executive - Focus on strategy and organizational leadership'
        }
    }

    return expectations.get(role_level, expectations['ic'])


def adjust_match_score(
    base_score: float,
    resume_role_level: str,
    jd_role_level: str,
    technical_match_pct: float,
    soft_skills_match_pct: float
) -> Tuple[float, str]:
    """
    Adjust match score based on role level alignment

    Args:
        base_score: Original match score (0-100)
        resume_role_level: Candidate's role level
        jd_role_level: Job's role level
        technical_match_pct: % of technical skills matched (0-100)
        soft_skills_match_pct: % of soft skills matched (0-100)

    Returns:
        Tuple of (adjusted_score, explanation)
    """
    resume_exp = get_role_level_expectations(resume_role_level)
    jd_exp = get_role_level_expectations(jd_role_level)

    # Calculate weighted score based on JD expectations
    weighted_score = (
        technical_match_pct * jd_exp['technical_weight'] +
        soft_skills_match_pct * jd_exp['soft_skills_weight']
    )

    # Role level alignment bonus/penalty
    level_hierarchy = {'ic': 0, 'manager': 1, 'executive': 2}
    resume_level_num = level_hierarchy.get(resume_role_level, 0)
    jd_level_num = level_hierarchy.get(jd_role_level, 0)

    level_diff = resume_level_num - jd_level_num

    if level_diff == 0:
        # Same level - no adjustment
        adjustment = 0
        explanation = f"Role levels aligned ({resume_role_level} → {jd_role_level})"
    elif level_diff == 1:
        # One level up (e.g., Manager → IC) - slight bonus for overqualified
        adjustment = 5
        explanation = f"Candidate is one level senior ({resume_role_level} → {jd_role_level}) - bonus for experience"
    elif level_diff == -1:
        # Stepping up (Manager → Director, IC → Manager)
        # Check if they're ready based on multiple signals

        # Strong indicator: high base score + good soft skills = ready to step up
        if base_score >= 70 and soft_skills_match_pct >= 60:
            adjustment = 5  # Small bonus for natural progression
            explanation = f"Candidate demonstrates readiness to step up ({resume_role_level} → {jd_role_level})"

        # Moderate: decent skills, ready to step up with some development
        elif soft_skills_match_pct >= 50:
            adjustment = 0  # No penalty
            explanation = f"Candidate ready to step up ({resume_role_level} → {jd_role_level}) - sufficient soft skills"

        # Weak: not ready yet
        else:
            adjustment = -10
            explanation = f"Candidate may need more experience before stepping up ({resume_role_level} → {jd_role_level})"
    elif level_diff >= 2:
        # Significantly overqualified
        adjustment = 10
        explanation = f"Candidate significantly overqualified ({resume_role_level} → {jd_role_level})"
    else:
        # Significantly underqualified
        adjustment = -15
        explanation = f"Candidate may be underqualified for level ({resume_role_level} → {jd_role_level})"

    # Combine base score with weighted score and adjustment
    # Use 95% base score + 5% weighted score (less aggressive), then apply adjustment
    # Cap total adjustment at ±20 points to prevent extreme penalties
    weighted_component = (base_score * 0.95 + weighted_score * 0.05) + adjustment

    # Limit how much the role adjustment can change the score
    max_change = 20
    if weighted_component < base_score - max_change:
        final_score = base_score - max_change
    elif weighted_component > base_score + max_change:
        final_score = base_score + max_change
    else:
        final_score = weighted_component

    final_score = max(0, min(100, final_score))  # Clamp to 0-100

    return final_score, explanation


def extract_soft_skills(skills) -> set:
    """
    Extract soft skills from a skill set or list

    Args:
        skills: Set or list of all skills

    Returns:
        Set of soft skills
    """
    soft_skill_keywords = {
        'leadership', 'management', 'communication', 'collaboration', 'teamwork',
        'problem solving', 'critical thinking', 'adaptability', 'creativity',
        'time management', 'organization', 'strategic planning', 'decision making',
        'negotiation', 'conflict resolution', 'mentoring', 'coaching', 'presentation',
        'stakeholder management', 'project management', 'people management',
        'team building', 'emotional intelligence', 'interpersonal', 'public speaking'
    }

    # Convert to set if it's a list
    skills_set = set(skills) if isinstance(skills, list) else skills

    soft_skills = set()
    for skill in skills_set:
        skill_lower = skill.lower()
        if any(soft_kw in skill_lower for soft_kw in soft_skill_keywords):
            soft_skills.add(skill)

    return soft_skills


def extract_technical_skills(skills) -> set:
    """
    Extract technical skills from a skill set or list

    Args:
        skills: Set or list of all skills

    Returns:
        Set of technical skills (non-soft skills)
    """
    # Convert to set if it's a list
    skills_set = set(skills) if isinstance(skills, list) else skills

    soft_skills = extract_soft_skills(skills)
    return skills_set - soft_skills
