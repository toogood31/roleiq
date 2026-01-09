"""
Transferable Skills Mapping System
Maps skills across industries/domains to help career changers
Identifies universally applicable skills vs. domain-specific ones
"""
from typing import Set, List, Tuple, Dict
from rapidfuzz import fuzz

# Universal skills that transfer across ALL industries
UNIVERSAL_SKILLS = {
    # Communication
    'communication', 'written communication', 'verbal communication',
    'presentation', 'public speaking', 'technical writing', 'documentation',

    # Leadership & Management
    'leadership', 'team leadership', 'project management', 'people management',
    'stakeholder management', 'change management', 'strategic planning',
    'decision making', 'problem solving', 'critical thinking',

    # Collaboration
    'teamwork', 'collaboration', 'cross-functional collaboration',
    'interpersonal skills', 'relationship building', 'networking',

    # Organization & Planning
    'time management', 'organization', 'prioritization', 'planning',
    'multitasking', 'attention to detail', 'process improvement',

    # Adaptability
    'adaptability', 'flexibility', 'learning agility', 'innovation',
    'creativity', 'resourcefulness',

    # Business Skills
    'budget management', 'financial analysis', 'data analysis',
    'reporting', 'metrics tracking', 'kpi management',
    'client relations', 'customer service', 'negotiation',

    # Project & Process
    'agile', 'scrum', 'waterfall', 'kanban', 'lean', 'six sigma',
    'project planning', 'risk management', 'quality assurance'
}

# Domain-specific skill mappings
# Format: {skill_in_domain_A: [(skill_in_domain_B, similarity_score), ...]}
DOMAIN_SKILL_MAPPINGS = {
    # Technical/Software → Management/Leadership
    'software architecture': [
        ('system design', 0.95),
        ('technical strategy', 0.90),
        ('solution architecture', 0.85)
    ],
    'code review': [
        ('quality assurance', 0.85),
        ('peer review', 0.90),
        ('technical oversight', 0.80)
    ],
    'technical mentoring': [
        ('coaching', 0.90),
        ('training', 0.85),
        ('knowledge transfer', 0.85)
    ],

    # Healthcare → General Business
    'patient care': [
        ('client relations', 0.80),
        ('customer service', 0.75),
        ('stakeholder management', 0.70)
    ],
    'medical records': [
        ('data management', 0.85),
        ('documentation', 0.90),
        ('compliance', 0.80)
    ],
    'clinical protocols': [
        ('standard operating procedures', 0.90),
        ('process management', 0.85),
        ('quality standards', 0.80)
    ],

    # Education → Corporate Training
    'curriculum development': [
        ('training program design', 0.95),
        ('content development', 0.90),
        ('instructional design', 0.95)
    ],
    'classroom management': [
        ('group facilitation', 0.85),
        ('workshop delivery', 0.80),
        ('audience engagement', 0.75)
    ],
    'student assessment': [
        ('performance evaluation', 0.90),
        ('competency assessment', 0.85),
        ('feedback delivery', 0.80)
    ],

    # Sales → Account Management
    'prospecting': [
        ('lead generation', 0.95),
        ('business development', 0.90),
        ('client acquisition', 0.85)
    ],
    'closing deals': [
        ('contract negotiation', 0.90),
        ('stakeholder alignment', 0.75),
        ('decision facilitation', 0.70)
    ],
    'pipeline management': [
        ('opportunity tracking', 0.95),
        ('forecasting', 0.85),
        ('resource planning', 0.75)
    ],

    # Finance → General Analytics
    'financial modeling': [
        ('data modeling', 0.85),
        ('predictive analysis', 0.80),
        ('scenario planning', 0.85)
    ],
    'variance analysis': [
        ('performance analysis', 0.90),
        ('root cause analysis', 0.85),
        ('trend analysis', 0.85)
    ],
    'budgeting': [
        ('resource allocation', 0.90),
        ('financial planning', 0.95),
        ('cost management', 0.85)
    ],

    # Military → Corporate
    'mission planning': [
        ('strategic planning', 0.90),
        ('project planning', 0.85),
        ('operational planning', 0.90)
    ],
    'unit leadership': [
        ('team leadership', 0.95),
        ('people management', 0.90),
        ('personnel development', 0.85)
    ],
    'logistics coordination': [
        ('supply chain management', 0.90),
        ('operations management', 0.85),
        ('resource coordination', 0.90)
    ],

    # Research → Product Development
    'research methodology': [
        ('analytical framework', 0.85),
        ('data collection', 0.90),
        ('systematic analysis', 0.85)
    ],
    'literature review': [
        ('competitive analysis', 0.80),
        ('market research', 0.75),
        ('landscape assessment', 0.75)
    ],
    'hypothesis testing': [
        ('a/b testing', 0.90),
        ('experimentation', 0.95),
        ('validation', 0.85)
    ],

    # Marketing → Product Management
    'market segmentation': [
        ('user segmentation', 0.95),
        ('target audience analysis', 0.90),
        ('persona development', 0.85)
    ],
    'campaign management': [
        ('program management', 0.85),
        ('initiative coordination', 0.80),
        ('launch management', 0.85)
    ],
    'brand strategy': [
        ('product positioning', 0.90),
        ('value proposition', 0.85),
        ('competitive differentiation', 0.80)
    ]
}


