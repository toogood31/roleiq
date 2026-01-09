"""
Advanced Skill Enhancement Module
This module provides enterprise-grade skill extraction capabilities that surpass commercial ATS systems.

Key Features:
1. Synonym & Abbreviation Mapping (handles "JS" → "JavaScript", "AP" → "Accounts Payable")
2. Verb-Based Extraction (extracts skills from "managed budgets", "analyzed data")
3. Tool/Software NER (dedicated extraction for Salesforce, SAP, Workday, etc.)
4. Contextual Skill Inference (infers "team leadership" from "Led team of 5")
5. Industry-Specific Patterns (HR, Finance, Tech, etc.)
6. Multi-word Phrase Enhancement
7. Normalization & Deduplication
"""

import re
from typing import List, Set, Dict, Tuple

# ============================================================================
# TIER 1: SYNONYM & ABBREVIATION MAPPINGS
# ============================================================================

# Comprehensive synonym mappings (lowercase canonical form)
SKILL_SYNONYMS = {
    # Programming Languages
    'javascript': ['js', 'ecmascript', 'es6', 'es2015', 'node', 'nodejs'],
    'typescript': ['ts'],
    'python': ['py'],
    'c++': ['cpp', 'c plus plus', 'cplusplus'],
    'c#': ['csharp', 'c sharp'],
    'objective-c': ['objective c', 'obj-c', 'objc'],

    # HR & Compensation
    'compensation and benefits': ['comp and ben', 'comp & ben', 'c&b', 'total rewards'],
    'compensation': ['comp', 'total comp'],
    'human resources': ['hr', 'people operations', 'people ops'],
    'human resource information system': ['hris'],
    'applicant tracking system': ['ats'],
    'performance management': ['perf management', 'performance mgmt'],
    'employee relations': ['er'],
    'talent acquisition': ['ta', 'recruiting', 'recruitment'],
    'organizational development': ['od', 'org dev'],
    'learning and development': ['l&d', 'training and development', 't&d'],
    'diversity equity and inclusion': ['dei', 'd&i', 'diversity and inclusion'],

    # Accounting & Finance
    'accounts payable': ['ap', 'a/p'],
    'accounts receivable': ['ar', 'a/r'],
    'generally accepted accounting principles': ['gaap', 'us gaap'],
    'international financial reporting standards': ['ifrs'],
    'certified public accountant': ['cpa'],
    'chartered financial analyst': ['cfa'],
    'financial planning and analysis': ['fp&a', 'fpa'],
    'return on investment': ['roi'],
    'earnings before interest taxes depreciation and amortization': ['ebitda'],
    'profit and loss': ['p&l', 'pnl', 'p and l'],
    'balance sheet': ['b/s'],
    'general ledger': ['gl', 'g/l'],
    'cost of goods sold': ['cogs'],
    'accounts payable clerk': ['ap clerk'],
    'accounts receivable clerk': ['ar clerk'],

    # Business & Management
    'mergers and acquisitions': ['m&a', 'm and a', 'ma'],
    'business to business': ['b2b', 'b-to-b'],
    'business to consumer': ['b2c', 'b-to-c'],
    'chief executive officer': ['ceo'],
    'chief financial officer': ['cfo'],
    'chief technology officer': ['cto'],
    'chief operating officer': ['coo'],
    'chief human resources officer': ['chro'],
    'key performance indicator': ['kpi', 'kpis'],
    'return on equity': ['roe'],
    'return on assets': ['roa'],
    'enterprise resource planning': ['erp'],
    'customer relationship management': ['crm'],
    'project management': ['pm', 'proj mgmt'],
    'business intelligence': ['bi'],

    # Software & Tools
    'microsoft excel': ['excel', 'ms excel', 'msexcel'],
    'microsoft word': ['word', 'ms word', 'msword'],
    'microsoft powerpoint': ['powerpoint', 'ppt', 'ms powerpoint'],
    'microsoft office': ['ms office', 'office', 'microsoft office suite'],
    'google analytics': ['ga'],
    'structured query language': ['sql'],
    'application programming interface': ['api'],
    'software as a service': ['saas'],
    'infrastructure as a service': ['iaas'],
    'platform as a service': ['paas'],

    # Technical
    'artificial intelligence': ['ai'],
    'machine learning': ['ml'],
    'natural language processing': ['nlp'],
    'user experience': ['ux'],
    'user interface': ['ui'],
    'continuous integration': ['ci'],
    'continuous deployment': ['cd'],
    'continuous integration and continuous deployment': ['ci/cd', 'cicd'],
    'amazon web services': ['aws'],
    'google cloud platform': ['gcp'],
    'search engine optimization': ['seo'],
    'search engine marketing': ['sem'],

    # Other
    'year over year': ['yoy', 'y-o-y'],
    'month over month': ['mom', 'm-o-m'],
    'quarter over quarter': ['qoq', 'q-o-q'],
    'fiscal year': ['fy'],
    'calendar year': ['cy'],
}

