"""
Skill Taxonomy & Hierarchy System
Enables hierarchical skill matching and abbreviation normalization
"""
from typing import Set, Dict, List, Tuple
from rapidfuzz import fuzz

# Skill Hierarchy: child_skill → (parent_skill, category)
# This allows "React" to match "JavaScript frameworks" and "Frontend development"
SKILL_HIERARCHY = {
    # Frontend Technologies
    'react': ('javascript frameworks', 'frontend development'),
    'react.js': ('javascript frameworks', 'frontend development'),
    'reactjs': ('javascript frameworks', 'frontend development'),
    'vue': ('javascript frameworks', 'frontend development'),
    'vue.js': ('javascript frameworks', 'frontend development'),
    'angular': ('javascript frameworks', 'frontend development'),
    'angularjs': ('javascript frameworks', 'frontend development'),
    'svelte': ('javascript frameworks', 'frontend development'),
    'next.js': ('javascript frameworks', 'frontend development'),
    'nuxt.js': ('javascript frameworks', 'frontend development'),
    'redux': ('state management', 'frontend development'),
    'mobx': ('state management', 'frontend development'),
    'vuex': ('state management', 'frontend development'),
    'html': ('web fundamentals', 'frontend development'),
    'html5': ('web fundamentals', 'frontend development'),
    'css': ('web fundamentals', 'frontend development'),
    'css3': ('web fundamentals', 'frontend development'),
    'sass': ('css preprocessors', 'frontend development'),
    'scss': ('css preprocessors', 'frontend development'),
    'less': ('css preprocessors', 'frontend development'),
    'tailwind': ('css frameworks', 'frontend development'),
    'bootstrap': ('css frameworks', 'frontend development'),

    # Backend Technologies
    'node.js': ('backend frameworks', 'backend development'),
    'nodejs': ('backend frameworks', 'backend development'),
    'express': ('backend frameworks', 'backend development'),
    'express.js': ('backend frameworks', 'backend development'),
    'django': ('backend frameworks', 'backend development'),
    'flask': ('backend frameworks', 'backend development'),
    'fastapi': ('backend frameworks', 'backend development'),
    'spring': ('backend frameworks', 'backend development'),
    'spring boot': ('backend frameworks', 'backend development'),
    'ruby on rails': ('backend frameworks', 'backend development'),
    'rails': ('backend frameworks', 'backend development'),
    'asp.net': ('backend frameworks', 'backend development'),

    # Programming Languages
    'javascript': ('programming languages', 'software development'),
    'typescript': ('programming languages', 'software development'),
    'python': ('programming languages', 'software development'),
    'java': ('programming languages', 'software development'),
    'c#': ('programming languages', 'software development'),
    'c++': ('programming languages', 'software development'),
    'go': ('programming languages', 'software development'),
    'golang': ('programming languages', 'software development'),
    'rust': ('programming languages', 'software development'),
    'ruby': ('programming languages', 'software development'),
    'php': ('programming languages', 'software development'),
    'swift': ('programming languages', 'software development'),
    'kotlin': ('programming languages', 'software development'),
    'scala': ('programming languages', 'software development'),
    'r': ('programming languages', 'software development'),

    # Databases
    'postgresql': ('sql databases', 'database management'),
    'postgres': ('sql databases', 'database management'),
    'mysql': ('sql databases', 'database management'),
    'sql server': ('sql databases', 'database management'),
    'oracle': ('sql databases', 'database management'),
    'mongodb': ('nosql databases', 'database management'),
    'redis': ('nosql databases', 'database management'),
    'dynamodb': ('nosql databases', 'database management'),
    'cassandra': ('nosql databases', 'database management'),
    'elasticsearch': ('search databases', 'database management'),

    # DevOps & Cloud
    'docker': ('containerization', 'devops'),
    'kubernetes': ('container orchestration', 'devops'),
    'k8s': ('container orchestration', 'devops'),
    'aws': ('cloud platforms', 'devops'),
    'amazon web services': ('cloud platforms', 'devops'),
    'azure': ('cloud platforms', 'devops'),
    'microsoft azure': ('cloud platforms', 'devops'),
    'gcp': ('cloud platforms', 'devops'),
    'google cloud': ('cloud platforms', 'devops'),
    'terraform': ('infrastructure as code', 'devops'),
    'ansible': ('configuration management', 'devops'),
    'jenkins': ('ci/cd', 'devops'),
    'github actions': ('ci/cd', 'devops'),
    'gitlab ci': ('ci/cd', 'devops'),
    'circleci': ('ci/cd', 'devops'),

    # Data Science & ML
    'machine learning': ('artificial intelligence', 'data science'),
    'deep learning': ('artificial intelligence', 'data science'),
    'neural networks': ('artificial intelligence', 'data science'),
    'natural language processing': ('artificial intelligence', 'data science'),
    'nlp': ('artificial intelligence', 'data science'),
    'computer vision': ('artificial intelligence', 'data science'),
    'tensorflow': ('ml frameworks', 'data science'),
    'pytorch': ('ml frameworks', 'data science'),
    'scikit-learn': ('ml frameworks', 'data science'),
    'sklearn': ('ml frameworks', 'data science'),
    'pandas': ('data analysis', 'data science'),
    'numpy': ('data analysis', 'data science'),
    'matplotlib': ('data visualization', 'data science'),
    'seaborn': ('data visualization', 'data science'),
    'tableau': ('data visualization', 'data science'),
    'power bi': ('data visualization', 'data science'),

    # Business & Management
    'project management': ('management', 'business operations'),
    'product management': ('management', 'business operations'),
    'team leadership': ('management', 'business operations'),
    'people management': ('management', 'business operations'),
    'stakeholder management': ('management', 'business operations'),
    'budget management': ('financial management', 'business operations'),
    'financial planning': ('financial management', 'business operations'),
    'strategic planning': ('strategy', 'business operations'),
    'agile': ('project methodologies', 'business operations'),
    'scrum': ('project methodologies', 'business operations'),
    'kanban': ('project methodologies', 'business operations'),
    'waterfall': ('project methodologies', 'business operations'),

    # Marketing & Sales
    'digital marketing': ('marketing', 'sales and marketing'),
    'content marketing': ('marketing', 'sales and marketing'),
    'social media marketing': ('marketing', 'sales and marketing'),
    'email marketing': ('marketing', 'sales and marketing'),
    'seo': ('digital marketing', 'sales and marketing'),
    'sem': ('digital marketing', 'sales and marketing'),
    'google analytics': ('analytics', 'sales and marketing'),
    'salesforce': ('crm', 'sales and marketing'),
    'hubspot': ('crm', 'sales and marketing'),

    # Design
    'ui design': ('design', 'user experience'),
    'ux design': ('design', 'user experience'),
    'user interface design': ('design', 'user experience'),
    'user experience design': ('design', 'user experience'),
    'graphic design': ('design', 'visual design'),
    'figma': ('design tools', 'user experience'),
    'sketch': ('design tools', 'user experience'),
    'adobe xd': ('design tools', 'user experience'),
    'photoshop': ('design tools', 'visual design'),
    'illustrator': ('design tools', 'visual design'),
}