def is_universal_skill(skill: str) -> bool:
    """
    Check if a skill is universally transferable across industries

    Args:
        skill: Skill name

    Returns:
        True if skill is universal, False otherwise
    """
    skill_lower = skill.lower().strip()

    # Direct match
    if skill_lower in UNIVERSAL_SKILLS:
        return True

    # Fuzzy match for variations
    for universal in UNIVERSAL_SKILLS:
        if fuzz.ratio(skill_lower, universal) >= 90:
            return True

    return False


def find_transferable_match(skill: str, threshold: float = 0.70) -> List[Tuple[str, float]]:
    """
    Find transferable skills for a given skill

    Args:
        skill: Source skill
        threshold: Minimum similarity score to consider (0-1)

    Returns:
        List of (target_skill, similarity_score) tuples
    """
    skill_lower = skill.lower().strip()
    matches = []

    # Check if skill has direct mappings
    if skill_lower in DOMAIN_SKILL_MAPPINGS:
        for target_skill, score in DOMAIN_SKILL_MAPPINGS[skill_lower]:
            if score >= threshold:
                matches.append((target_skill, score))

    # Check reverse mappings (if target skill is in our domain mappings)
    for source_skill, target_list in DOMAIN_SKILL_MAPPINGS.items():
        for target_skill, score in target_list:
            if fuzz.ratio(skill_lower, target_skill) >= 85:
                if score >= threshold:
                    matches.append((source_skill, score))

    return matches