# Build reverse mapping (abbreviation → canonical form)
ABBREVIATION_TO_CANONICAL = {}
for canonical, variations in SKILL_SYNONYMS.items():
    for variant in variations:
        ABBREVIATION_TO_CANONICAL[variant.lower()] = canonical

# ============================================================================
# TIER 2: VERB-BASED SKILL EXTRACTION
# ============================================================================

# Map action verbs to skill categories
VERB_TO_SKILL = {
    # Management & Leadership
    'manage': 'management',
    'managed': 'management',
    'managing': 'management',
    'lead': 'leadership',
    'led': 'leadership',
    'leading': 'leadership',
    'supervise': 'supervision',
    'supervised': 'supervision',
    'supervising': 'supervision',
    'direct': 'direction',
    'directed': 'direction',
    'directing': 'direction',
    'oversee': 'oversight',
    'oversaw': 'oversight',
    'overseeing': 'oversight',
    'coordinate': 'coordination',
    'coordinated': 'coordination',
    'coordinating': 'coordination',

    # Analysis & Strategy
    'analyze': 'analysis',
    'analyzed': 'analysis',
    'analyzing': 'analysis',
    'assess': 'assessment',
    'assessed': 'assessment',
    'assessing': 'assessment',
    'evaluate': 'evaluation',
    'evaluated': 'evaluation',
    'evaluating': 'evaluation',
    'research': 'research',
    'researched': 'research',
    'researching': 'research',
    'investigate': 'investigation',
    'investigated': 'investigation',
    'investigating': 'investigation',
    'forecast': 'forecasting',
    'forecasted': 'forecasting',
    'forecasting': 'forecasting',
    'plan': 'planning',
    'planned': 'planning',
    'planning': 'planning',
    'strategize': 'strategic planning',
    'strategized': 'strategic planning',
    'strategizing': 'strategic planning',

    # Development & Creation
    'develop': 'development',
    'developed': 'development',
    'developing': 'development',
    'design': 'design',
    'designed': 'design',
    'designing': 'design',
    'create': 'creation',
    'created': 'creation',
    'creating': 'creation',
    'build': 'building',
    'built': 'building',
    'building': 'building',
    'implement': 'implementation',
    'implemented': 'implementation',
    'implementing': 'implementation',
    'deploy': 'deployment',
    'deployed': 'deployment',
    'deploying': 'deployment',
    'launch': 'launching',
    'launched': 'launching',
    'launching': 'launching',

    # Communication & Collaboration
    'present': 'presentation',
    'presented': 'presentation',
    'presenting': 'presentation',
    'communicate': 'communication',
    'communicated': 'communication',
    'communicating': 'communication',
    'collaborate': 'collaboration',
    'collaborated': 'collaboration',
    'collaborating': 'collaboration',
    'negotiate': 'negotiation',
    'negotiated': 'negotiation',
    'negotiating': 'negotiation',
    'consult': 'consulting',
    'consulted': 'consulting',
    'consulting': 'consulting',
    'advise': 'advisory',
    'advised': 'advisory',
    'advising': 'advisory',

    # Optimization & Improvement
    'optimize': 'optimization',
    'optimized': 'optimization',
    'optimizing': 'optimization',
    'improve': 'improvement',
    'improved': 'improvement',
    'improving': 'improvement',
    'streamline': 'streamlining',
    'streamlined': 'streamlining',
    'streamlining': 'streamlining',
    'automate': 'automation',
    'automated': 'automation',
    'automating': 'automation',
    'enhance': 'enhancement',
    'enhanced': 'enhancement',
    'enhancing': 'enhancement',

    # Accounting & Finance specific
    'reconcile': 'reconciliation',
    'reconciled': 'reconciliation',
    'reconciling': 'reconciliation',
    'audit': 'auditing',
    'audited': 'auditing',
    'auditing': 'auditing',
    'budget': 'budgeting',
    'budgeted': 'budgeting',
    'budgeting': 'budgeting',
    'report': 'reporting',
    'reported': 'reporting',
    'reporting': 'reporting',
}