# Abbreviations and Synonyms: abbreviation/synonym → canonical form
SKILL_ABBREVATIONS = {
    # Programming & Tech
    'js': 'javascript',
    'ts': 'typescript',
    'py': 'python',
    'rb': 'ruby',
    'c#': 'c sharp',
    'k8s': 'kubernetes',
    'psql': 'postgresql',
    'pg': 'postgresql',
    'tf': 'tensorflow',
    'sk-learn': 'scikit-learn',
    'np': 'numpy',
    'pd': 'pandas',
    'cv': 'computer vision',
    'dl': 'deep learning',
    'nn': 'neural networks',

    # Cloud & DevOps
    'ec2': 'amazon ec2',
    's3': 'amazon s3',
    'rds': 'amazon rds',
    'gke': 'google kubernetes engine',
    'aks': 'azure kubernetes service',
    'eks': 'amazon eks',
    'ci/cd': 'continuous integration continuous deployment',
    'iac': 'infrastructure as code',

    # Business & Management (context-dependent)
    'pm': 'project management',  # Could also be Product Manager
    'pmo': 'project management office',
    'kpi': 'key performance indicators',
    'roi': 'return on investment',
    'p&l': 'profit and loss',
    'b2b': 'business to business',
    'b2c': 'business to consumer',
    'saas': 'software as a service',
    'paas': 'platform as a service',
    'iaas': 'infrastructure as a service',

    # Marketing
    'ctr': 'click through rate',
    'cpc': 'cost per click',
    'cpa': 'cost per acquisition',
    'cpm': 'cost per mille',
    'smm': 'social media marketing',
    'ppc': 'pay per click',

    # Data & Analytics
    'etl': 'extract transform load',
    'bi': 'business intelligence',
    'db': 'database',
    'dbms': 'database management system',
    'olap': 'online analytical processing',
    'oltp': 'online transaction processing',

    # General Business
    'hr': 'human resources',
    'r&d': 'research and development',
    'qa': 'quality assurance',
    'qc': 'quality control',
    'crm': 'customer relationship management',
    'erp': 'enterprise resource planning',
    'sop': 'standard operating procedures',
    'sow': 'statement of work',
}