def calculate_transferable_coverage(
    resume_skills,
    jd_skills,
    exact_matches
) -> Dict:
    """
    Calculate how many JD skills can be covered by transferable skills

    Args:
        resume_skills: Skills from resume (set or list)
        jd_skills: Skills from JD (set or list)
        exact_matches: Skills already matched exactly (set or list)

    Returns:
        Dict with transferable skill analysis
    """
    # Convert to sets if needed
    resume_skills_set = set(resume_skills) if isinstance(resume_skills, list) else resume_skills
    jd_skills_set = set(jd_skills) if isinstance(jd_skills, list) else jd_skills
    exact_matches_set = set(exact_matches) if isinstance(exact_matches, list) else exact_matches

    # Skills that need transferable matching (not already matched)
    remaining_jd_skills = jd_skills_set - exact_matches_set

    transferable_matches = []
    universal_matches = []

    for jd_skill in remaining_jd_skills:
        jd_skill_lower = jd_skill.lower().strip()

        # Check if it's a universal skill
        if is_universal_skill(jd_skill):
            # See if resume has this universal skill
            for resume_skill in resume_skills_set:
                if is_universal_skill(resume_skill):
                    resume_lower = resume_skill.lower().strip()
                    similarity = fuzz.ratio(jd_skill_lower, resume_lower) / 100.0
                    if similarity >= 0.75:
                        universal_matches.append({
                            'jd_skill': jd_skill,
                            'resume_skill': resume_skill,
                            'score': similarity,
                            'type': 'universal'
                        })
                        break

        # Check for domain transferable skills
        for resume_skill in resume_skills_set:
            resume_lower = resume_skill.lower().strip()

            # Check if resume skill can transfer to JD skill
            resume_transfers = find_transferable_match(resume_lower, threshold=0.70)
            for transfer_skill, transfer_score in resume_transfers:
                if fuzz.ratio(jd_skill_lower, transfer_skill) >= 75:
                    transferable_matches.append({
                        'jd_skill': jd_skill,
                        'resume_skill': resume_skill,
                        'transfers_to': transfer_skill,
                        'score': transfer_score,
                        'type': 'domain_transfer'
                    })
                    break

            # Check if JD skill can transfer from resume skill
            jd_transfers = find_transferable_match(jd_skill_lower, threshold=0.70)
            for transfer_skill, transfer_score in jd_transfers:
                if fuzz.ratio(resume_lower, transfer_skill) >= 75:
                    transferable_matches.append({
                        'jd_skill': jd_skill,
                        'resume_skill': resume_skill,
                        'transfers_from': transfer_skill,
                        'score': transfer_score,
                        'type': 'domain_transfer'
                    })
                    break

    # Combine all matches
    all_transferable = universal_matches + transferable_matches

    # Count unique JD skills covered
    covered_jd_skills = set(match['jd_skill'] for match in all_transferable)

    return {
        'universal_matches': universal_matches,
        'domain_transfers': transferable_matches,
        'all_matches': all_transferable,
        'coverage_count': len(covered_jd_skills),
        'coverage_percentage': (len(covered_jd_skills) / len(remaining_jd_skills) * 100) if remaining_jd_skills else 0,
        'total_jd_skills_remaining': len(remaining_jd_skills)
    }


def identify_career_change_readiness(
    resume_skills: Set[str],
    jd_skills: Set[str],
    exact_match_pct: float
) -> Dict:
    """
    Assess candidate's readiness for a career change based on transferable skills

    Args:
        resume_skills: Skills from resume
        jd_skills: Skills from JD
        exact_match_pct: Percentage of exact skill matches (0-100)

    Returns:
        Dict with career change readiness assessment
    """
    # Count universal skills in resume
    resume_universal = sum(1 for skill in resume_skills if is_universal_skill(skill))
    jd_universal = sum(1 for skill in jd_skills if is_universal_skill(skill))

    # Calculate universal skill coverage
    universal_coverage = (resume_universal / jd_universal * 100) if jd_universal > 0 else 0

    # Determine readiness level
    if exact_match_pct >= 60:
        readiness = 'strong'
        explanation = 'High direct skill match - well-positioned for this role'
    elif exact_match_pct >= 40 and universal_coverage >= 70:
        readiness = 'moderate'
        explanation = 'Good transferable skills - career transition feasible with some upskilling'
    elif exact_match_pct >= 25 and universal_coverage >= 50:
        readiness = 'developing'
        explanation = 'Some relevant experience - would benefit from targeted training'
    else:
        readiness = 'early'
        explanation = 'Significant career pivot - requires substantial skill development'

    return {
        'readiness_level': readiness,
        'explanation': explanation,
        'universal_skills_in_resume': resume_universal,
        'universal_skills_in_jd': jd_universal,
        'universal_coverage_pct': round(universal_coverage, 1),
        'exact_match_pct': exact_match_pct,
        'recommendation': _get_career_change_recommendation(readiness, exact_match_pct)
    }


def _get_career_change_recommendation(readiness: str, exact_match_pct: float) -> str:
    """Get recommendation based on career change readiness"""
    recommendations = {
        'strong': 'Apply confidently - your skills align well with this role',
        'moderate': 'Consider applying - highlight transferable skills in your application',
        'developing': 'Build domain-specific skills first, then apply',
        'early': 'Focus on gaining foundational skills before applying'
    }
    return recommendations.get(readiness, 'Continue building relevant experience')