# Common skill-bearing nouns that follow verbs
SKILL_BEARING_NOUNS = {
    'budget', 'budgets', 'team', 'teams', 'project', 'projects', 'program', 'programs',
    'process', 'processes', 'system', 'systems', 'data', 'report', 'reports', 'analysis',
    'strategy', 'strategies', 'campaign', 'campaigns', 'initiative', 'initiatives',
    'compensation', 'benefits', 'payroll', 'accounts', 'ledger', 'statements',
    'reconciliation', 'invoice', 'invoices', 'payment', 'payments', 'contract', 'contracts',
    'performance', 'metrics', 'kpi', 'kpis', 'dashboard', 'dashboards',
    'employee', 'employees', 'stakeholder', 'stakeholders', 'client', 'clients',
    'vendor', 'vendors', 'database', 'databases', 'spreadsheet', 'spreadsheets',
    'presentation', 'presentations', 'model', 'models', 'forecast', 'forecasts'
}

# ============================================================================
# TIER 3: TOOL & SOFTWARE NER
# ============================================================================

# Comprehensive list of tools and software (case-insensitive matching)
TOOLS_AND_SOFTWARE = {
    # HR/HRIS Systems
    'workday', 'adp', 'paychex', 'paylocity', 'bamboohr', 'namely', 'gusto', 'rippling',
    'ultipro', 'dayforce', 'successfactors', 'oracle hcm', 'peoplesoft',
    'kronos', 'ceridian', 'paycom', 'zenefits',

    # ATS Systems
    'greenhouse', 'lever', 'jobvite', 'icims', 'taleo', 'smartrecruiters',
    'workable', 'bullhorn', 'recruitee', 'jazz hr',

    # Compensation Software
    'payscale', 'salary.com', 'companalyst', 'paycom', 'payfactors', 'radford',
    'mercer compensation', 'willis towers watson', 'korn ferry',

    # Accounting Software
    'quickbooks', 'xero', 'sage', 'netsuite', 'freshbooks', 'wave', 'zoho books',
    'myob', 'kashoo', 'freeagent', 'peachtree', 'sage 50', 'sage intacct',

    # ERP Systems
    'sap', 'oracle', 'microsoft dynamics', 'dynamics 365', 'dynamics nav',
    'dynamics ax', 'jd edwards', 'epicor', 'infor', 'ifs', 'syspro',

    # CRM Systems
    'salesforce', 'hubspot', 'zoho crm', 'microsoft dynamics crm', 'pipedrive',
    'freshsales', 'insightly', 'nimble', 'sugarcrm', 'vtiger',

    # Project Management
    'jira', 'asana', 'trello', 'monday.com', 'clickup', 'basecamp', 'wrike',
    'smartsheet', 'airtable', 'notion', 'ms project', 'microsoft project',

    # Data & Analytics
    'tableau', 'power bi', 'looker', 'qlik', 'sisense', 'domo', 'thoughtspot',
    'google analytics', 'adobe analytics', 'mixpanel', 'amplitude',

    # Collaboration
    'slack', 'microsoft teams', 'zoom', 'google workspace', 'g suite',
    'microsoft 365', 'office 365', 'confluence', 'sharepoint',

    # Development & Technical
    'github', 'gitlab', 'bitbucket', 'jenkins', 'docker', 'kubernetes',
    'terraform', 'ansible', 'puppet', 'chef', 'aws', 'azure', 'gcp',
    'visual studio', 'vscode', 'intellij', 'pycharm', 'eclipse',

    # Databases
    'mysql', 'postgresql', 'mongodb', 'redis', 'cassandra', 'oracle database',
    'sql server', 'microsoft sql server', 'mariadb', 'dynamodb',

    # Other Business Tools
    'concur', 'expensify', 'bill.com', 'brex', 'divvy', 'certify',
    'docusign', 'adobe sign', 'hellosign', 'pandadoc',
}

# ============================================================================
# TIER 4: INDUSTRY-SPECIFIC SKILL PATTERNS
# ============================================================================