# Synonym groups - skills that are essentially the same
SKILL_SYNONYMS = {
    'ml': 'machine learning',
    'ai': 'artificial intelligence',
    'frontend': 'front end',
    'front-end': 'front end',
    'backend': 'back end',
    'back-end': 'back end',
    'fullstack': 'full stack',
    'full-stack': 'full stack',
    'devops': 'dev ops',
    'ui/ux': 'ui ux',
    'rest api': 'restful api',
    'rest apis': 'restful api',
}


def normalize_skill(skill: str) -> str:
    """
    Normalize a skill name by expanding abbreviations and applying synonyms

    Args:
        skill: Raw skill name

    Returns:
        Normalized skill name
    """
    skill_lower = skill.lower().strip()

    # First check abbreviations
    if skill_lower in SKILL_ABBREVATIONS:
        return SKILL_ABBREVATIONS[skill_lower]

    # Then check synonyms
    if skill_lower in SKILL_SYNONYMS:
        return SKILL_SYNONYMS[skill_lower]

    return skill_lower


def get_skill_hierarchy(skill: str) -> List[str]:
    """
    Get the full hierarchy for a skill (skill → parent → category)

    Args:
        skill: Skill name

    Returns:
        List of skills from most specific to most general
        Example: 'react' → ['react', 'javascript frameworks', 'frontend development']
    """
    normalized = normalize_skill(skill)
    hierarchy = [normalized]

    if normalized in SKILL_HIERARCHY:
        parent, category = SKILL_HIERARCHY[normalized]
        hierarchy.append(parent)
        if category not in hierarchy:
            hierarchy.append(category)

    return hierarchy


def expand_skill_with_parents(skill: str) -> Set[str]:
    """
    Expand a skill to include its parent skills and categories

    Args:
        skill: Skill name

    Returns:
        Set of skill and all parent skills
    """
    return set(get_skill_hierarchy(skill))


def match_with_hierarchy(resume_skills: Set[str], jd_skills: Set[str]) -> Tuple[Set[str], Dict[str, str]]:
    """
    Match skills using hierarchical relationships

    Args:
        resume_skills: Skills from resume
        jd_skills: Skills from job description

    Returns:
        Tuple of (matched_skills, match_explanations)
        - matched_skills: Set of JD skills that were matched
        - match_explanations: Dict mapping matched JD skill → explanation
    """
    matched = set()
    explanations = {}

    # Normalize all skills first
    normalized_resume = {normalize_skill(s): s for s in resume_skills}
    normalized_jd = {normalize_skill(s): s for s in jd_skills}

    # For each JD skill, check if resume has it or a child skill
    for jd_norm, jd_original in normalized_jd.items():
        # Direct match after normalization
        if jd_norm in normalized_resume:
            matched.add(jd_original)
            explanations[jd_original] = f"Direct match (normalized)"
            continue

        # Check if any resume skill is a child of this JD skill
        for resume_norm, resume_original in normalized_resume.items():
            resume_hierarchy = get_skill_hierarchy(resume_norm)

            # If JD skill appears in resume skill's hierarchy, it's a match
            if jd_norm in resume_hierarchy:
                matched.add(jd_original)
                explanations[jd_original] = f"Hierarchical match via '{resume_original}'"
                break

        # Check if this JD skill is a child of any resume skill (resume is more general)
        if jd_original not in matched:
            jd_hierarchy = get_skill_hierarchy(jd_norm)
            for resume_norm in normalized_resume:
                if resume_norm in jd_hierarchy:
                    matched.add(jd_original)
                    explanations[jd_original] = f"General match (resume has broader '{normalized_resume[resume_norm]}')"
                    break

    return matched, explanations


def fuzzy_match_abbreviations(skill: str, candidates: List[str], threshold: int = 85) -> str:
    """
    Fuzzy match a skill against candidates, handling abbreviations

    Args:
        skill: Skill to match
        candidates: List of candidate skills
        threshold: Minimum fuzzy match score (0-100)

    Returns:
        Best matching candidate or original skill if no match
    """
    skill_norm = normalize_skill(skill)

    best_match = skill
    best_score = 0

    for candidate in candidates:
        candidate_norm = normalize_skill(candidate)
        score = fuzz.ratio(skill_norm, candidate_norm)

        if score > best_score and score >= threshold:
            best_score = score
            best_match = candidate

    return best_match