# HR & Compensation specific skill patterns
HR_COMPENSATION_SKILLS = {
    'job evaluation', 'salary benchmarking', 'market pricing', 'pay equity',
    'pay equity analysis', 'compensation philosophy', 'compensation structure',
    'grade structure', 'salary ranges', 'pay bands', 'broadbanding',
    'merit increase', 'merit matrix', 'compa-ratio', 'range penetration',
    'incentive plan design', 'bonus plan', 'commission structure',
    'equity compensation', 'stock options', 'rsus', 'restricted stock units',
    'ltip', 'long-term incentive plan', 'short-term incentive',
    'total rewards statement', 'compensation survey', 'market data',
    'job architecture', 'job leveling', 'career pathing',
    'flsa', 'fair labor standards act', 'exempt vs non-exempt',
    'salary admin', 'salary administration', 'off-cycle increase',
    'promotional increase', 'retention bonus', 'sign-on bonus',
    'severance package', 'golden parachute', 'change in control',
    'clawback provision', 'pay transparency', 'pay range disclosure',
    'compensation committee', 'say on pay', 'proxy statement',
    'sec filings', 'compensation disclosure', 'tally sheet',
    '409a valuation', 'stock option pricing', 'black-scholes',
    'job description writing', 'jd development', 'competency modeling',
    'talent management', 'succession planning', 'high potential',
    'performance appraisal', 'performance review', '360 review',
    'calibration', 'forced ranking', 'stack ranking',
    'people analytics', 'hr metrics', 'turnover analysis',
    'retention rate', 'time to fill', 'cost per hire',
    'employee engagement', 'engagement survey', 'pulse survey',
    'exit interview', 'stay interview', 'onboarding',
    'employee handbook', 'policy development', 'compliance',
}

# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def normalize_skill(skill: str) -> str:
    """
    Normalize a skill to its canonical form.
    Handles abbreviations, synonyms, and formatting.
    """
    skill_lower = skill.lower().strip()

    # Remove excessive whitespace
    skill_lower = re.sub(r'\s+', ' ', skill_lower)

    # Check if it's an abbreviation that should be expanded
    if skill_lower in ABBREVIATION_TO_CANONICAL:
        return ABBREVIATION_TO_CANONICAL[skill_lower]

    # Check for common patterns
    # "comp & ben" → "compensation and benefits"
    skill_lower = skill_lower.replace('&', 'and')
    if skill_lower in ABBREVIATION_TO_CANONICAL:
        return ABBREVIATION_TO_CANONICAL[skill_lower]

    return skill_lower


def extract_verb_based_skills(text: str) -> Set[str]:
    """
    Extract skills from verb+noun patterns like "managed budgets", "analyzed data".
    Returns normalized skills like "budget management", "data analysis".
    """
    skills = set()
    text_lower = text.lower()

    # Pattern: verb + article/determiner + adjective(s) + noun
    # Examples: "managed 5-person team", "analyzed compensation data", "led strategic initiatives"

    for verb, skill_suffix in VERB_TO_SKILL.items():
        # Build regex pattern for this verb
        # Match: verb + optional determiner + optional adjectives + noun
        pattern = rf'\b{verb}\b\s+(?:a\s+|an\s+|the\s+)?(?:\w+\s+)?(\w+)'

        matches = re.finditer(pattern, text_lower)
        for match in matches:
            noun = match.group(1)

            # Check if the noun is skill-bearing
            if noun in SKILL_BEARING_NOUNS or noun.rstrip('s') in SKILL_BEARING_NOUNS:
                # Construct skill: "budget management", "data analysis"
                if noun.endswith('s') and len(noun) > 2:
                    noun_singular = noun[:-1]  # Remove plural 's'
                else:
                    noun_singular = noun

                # Special handling for different skill types
                if skill_suffix in ['management', 'leadership', 'supervision']:
                    skill = f"{noun_singular} {skill_suffix}"
                elif skill_suffix.endswith('ing'):
                    # "budgeting", "reporting", "forecasting"
                    skill = skill_suffix
                else:
                    # "budget analysis", "data analysis"
                    skill = f"{noun_singular} {skill_suffix}"

                skills.add(skill)

    return skills


def extract_tool_mentions(text: str) -> Set[str]:
    """
    Extract mentions of tools and software from text using NER-like pattern matching.
    Returns normalized tool names.
    """
    tools = set()
    text_lower = text.lower()

    for tool in TOOLS_AND_SOFTWARE:
        # Use word boundaries to avoid partial matches
        # But also handle cases like "SAP experience" or "proficient in Salesforce"
        pattern = rf'\b{re.escape(tool)}\b'
        if re.search(pattern, text_lower):
            tools.add(tool)

    return tools


def extract_industry_specific_skills(text: str, industry: str = 'hr') -> Set[str]:
    """
    Extract industry-specific skills using domain knowledge.
    Currently supports: hr, compensation
    """
    skills = set()
    text_lower = text.lower()

    if industry in ['hr', 'compensation', 'human resources']:
        for skill_pattern in HR_COMPENSATION_SKILLS:
            pattern = rf'\b{re.escape(skill_pattern)}\b'
            if re.search(pattern, text_lower):
                skills.add(skill_pattern)

    return skills


def extract_contextual_skills(text: str) -> Set[str]:
    """
    Extract skills inferred from context.
    Examples:
    - "Led team of 5 engineers" → "team leadership", "engineering management"
    - "Managed $2M budget" → "budget management", "financial management"
    - "Coached junior analysts" → "coaching", "mentoring", "junior analyst development"
    """
    skills = set()
    text_lower = text.lower()

    # Pattern 1: "Led/Managed team of X"
    if re.search(r'\b(led|managed|supervised)\s+(?:a\s+)?team', text_lower):
        skills.add('team leadership')
        skills.add('people management')

    # Pattern 2: Numbers + budget/dollars/revenue
    if re.search(r'\$[\d,]+[mk]?\s*(?:budget|revenue|sales)', text_lower):
        skills.add('budget management')
        skills.add('financial management')

    if re.search(r'(?:budget|revenue|sales)\s+of\s+\$[\d,]+', text_lower):
        skills.add('budget management')
        skills.add('financial management')

    # Pattern 3: Coached/Mentored/Trained
    if re.search(r'\b(coached|mentored|trained|developed)\s+', text_lower):
        skills.add('coaching')
        skills.add('mentoring')
        skills.add('employee development')

    # Pattern 4: Cross-functional
    if re.search(r'\bcross-functional\b', text_lower):
        skills.add('cross-functional collaboration')
        skills.add('stakeholder management')

    # Pattern 5: Strategic
    if re.search(r'\bstrategic\s+(planning|initiative|roadmap)', text_lower):
        skills.add('strategic planning')

    return skills


def deduplicate_skills(skills: Set[str]) -> List[str]:
    """
    Remove duplicate skills accounting for synonyms and variations.
    Returns deduplicated list sorted by length (longer = more specific).
    """
    # Normalize all skills first
    normalized = {}
    for skill in skills:
        norm = normalize_skill(skill)
        if norm not in normalized or len(skill) > len(normalized[norm]):
            # Keep the longer/more specific version
            normalized[norm] = skill

    # Sort by length (longer first) then alphabetically
    result = sorted(normalized.values(), key=lambda x: (-len(x), x))

    return result


def enhance_skills(base_skills: List[str], text: str, industry: str = None) -> List[str]:
    """
    Main function to enhance extracted skills with advanced techniques.

    Args:
        base_skills: Skills extracted by the base ESCO ontology approach
        text: Full text of resume or job description
        industry: Optional industry hint for domain-specific extraction

    Returns:
        Enhanced and deduplicated list of skills
    """
    # Start with base skills
    all_skills = set(base_skills)

    # 1. Normalize existing skills (expand abbreviations)
    normalized_base = set()
    for skill in base_skills:
        normalized = normalize_skill(skill)
        normalized_base.add(normalized)
        all_skills.add(normalized)

    # 2. Extract verb-based skills
    verb_skills = extract_verb_based_skills(text)
    all_skills.update(verb_skills)

    # 3. Extract tool mentions
    tools = extract_tool_mentions(text)
    all_skills.update(tools)

    # 4. Extract industry-specific skills
    if industry:
        industry_skills = extract_industry_specific_skills(text, industry)
        all_skills.update(industry_skills)
    else:
        # Try all industries if not specified
        for ind in ['hr']:
            industry_skills = extract_industry_specific_skills(text, ind)
            all_skills.update(industry_skills)

    # 5. Extract contextual skills
    contextual = extract_contextual_skills(text)
    all_skills.update(contextual)

    # 6. Deduplicate and normalize
    final_skills = deduplicate_skills(all_skills)

    return final_skills


# ============================================================================
# UTILITY FUNCTIONS FOR TESTING
# ============================================================================

def compare_extraction_quality(original_skills: List[str], enhanced_skills: List[str]) -> Dict:
    """
    Compare original vs enhanced extraction quality.
    Returns metrics showing improvement.
    """
    original_set = set(s.lower() for s in original_skills)
    enhanced_set = set(s.lower() for s in enhanced_skills)

    # Calculate metrics
    only_in_enhanced = enhanced_set - original_set
    only_in_original = original_set - enhanced_set
    common = original_set & enhanced_set

    improvement_pct = (len(only_in_enhanced) / len(original_set) * 100) if original_set else 0

    return {
        'original_count': len(original_skills),
        'enhanced_count': len(enhanced_skills),
        'common_count': len(common),
        'new_skills_found': len(only_in_enhanced),
        'skills_lost': len(only_in_original),
        'improvement_pct': round(improvement_pct, 1),
        'new_skills_list': list(only_in_enhanced)[:20],  # Show first 20
        'lost_skills_list': list(only_in_original)[:10]  # Show first 10
    }
