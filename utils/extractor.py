import json
import re
import pandas as pd
from sentence_transformers import util
from datetime import datetime
from utils.model_cache import load_spacy_model, load_sentence_transformer
from utils.llm_inference import infer_skills_from_job_title

nlp = load_spacy_model()
model = load_sentence_transformer()

# Module-level cache for LLM job title inferences (persists across function calls)
_llm_job_title_cache = {}

# Module-level cache for ontology embeddings (computed once, reused forever)
_ontology_cache = {
    'labels': None,
    'embeddings': None,
    'path': None
}

def get_cached_ontology_embeddings(ontology_labels, ontology_path=None):
    """
    Get ontology embeddings from cache, or compute and cache them.
    This avoids re-encoding 100k+ skills on every analysis.
    """
    global _ontology_cache

    # Check if we already have cached embeddings for this ontology
    if (_ontology_cache['embeddings'] is not None and
        _ontology_cache['path'] == ontology_path):
        return _ontology_cache['labels'], _ontology_cache['embeddings']

    # Compute embeddings (this is slow but only happens once)
    embeddings = model.encode(ontology_labels, show_progress_bar=False)

    # Cache for future use
    _ontology_cache['labels'] = ontology_labels
    _ontology_cache['embeddings'] = embeddings
    _ontology_cache['path'] = ontology_path

    return ontology_labels, embeddings

# Industry classification keywords
INDUSTRY_KEYWORDS = {
    'technology': ['software engineer', 'software', 'developer', 'programming', 'coding', 'ai', 'ml', 'data science', 'cloud', 'devops', 'api', 'saas', 'tech stack', 'full stack', 'backend', 'frontend'],
    'engineering': ['structural engineer', 'civil engineer', 'mechanical engineer', 'electrical engineer', 'structural engineering', 'civil engineering', 'mechanical engineering', 'electrical engineering', 'construction', 'building codes', 'autocad', 'revit', 'concrete', 'steel design', 'hvac', 'plumbing', 'blueprint', 'architecture'],
    'finance': ['finance', 'banking', 'investment', 'portfolio', 'trading', 'financial analysis', 'accounting', 'cfa', 'cfp', 'audit', 'compliance', 'treasury',
                'controller', 'accounts payable', 'accounts receivable', 'ap', 'ar', 'reconciliation', 'journal entries', 'general ledger', 'gaap', 'financial reporting',
                'payroll', 'bookkeeping', 'cpa', 'quickbooks', 'balance sheet', 'income statement', 'cash flow', 'budgeting', 'forecasting'],
    'healthcare': ['healthcare', 'medical', 'clinical', 'patient', 'hospital', 'nursing', 'physician', 'pharma', 'biotech', 'health systems'],
    'marketing': ['marketing', 'brand', 'advertising', 'campaign', 'digital marketing', 'seo', 'sem', 'content marketing', 'social media', 'growth'],
    'sales': ['sales', 'business development', 'account management', 'revenue', 'quota', 'pipeline', 'crm', 'b2b', 'b2c', 'enterprise sales'],
    'hr': ['human resources', 'hr', 'talent acquisition', 'recruiting', 'compensation', 'benefits', 'employee relations', 'hris', 'people operations'],
    'operations': ['operations', 'supply chain', 'logistics', 'procurement', 'inventory', 'manufacturing', 'process improvement', 'six sigma', 'lean'],
    'creative': ['design', 'creative', 'ux', 'ui', 'graphic design', 'art direction', 'branding', 'portfolio', 'adobe', 'figma', 'sketch'],
    'legal': ['legal', 'attorney', 'lawyer', 'compliance', 'regulatory', 'contracts', 'litigation', 'corporate law', 'intellectual property'],
    'education': ['education', 'teaching', 'training', 'curriculum', 'instruction', 'academic', 'professor', 'educator', 'learning']
}

def load_ontology(file_path):
    df = pd.read_csv(file_path)
    skills = df['preferredLabel'].tolist()  # Adjust if column differs
    return skills

def load_seniority_levels(file_path):
    with open(file_path, 'r') as f:
        levels = json.load(f)
    return levels

def detect_industry(text):
    """
    Detect the industry/domain of a job description or resume.
    Returns the top 2 detected industries with confidence scores.
    """
    text_lower = text.lower()
    industry_scores = {}

    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        if score > 0:
            industry_scores[industry] = score

    # Sort by score and return top 2
    sorted_industries = sorted(industry_scores.items(), key=lambda x: x[1], reverse=True)

    if len(sorted_industries) == 0:
        return [('general', 0)]
    elif len(sorted_industries) == 1:
        return sorted_industries
    else:
        return sorted_industries[:2]

def clean_text_for_skill_extraction(text):
    """
    Clean text before NLP parsing to remove formatting artifacts that cause malformed skill extraction.

    Fixes:
    - Bullet characters (•, ·, ◦, ▪, ■, etc.) → spaces
    - Special formatting characters
    - Multiple consecutive spaces (PRESERVING newlines for section detection)
    - Zero-width characters

    Returns:
        Cleaned text ready for NLP parsing
    """
    # Remove common bullet characters and replace with space
    bullet_chars = ['•', '·', '◦', '▪', '■', '●', '○', '□', '▫', '◾', '◽', '►', '▸', '▹']
    for bullet in bullet_chars:
        text = text.replace(bullet, ' ')

    # Remove zero-width characters and other formatting artifacts
    text = text.replace('\u200b', '')  # Zero-width space
    text = text.replace('\u200c', '')  # Zero-width non-joiner
    text = text.replace('\u200d', '')  # Zero-width joiner
    text = text.replace('\ufeff', '')  # Zero-width no-break space

    # Normalize multiple spaces to single space WITHIN lines (preserve newlines!)
    # This is critical: we need line structure for benefits section detection
    text = re.sub(r'[^\S\n]+', ' ', text)  # Replace non-newline whitespace with single space

    # Normalize excessive newlines (keep structure but clean up 3+ newlines to 2)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

    return text.strip()


def detect_and_exclude_benefits_sections(text):
    """
    Detect and exclude benefits/compensation sections from skill extraction.

    These sections often contain non-skill terms like "401k", "medical", "dental",
    "up to X% match" that get incorrectly extracted as skills.

    Returns:
        Text with benefits sections removed
    """
    # Comprehensive benefits section indicators
    benefits_headers = [
        r'\bbenefits?\s*(?:package|offered|include|program)?\b',
        r'\bcompensation\s*(?:package|offered|includes?)?\b',
        r'\bwe\s+offer\b',
        r'\bperks?\s*(?:include|offered)?\b',
        r'\bwhat\s+we\s+offer\b',
        r'\bemployee\s+benefits\b',
        r'\btotal\s+rewards?\b',
    ]

    # Combined pattern to match benefits section headers
    benefits_pattern = '|'.join(benefits_headers)

    # Split text into lines
    lines = text.split('\n')
    filtered_lines = []
    in_benefits_section = False
    benefits_section_depth = 0

    for i, line in enumerate(lines):
        line_lower = line.lower().strip()

        # Check if this line starts a benefits section
        if re.search(benefits_pattern, line_lower, re.IGNORECASE):
            in_benefits_section = True
            benefits_section_depth = len(line) - len(line.lstrip())  # Track indentation
            continue  # Skip the header line

        # Check if we've exited the benefits section
        if in_benefits_section:
            # Exit if we hit a new major section (typically less indented or all caps header)
            is_new_section = (
                (len(line) - len(line.lstrip()) <= benefits_section_depth and line.strip() and line[0].isupper()) or
                line.isupper() or
                re.match(r'^[A-Z][A-Za-z\s]+:?\s*$', line.strip())  # "SECTION HEADER" or "Section Header:"
            )

            # Also exit if we see common non-benefits section headers
            exit_keywords = [
                r'^\s*(?:experience|education|skills|qualifications|responsibilities|duties|requirements)',
                r'^\s*(?:job\s+description|position\s+summary|about\s+(?:the\s+)?role)',
            ]
            is_exit_section = any(re.match(pattern, line_lower) for pattern in exit_keywords)

            if is_new_section or is_exit_section:
                in_benefits_section = False
                benefits_section_depth = 0
            else:
                continue  # Skip lines in benefits section

        # Keep non-benefits lines
        filtered_lines.append(line)

    return '\n'.join(filtered_lines)


def extract_skills(text, ontology):
    """
    Extract skills with flexible fallback approach:
    1. Try ontology matching first (structured skills)
    2. Fall back to direct extraction from text if ontology yields few results
    """

    def is_non_skill_phrase(phrase):
        """
        Filter out non-skill phrases including:
        - Benefits/perks (medical, dental, 401k, etc.)
        - Generic meta-text (job description, responsibilities, etc.)
        - Vague qualifiers (strong knowledge, good understanding, etc.)
        - Company context (the law firm, the company, etc.)
        - Abstract/intangible concepts (work spirit, team spirit, etc.)
        - Phrases with pronouns (their, your, our, etc.)

        Returns True if phrase should be EXCLUDED.
        Returns False if phrase is a legitimate skill (should be kept).
        """
        phrase_lower = phrase.lower().strip()

        # CRITICAL: Whitelist of skills that should NEVER be filtered out
        # These bypass all filtering logic below
        PROTECTED_SKILLS = {
            # Accounting/Finance core skills
            'general ledger accounting', 'general ledger', 'financial statements',
            'financial statement preparation', 'balance sheet', 'income statement',
            'cash flow statement', 'cash flow statements', 'accrual accounting',
            'accounts payable', 'accounts receivable', 'ap', 'ar',
            'bank reconciliation', 'account reconciliation', 'reconciliation',
            'journal entries', 'gaap', 'generally accepted accounting principles',
            'financial reporting', 'financial analysis', 'bookkeeping',
            'quickbooks', 'sage', 'payroll', 'payroll processing',
            'month end close', 'year end close', 'senior management',
            'tax preparation', 'audit', 'budgeting', 'forecasting',
            'variance analysis', 'cost accounting', 'controller',
            'cpa', 'certified public accountant', 'ifrs',
            'balance sheet reconciliation', 'general ledger reconciliation',

            # Add more industry-specific whitelists as needed
        }

        if phrase_lower in PROTECTED_SKILLS:
            return False  # NEVER filter these skills

        # FIRST: Filter pronouns and possessives - these are NEVER skills
        # This catches "their individual capabilities", "your skills", etc.
        pronouns = ['their', 'our', 'your', 'its', 'his', 'her', 'my', 'we', 'they', 'you']
        words = phrase_lower.split()
        for pronoun in pronouns:
            if pronoun in words:
                return True  # Reject any phrase containing pronouns

        # SECOND: Filter abstract/intangible concepts that aren't real skills
        abstract_concepts = [
            'work spirit', 'team spirit', 'spirit', 'attitude', 'mindset',
            'individual capabilities', 'capabilities', 'personal qualities',
            'work ethic', 'professional demeanor', 'character traits',
            'core values', 'cultural fit', 'passion', 'enthusiasm',
            'dedication', 'commitment', 'motivation', 'drive'
        ]
        for concept in abstract_concepts:
            if concept in phrase_lower or phrase_lower == concept:
                return True  # Reject abstract concepts

        # THIRD: Filter vague "X skills" patterns (staff skills, work skills, etc.)
        # Exception: Keep specific technical skills like "python skills", "sql skills"
        # CRITICAL FIX: Reject ALL "X skills" patterns by default
        # "Skills" is a meta-term. Real skills are "Python", "accounting", not "Python skills"
        # Only keep extremely specific technical skill names that are commonly written with "skills"
        if phrase_lower.endswith(' skills') or phrase_lower.endswith(' skill'):
            # Whitelist: ONLY allow these specific skill combinations
            allowed_skill_patterns = [
                'excel skills', 'sql skills', 'python skills', 'java skills',
                'coding skills', 'programming skills', 'technical skills'
            ]
            if phrase_lower not in allowed_skill_patterns:
                return True  # Reject "diplomacy skills", "communication skills", "leadership skills", etc.

        # ============================================================================
        # CRITICAL: Run SPECIFIC filters BEFORE general skill_indicators check
        # Otherwise "design work" would match "design" and return False too early
        # ============================================================================

        # CRITICAL FIX: Filter meta-descriptors about background/experience
        # "strong background", "solid foundation", etc. are NOT skills
        meta_descriptors = [
            'strong background', 'solid background', 'deep background', 'proven background',
            'extensive background', 'broad background', 'comprehensive background',
            'proven track record', 'track record', 'solid foundation', 'strong foundation',
            'extensive experience', 'proven experience', 'deep experience',
            'solid understanding', 'strong understanding', 'deep understanding',
            'comprehensive knowledge', 'extensive knowledge', 'proven ability',
            'demonstrated ability', 'proven skills'
        ]
        if phrase_lower in meta_descriptors:
            return True  # Reject meta-descriptors

        # CRITICAL FIX: Filter vague "X background" patterns
        if phrase_lower.endswith(' background'):
            return True  # Reject "strong background", "technical background", etc.

        # CRITICAL FIX: Filter generic decision-making phrases
        # "informed decisions", "strategic decisions", etc. are NOT skills
        generic_decision_phrases = [
            'informed decisions', 'strategic decisions', 'data-driven decisions',
            'business decisions', 'key decisions', 'critical decisions',
            'sound decisions', 'effective decisions', 'timely decisions'
        ]
        if phrase_lower in generic_decision_phrases:
            return True  # Reject generic decision phrases

        # CRITICAL FIX: Filter vague "X trends" and "X topics" patterns
        if phrase_lower.endswith(' trends') or phrase_lower.endswith(' topics'):
            # Allow specific trends like "market trends", "industry trends" if they have context
            # But reject vague ones like "data trends", "compensation trends" (too generic)
            vague_trend_prefixes = ['data', 'compensation', 'current', 'emerging', 'latest']
            if any(prefix in phrase_lower for prefix in vague_trend_prefixes):
                return True  # Reject vague trend descriptors

        if 'sensitive topics' in phrase_lower or phrase_lower == 'sensitive topics':
            return True  # Reject "sensitive topics"

        # CRITICAL FIX: Detect concatenated words with no spaces
        # "identifyonboard", "identifyonboard new roles", etc.
        # Check if ANY individual word contains multiple verbs mashed together
        common_verbs = ['identify', 'onboard', 'design', 'implement', 'analyze', 'develop', 'create',
                       'manage', 'coordinate', 'oversee', 'support', 'maintain', 'establish']

        # Check each word in the phrase for multiple verbs concatenated
        words = phrase_lower.split()
        for word in words:
            verb_count_in_word = sum(1 for verb in common_verbs if verb in word)
            if verb_count_in_word >= 2:
                # Multiple verbs in a single word = concatenation error
                return True  # Reject "identifyonboard" in any context

        # CRITICAL FIX: Filter incomplete fragments that start with "the"
        # "the design implementation", "the company", etc. are fragments, not skills
        if phrase_lower.startswith('the '):
            return True  # Reject fragments starting with "the"

        # CRITICAL FIX: Filter vague "X administration" patterns
        # "ongoing administration", "daily administration", etc. are too vague
        if phrase_lower.endswith(' administration') or phrase_lower == 'administration':
            # Allow specific types like "benefits administration", "payroll administration"
            specific_admin = ['benefits', 'payroll', 'database', 'system', 'network', 'server']
            has_specific_context = any(ctx in phrase_lower for ctx in specific_admin)
            if not has_specific_context:
                return True  # Reject vague administration phrases

        # CRITICAL FIX: Filter "X ability" and "X capability" patterns
        # "talent ability", "strong ability", etc. are abstract, not skills
        if phrase_lower.endswith(' ability') or phrase_lower.endswith(' capability'):
            return True  # Reject "X ability" patterns

        # CRITICAL FIX: Filter "X teams" patterns - refers to people, not skills
        # "legal teams", "development teams", etc.
        if phrase_lower.endswith(' teams') or phrase_lower.endswith(' team'):
            return True  # Reject team references

        # CRITICAL FIX: Filter "X performance" patterns - too vague
        # "growth performance", "business performance", etc.
        if phrase_lower.endswith(' performance'):
            return True  # Reject vague performance phrases

        # CRITICAL FIX: Filter "X assignments" patterns - work arrangements, not skills
        # "international assignments", "project assignments", etc.
        if phrase_lower.endswith(' assignments') or phrase_lower.endswith(' assignment'):
            return True  # Reject assignment references

        # CRITICAL FIX: Filter "new and existing X" patterns - too generic
        if 'new and existing' in phrase_lower:
            return True  # Reject "new and existing jobs", etc.

        # CRITICAL FIX: Detect phrases with missing connector words
        # "compensation trends regulatory changes" should be "compensation trends AND regulatory changes"
        # Check for 3+ word phrases where all words are nouns with no connectors
        words_in_phrase = phrase_lower.split()
        if len(words_in_phrase) >= 3:
            connectors = ['and', 'or', 'of', 'to', 'for', 'with', 'in', 'on', 'at', 'by', 'from', 'the']
            has_connector = any(conn in words_in_phrase for conn in connectors)

            # If no connectors and 3+ words, likely a concatenation
            # Exception: Allow proper compound skills like "project management system"
            if not has_connector:
                # Check if it looks like multiple separate concepts mashed together
                # "compensation trends regulatory changes" = 2 separate concepts
                concept_keywords = ['trends', 'changes', 'programs', 'plans', 'strategies', 'systems',
                                   'processes', 'standards', 'policies', 'procedures', 'regulations',
                                   'requirements', 'implementation', 'development', 'analysis']
                concept_count = sum(1 for word in words_in_phrase if word in concept_keywords)

                if concept_count >= 2:
                    # Multiple concept keywords without connectors = concatenation
                    return True  # Reject "compensation trends regulatory changes"

        # Filter vague work type descriptors
        vague_work_types = [
            'design work', 'administrative work', 'project work', 'client work',
            'fieldwork', 'desk work', 'construction work', 'office work'
        ]
        if phrase_lower in vague_work_types:
            return True

        # Filter references to "professionals" (refers to other people)
        if 'professionals' in phrase_lower or 'colleagues' in phrase_lower or 'team members' in phrase_lower:
            return True

        # Filter generic "professional development" (employee benefit)
        if 'professional development' in phrase_lower:
            return True

        # Filter workplace culture/environment descriptors
        environment_benefit_words = ['environment', 'culture', 'atmosphere', 'workplace']
        if any(word in phrase_lower for word in environment_benefit_words):
            skill_exceptions = ['environmental', 'engineering', 'science', 'studies', 'management']
            has_skill_exception = any(exc in phrase_lower for exc in skill_exceptions)
            if not has_skill_exception:
                return True

        # Filter "other X" phrases
        if phrase_lower.startswith('other '):
            return True

        # Filter pure numbers (phone numbers, zip codes, IDs, etc.)
        if phrase_lower.strip().isdigit():
            return True  # Reject "6941", "12345", etc.

        # Filter overly long phrases (5+ words)
        words_in_phrase = phrase_lower.split()
        if len(words_in_phrase) >= 5:
            return True

        # CRITICAL FIX: Filter generic business phrases that are NOT skills
        # "job duties", "industry standards", "key deliverables", etc. are vague descriptors
        generic_business_phrases = [
            'job duties', 'job responsibilities', 'job requirements', 'job description',
            'industry standards', 'industry best practices', 'best practices',
            'key deliverables', 'deliverables', 'key responsibilities',
            'core responsibilities', 'primary responsibilities', 'main duties',
            'daily duties', 'core duties', 'job functions', 'job tasks',
            'work duties', 'work responsibilities', 'role responsibilities',
            'position responsibilities', 'key tasks', 'core job', 'role duties'
        ]
        if phrase_lower in generic_business_phrases:
            return True  # Reject generic business descriptors

        # CRITICAL FIX: Filter "talent" references (refers to people/employees, not skills)
        # "internal talent", "external talent", "top talent", etc.
        if 'talent' in phrase_lower:
            return True  # Reject all talent references

        # CRITICAL FIX: Filter references to people/roles (consultants, contractors, etc.)
        # "external consultants", "internal stakeholders", "senior leaders", etc.
        people_references = ['consultants', 'contractors', 'stakeholders', 'vendors',
                            'partners', 'executives', 'leaders', 'managers', 'directors',
                            'employees', 'staff members', 'personnel']
        if any(ref in phrase_lower for ref in people_references):
            # Exception: Allow specific job titles that are skills
            job_title_exceptions = ['project manager', 'program manager', 'product manager',
                                   'account manager', 'relationship manager']
            is_job_title = any(title in phrase_lower for title in job_title_exceptions)
            if not is_job_title:
                return True  # Reject people references

        # CRITICAL FIX: Filter organizational level descriptors (not skills)
        # "corporate and executive levels", "senior levels", "all levels", etc.
        level_descriptors = ['corporate and executive levels', 'executive levels',
                            'senior levels', 'all levels', 'leadership levels',
                            'corporate levels', 'organizational levels']
        if phrase_lower in level_descriptors or phrase_lower.endswith(' levels') or phrase_lower.endswith(' level'):
            return True  # Reject level descriptors

        # CRITICAL FIX: Filter vague "X delivery" patterns
        # "lead delivery", "project delivery", "service delivery" are too vague
        if phrase_lower.endswith(' delivery'):
            # Allow specific deliverables
            specific_delivery = ['software delivery', 'content delivery', 'product delivery']
            if phrase_lower not in specific_delivery:
                return True  # Reject vague delivery phrases

        # CRITICAL FIX: Filter "minimal/limited X" patterns - these are job requirements, not skills
        # "minimal oversight", "minimal supervision", "limited direction" etc.
        minimal_limited_patterns = ['minimal', 'limited', 'little', 'low']
        if any(pattern in phrase_lower.split() for pattern in minimal_limited_patterns):
            return True  # Reject minimal/limited requirement phrases

        # CRITICAL FIX: Filter frequency/time descriptors combined with vague nouns
        # "regular market analyses", "ongoing support", "continuous improvement" are too vague
        frequency_descriptors = ['regular', 'ongoing', 'continuous', 'frequent', 'periodic',
                                'routine', 'daily', 'weekly', 'monthly', 'annual']
        if any(freq in phrase_lower.split() for freq in frequency_descriptors):
            # Check if it's a specific skill or just a frequency descriptor
            # Allow: "monthly financial reporting" (specific)
            # Reject: "regular market analyses", "ongoing administration"
            specific_skill_contexts = ['reporting', 'reconciliation', 'closing', 'statements']
            has_specific_context = any(ctx in phrase_lower for ctx in specific_skill_contexts)
            if not has_specific_context:
                return True  # Reject vague frequency + noun combinations

        # CRITICAL FIX: Filter vague "X advances" or "X developments" phrases
        # MUST run BEFORE skill_indicators check to avoid false positives
        if phrase_lower.endswith(' advances') or phrase_lower.endswith(' developments'):
            return True  # Reject "technological advances", "industry developments", "legislative developments"

        # CRITICAL FIX: Filter vague "X principles" and "X implications" patterns
        # MUST run BEFORE skill_indicators check
        if phrase_lower.endswith(' principles') or phrase_lower.endswith(' implications'):
            return True  # Reject "financial principles", "business implications", etc.

        # CRITICAL FIX: Filter aspirational modifiers + vague nouns
        # MUST run BEFORE skill_indicators check to catch "innovative plans" etc.
        aspirational_modifiers = ['innovative', 'strategic', 'effective', 'efficient', 'successful',
                                 'optimal', 'comprehensive', 'robust', 'dynamic']
        vague_nouns = ['plans', 'initiatives', 'solutions', 'approaches', 'methods', 'practices',
                      'strategies', 'programs', 'systems']

        words = phrase_lower.split()
        if len(words) >= 2:
            # Check if phrase is aspirational modifier + vague noun
            for modifier in aspirational_modifiers:
                for noun in vague_nouns:
                    if phrase_lower == f"{modifier} {noun}" or phrase_lower == f"{modifier} incentive {noun}":
                        return True  # Reject "innovative plans", "innovative incentive plans"

        # CRITICAL: Define vague multiword phrases FIRST before skill_indicators check
        # This prevents false positives like "general policies" from being kept
        vague_multiword_phrases_for_check = [
            # Descriptors (not skills)
            'particular focus', 'comprehensive program', 'comprehensive programs',
            'this program', 'that program', 'these programs', 'those programs',
            'established college core', 'college core',
            'increasing responsibility', 'increased responsibility',

            # Broken n-grams and grammatically incorrect phrases
            'programs excellent planning organization', 'excellent planning organization',
            'proper allocation revenues', 'allocation revenues',
            'general policies', 'specific policies',
            'institutional compliance', 'compliance programs',
            'staff productivity', 'employee productivity', 'team productivity',
            'strategic priorities student engagement',  # broken concatenation
            'student-facing co-curricular units',  # too specific/vague

            # Time periods (not skills)
            'five years', 'three years', 'two years', 'one year',
            'several years', 'many years', 'few years',

            # Vague phrases with "a/an/the"
            'a comprehensive program', 'the program', 'the initiative',
            'a program', 'an initiative', 'the project',

            # Generic program/initiative references
            'successful program', 'effective program', 'strong program',
            'new program', 'existing program', 'current program',

            # Compound nouns that are really multiple separate skills mashed together
            'sports information marketing', 'sports information marketing and sponsorships',
        ]

        # CRITICAL: Check vague phrases BEFORE skill_indicators to prevent false positives
        if phrase_lower in vague_multiword_phrases_for_check:
            return True  # Filter out even if it contains skill indicator words

        # Keywords that indicate it's a job skill/responsibility (KEEP these)
        skill_indicators = [
            'administer', 'administering', 'administration', 'manage', 'managing', 'management',
            'design', 'designing', 'implement', 'implementing', 'implementation',
            'analyze', 'analyzing', 'analysis', 'coordinate', 'coordinating', 'coordination',
            'develop', 'developing', 'development', 'oversee', 'overseeing', 'oversight',
            'specialist', 'analyst', 'manager', 'director', 'coordinator', 'representative',
            'consultant', 'advisor', 'administrator', 'lead', 'senior', 'junior',
            'plan', 'planning', 'strategy', 'strategic', 'program', 'compliance',
            'regulatory', 'policy', 'policies', 'expertise', 'experience in',
            'reconciliation', 'payable', 'receivable'  # accounting-specific
        ]

        # If phrase contains professional/action context, it's a skill - KEEP IT
        for indicator in skill_indicators:
            if indicator in phrase_lower:
                return False  # It's a skill, not a generic phrase

        # Meta-text about the job posting itself (EXCLUDE)
        meta_text_patterns = [
            'job description', 'job posting', 'position description', 'role description',
            'responsibilities', 'requirements', 'qualifications', 'preferred qualifications',
            'the company', 'the firm', 'the organization', 'our company', 'our firm',
            'law firm', 'our client', 'the client', 'our team',
            'minimum', 'maximum', 'required', 'preferred',  # requirement language
            'years experience', 'years of experience', 'related field'
        ]

        for pattern in meta_text_patterns:
            if pattern in phrase_lower:
                return True  # It's meta-text, exclude it

        # Job requirement language - phrases with these terms are usually not skills
        requirement_terms = ['minimum', 'maximum', 'required', 'preferred', 'must have', 'should have']
        for term in requirement_terms:
            if term in phrase_lower:
                return True

        # Vague qualifiers without specific skills (EXCLUDE)
        vague_qualifiers = [
            'strong knowledge', 'good knowledge', 'excellent knowledge', 'solid knowledge',
            'strong understanding', 'good understanding', 'thorough understanding', 'complete understanding',
            'interpersonal skills', 'communication skills', 'organizational skills',
            'strong skills', 'excellent skills', 'proven ability', 'ability to work',
            'team player', 'self-starter', 'detail oriented', 'fast paced',
            'multiple deadlines', 'daily operations', 'daily accounting operations',
            'strong attention', 'great attention', 'excellent attention',  # partial vague phrases
            'other duties', 'other responsibilities', 'other tasks',
            'various duties', 'various responsibilities', 'various tasks',
            'various pursuits', 'various platforms', 'various initiatives',  # too vague
            'minimal oversight', 'minimal supervision', 'minimal direction',  # job requirement, not skill
            'interview material', 'interview materials', 'presentation material',  # deliverable, not skill
            'social declarations', 'social security declarations',  # regional/foreign terms
            'verbal written presentation', 'written presentation', 'verbal presentation',
            'ongoing administration', 'ongoing support', 'ongoing maintenance',
            'teammates', 'team members', 'colleagues', 'peers', 'coworkers',
            'materials', 'documents', 'files', 'reports', 'paperwork',  # too generic without context
            # Performance expectations (not skills)
            'timely responses', 'quick turnaround', 'fast response', 'rapid response',
            'timely manner', 'timely fashion', 'quick response', 'prompt response',
            # Work environment descriptors (not skills)
            'concurrent deadlines', 'tight deadlines', 'competing deadlines', 'overlapping deadlines',
            'fast-paced environment', 'fast paced environment', 'dynamic environment',
            'fast paced', 'high volume', 'fast-paced',
            # Incomplete attention phrases
            'exceptional attention', 'strong attention', 'great attention', 'excellent attention',
            # Too-specific marketing jargon
            'win themes', 'win strategies', 'win strategy'
        ]

        # Also reject standalone vague words
        vague_single_words = [
            'book', 'books', 'experience', 'knowledge', 'understanding',
            'documents', 'document', 'wages', 'wage', 'records', 'record',
            'management', 'processes', 'duties', 'tasks', 'functions',
            'skills', 'abilities', 'field', 'area', 'department',
            'teammates', 'materials', 'files', 'reports', 'paperwork',
            'colleagues', 'peers', 'coworkers', 'administration', 'support',
            'maintenance', 'presentation', 'presentations',
            'microsoft', 'software', 'tools', 'systems',  # Too vague without specific context
            'expenditures', 'revenues', 'outcomes', 'indicators', 'relations',
            'policies', 'regulations', 'procedures', 'guidelines', 'standards',
            'program', 'programs', 'initiative', 'initiatives', 'focus',
            'responsibility', 'responsibilities', 'accountability', 'requirements',
            'utilization', 'allocation', 'projections', 'acumen', 'compliance',
            'years'  # Reject time periods like "five years"
        ]
        if phrase_lower in vague_single_words:
            return True

        # Reject vague two-word combinations that aren't specific skills
        vague_2word_patterns = [
            'bank documents', 'tax documents', 'financial documents',
            'annual wages', 'middle management',  # Removed 'senior management' - it's a valid skill
            'related field', 'various tasks', 'daily tasks'
        ]
        if len(phrase_lower.split()) == 2 and phrase_lower in vague_2word_patterns:
            return True

        for qualifier in vague_qualifiers:
            if phrase_lower == qualifier or phrase_lower.startswith(qualifier + ' '):
                return True  # It's too vague, exclude it

        # Filter phrases containing "other" + any noun (too generic to be a skill)
        if phrase_lower.startswith('other '):
            return True

        # Filter phrases starting with articles (the, a, an)
        if phrase_lower.startswith('the ') or phrase_lower.startswith('a ') or phrase_lower.startswith('an '):
            return True

        # Filter phrases with "all" at the beginning (like "all financial information")
        if phrase_lower.startswith('all '):
            return True

        # Filter vague "X environment" or "X setting" phrases (anywhere in phrase)
        # Reject phrases containing "environment" or "setting" unless it's a specific tech term
        environment_exceptions = ['production environment', 'development environment', 'test environment',
                                 'cloud environment', 'virtual environment', 'linux environment']
        if (' environment' in phrase_lower or ' setting' in phrase_lower or phrase_lower.endswith(' settings')):
            # Keep specific technical environments
            if not any(exception in phrase_lower for exception in environment_exceptions):
                return True  # Reject vague environment phrases like "professional development great environment"

        # Filter generic "X systems" or "X information" (unless it's a specific system name)
        # These are too vague to be skills
        vague_endings = [' systems', ' information', ' data', ' experience', ' documents']
        for ending in vague_endings:
            if phrase_lower.endswith(ending):
                # Exception: specific system names
                specific_systems = ['erp systems', 'financial systems management', 'accounting systems implementation']
                if phrase_lower not in specific_systems:
                    # Filter all multi-word phrases ending with vague terms
                    if len(phrase_lower.split()) >= 2:
                        return True

        # Filter phrases containing "experience" in the middle (like "tax experience process improvement")
        if ' experience ' in phrase_lower and len(phrase_lower.split()) >= 3:
            return True

        # Reject phrases that are likely concatenated multi-skills (EXCLUDE)
        # These are usually multiple unrelated nouns strung together
        words = phrase_lower.split()

        # Check for words mashed together without spaces (like "accountingfinance", "designconstruction")
        # This happens when text extraction fails
        if len(words) == 1:
            # Check for concatenated skill terms
            known_terms = ['accounting', 'finance', 'payroll', 'reconciliation', 'invoice', 'payment',
                          'followup', 'follow', 'design', 'construction', 'coordination', 'repair',
                          'restoration', 'structural', 'engineer', 'architectural', 'mechanical',
                          'electrical', 'plumbing', 'building', 'project', 'management']
            term_count = sum(1 for term in known_terms if term in phrase_lower)

            # If long word with 2+ skill terms, likely mashed
            if len(phrase_lower) > 15 and term_count >= 2:
                return True  # Reject "accountingfinance", "designconstruction" type phrases

            # Check for specific mashed patterns
            mashed_patterns = ['followup', 'followuppayments', 'designconstruction', 'repairrestoration',
                              'coordinationmeetings', 'structuralengineer', 'projectmanagement']
            if any(pattern in phrase_lower for pattern in mashed_patterns):
                return True  # Reject concatenated words

        # Check for 2-word mashed terms (hyphenated or missing space)
        if len(words) == 2:
            # Check if it's a mashup like "followup payments"
            if any(term in words[0] for term in ['followup', 'follow-up', 'follow up']):
                return True

        skill_terms = ['reconciliation', 'invoice', 'payroll', 'accounting', 'finance',
                      'checks', 'balance', 'statements', 'entries', 'payments', 'dispute',
                      'differences', 'process', 'sheets', 'changes', 'efficiency', 'accuracy',
                      'ledger', 'receivable', 'payable', 'reporting', 'budgeting',
                      'social', 'declarations', 'environment', 'services', 'systems', 'information',
                      'professional', 'financial', 'book', 'paychex']

        # Check for 2-word phrases that are just skill+skill concatenation
        if len(words) == 2:
            # If both words are skill terms with no context, reject
            skill_count = sum(1 for word in words if any(term in word for term in skill_terms))

            # Special check for plural compound nouns (like "balance sheets income statements")
            # which might be split across phrase boundaries
            if all(word.endswith('s') for word in words) and skill_count >= 2:
                return True  # Reject plural compound concatenations like "payroll ap"

            if skill_count >= 2:
                # Exception: Keep common compound terms
                common_compounds = ['accounts payable', 'accounts receivable', 'journal entries',
                                  'bank reconciliation', 'account reconciliation', 'financial reporting',
                                  'financial statements', 'balance sheet', 'income statement',
                                  'cash flow', 'general ledger', 'payroll processing', 'general ledger accounting']
                if phrase_lower not in common_compounds:
                    return True  # Reject "accounting finance" type phrases

        # Check for 3-word phrases with multiple skill terms but no connecting words
        if len(words) == 3:
            skill_count = sum(1 for word in words if any(term in word for term in skill_terms))
            connectors = ['and', 'or', 'of', 'to', 'for', 'with', 'in', 'on', 'by']
            has_connector = any(word in connectors for word in words)

            # Exception: Keep legitimate 3-word accounting/finance terms
            common_3word_compounds = [
                'general ledger accounting', 'general ledger reconciliation',
                'accounts payable clerk', 'accounts receivable clerk',
                'month end close', 'year end close',
                'cost accounting system', 'financial statements analysis'
            ]

            # More aggressive: If 2+ skill terms and no connector, likely garbage
            if skill_count >= 2 and not has_connector:
                if phrase_lower not in common_3word_compounds:
                    return True  # Reject "checks dispute invoices" type phrases

            # Also reject if it's plural nouns strung together (like "balance sheets income")
            plural_count = sum(1 for word in words if word.endswith('s') and any(term in word for term in skill_terms))
            if plural_count >= 2 and not has_connector:
                return True  # Reject "sheets statements entries" type phrases

        # Check for 4+ word phrases with multiple skill terms
        if len(words) >= 4:
            skill_count = sum(1 for word in words if any(term in word for term in skill_terms))
            connectors = ['and', 'or', 'of', 'to', 'for', 'with', 'in', 'on', 'by']
            has_connector = any(word in connectors for word in words)

            # VERY aggressive: If 3+ skill terms OR 2+ skill terms with no connector, it's garbage
            if skill_count >= 3:
                return True  # Reject "reconciliation differences process invoice payments"

            if skill_count >= 2 and not has_connector:
                return True  # Reject "balance sheets income statements"

            # Also check the RATIO - if more than 50% of words are skill terms, likely concatenated
            if len(words) >= 4 and skill_count / len(words) >= 0.6:
                return True  # Reject high-density skill term phrases

        # Benefits/perks keywords (EXCLUDE)
        perk_indicators = [
            'we offer', 'offering', 'includes', 'including', 'such as',
            'competitive', 'comprehensive', 'generous', 'great', 'excellent',
            'package', 'full benefits', 'and more', 'perks include',
            'enjoy', 'receive', 'eligible for', 'access to'
        ]

        for indicator in perk_indicators:
            if indicator in phrase_lower:
                return True  # It's a perk, exclude it

        # Specific benefit patterns (EXCLUDE)
        perk_patterns = [
            'medical dental', 'dental and vision', 'vision 401k', 'health insurance',
            '401k match', 'paid time off', 'pto', 'sick leave', 'vacation days',
            'competitive benefits', 'benefits package', 'retirement plan',
            'stock options', 'gym membership', 'flexible schedule', 'remote work',
            'annual bonus', 'performance bonus', 'signing bonus', 'quarterly bonus',
            'paid holidays', 'paid vacation', 'holiday pay', 'parental leave',
            'tuition reimbursement', 'professional development', 'career advancement',
            'advancement opportunities', 'growth opportunities'
        ]

        for pattern in perk_patterns:
            if pattern in phrase_lower:
                return True  # It's a perk, exclude it

        # Standalone benefit keywords without professional context (EXCLUDE)
        generic_benefit_words = ['medical', 'dental', 'vision', '401k', 'insurance', 'retirement',
                                'pension', 'bonus', 'bonuses', 'holidays', 'vacation', 'pto',
                                'benefits', 'perks', 'compensation', 'salary', 'pay', 'wages',
                                'stipend', 'allowance', 'reimbursement']
        words_in_phrase = phrase_lower.split()

        # Reject short phrases (1-3 words) containing benefit keywords
        # Exception: Keep professional terms like "compensation analysis", "benefits administration"
        if len(words_in_phrase) <= 3:
            professional_benefit_contexts = ['administration', 'management', 'analyst', 'specialist',
                                            'coordinator', 'analysis', 'planning', 'strategy']
            has_professional_context = any(ctx in phrase_lower for ctx in professional_benefit_contexts)

            # If it contains benefit words but no professional context, reject it
            if any(word in generic_benefit_words for word in words_in_phrase) and not has_professional_context:
                return True  # Reject "paid holidays", "annual bonus", "holidays advancement", etc.

        # CRITICAL FIX: Filter company abbreviations and names
        # Company names are NOT skills
        company_indicators = [
            'inc', 'llc', 'corp', 'corporation', 'company', 'co.',
            'limited', 'ltd', 'group', 'associates', 'partners'
        ]
        if any(indicator in phrase_lower.split() for indicator in company_indicators):
            return True  # Reject company names

        # CRITICAL FIX: Filter building/facility descriptors (common in construction/real estate JDs)
        building_descriptors = [
            'high rises', 'high rise', 'office building', 'buildings',
            'facilities', 'stadiums', 'healthcare facilities',
            'offices nationwide', 'offices', 'person firm'
        ]
        if phrase_lower in building_descriptors:
            return True  # Reject building types

        # CRITICAL FIX: Filter numeric descriptors (company stats, not skills)
        # Matches: "5 offices", "110 person", "20 sectors", etc.
        numeric_descriptor_pattern = r'^\d+\s*\+?\s*(?:offices|person|people|employees|sectors|locations|clients|companies)'
        if re.match(numeric_descriptor_pattern, phrase_lower):
            return True  # Reject numeric company descriptors

        # CRITICAL FIX: Filter geographic location references when not in skill context
        # "great britain", "united states", etc. are NOT skills unless in specific context
        # Allow: "great britain accounting standards" (skill context)
        # Reject: "great britain" standalone or "good standing britain" (nonsense)
        geographic_terms = ['united states', 'great britain', 'britain', 'france', 'luxembourg', 'germany']
        if phrase_lower in geographic_terms:
            return True  # Reject standalone geographic references

        # Filter nonsense combinations of adjectives + countries
        # e.g., "good standing britain", "applicable law france"
        if any(country in phrase_lower for country in geographic_terms):
            # Check if it's a real skill or just a location reference
            skill_context_words = ['standards', 'gaap', 'law', 'regulations', 'compliance']
            has_skill_context = any(ctx in phrase_lower for ctx in skill_context_words)

            # If country appears but no skill context, reject
            if not has_skill_context:
                return True  # Reject "good standing britain" type phrases

        # CRITICAL FIX: Filter "applicable X" phrases (too vague)
        if phrase_lower.startswith('applicable '):
            return True  # Reject "applicable law", "applicable regulations"

        # CRITICAL FIX: Filter vague "other X" phrases
        # "other design professionals", "other duties", etc. are NOT skills
        if phrase_lower.startswith('other '):
            return True  # Reject "other X" phrases

        # CRITICAL FIX: Filter "every X" and "any X" phrases (too generic)
        if phrase_lower.startswith('every ') or phrase_lower.startswith('any '):
            return True  # Reject "every size", "any experience"

        # CRITICAL FIX: Filter generic service descriptions
        # These describe what a company does, not candidate skills
        service_descriptors = [
            'inspection services', 'design services', 'consulting services',
            'engineering services', 'professional services', 'support services'
        ]
        if phrase_lower in service_descriptors:
            return True  # Reject generic service descriptions

        # CRITICAL FIX: Filter degree field requirements (NOT skills)
        # "structural or civil engineering" is a degree requirement, not a skill
        degree_field_patterns = [
            'structural or civil engineering', 'civil or structural engineering',
            'structural engineering', 'civil engineering',  # Only if isolated, not in context
            'computer science', 'electrical engineering', 'mechanical engineering'
        ]
        # Only filter if it's the exact phrase without skill context
        if phrase_lower in degree_field_patterns:
            # Check if it appears in an education/degree context in the full text
            # If yes, it's a degree requirement, not a skill
            return True  # Reject degree field names

        # CRITICAL FIX: Filter specific known company/organization names
        # These slip through the general company indicators filter
        specific_company_names = ['bni', 'kpmg', 'pwc', 'ey', 'deloitte']
        if phrase_lower in specific_company_names:
            return True  # Reject specific company names

        # CRITICAL FIX: Filter vague work type descriptors
        vague_work_types = [
            'design work', 'administrative work', 'project work', 'client work',
            'fieldwork', 'desk work', 'construction work', 'office work'
        ]
        if phrase_lower in vague_work_types:
            return True  # Reject vague work descriptions

        # CRITICAL FIX: Filter weird skill concatenations with company types
        # Examples: "usgaap retail companies", "gaap manufacturing firms"
        if 'companies' in phrase_lower or 'firms' in phrase_lower or 'organizations' in phrase_lower:
            # If the phrase contains these words, it's likely a concatenation, not a skill
            return True  # Reject concatenations with company/firm references

        # CRITICAL FIX: Filter workplace culture/environment descriptors
        # "great environment", "professional development", etc. are benefits, not skills
        environment_benefit_words = ['environment', 'culture', 'atmosphere', 'workplace']
        if any(word in phrase_lower for word in environment_benefit_words):
            # Check if it's truly a skill (e.g., "environmental engineering") or just culture talk
            skill_exceptions = ['environmental', 'engineering', 'science', 'studies', 'management']
            has_skill_exception = any(exc in phrase_lower for exc in skill_exceptions)
            if not has_skill_exception:
                return True  # Reject "great environment", "professional development great environment"

        # CRITICAL FIX: Filter references to "professionals" (refers to other people, not your skills)
        if 'professionals' in phrase_lower or 'colleagues' in phrase_lower or 'team members' in phrase_lower:
            return True  # Reject "other design professionals", "work with colleagues"

        # CRITICAL FIX: Filter generic "professional development" (employee benefit)
        if 'professional development' in phrase_lower:
            return True  # Reject professional development benefits

        # CRITICAL FIX: Reject overly long phrases MORE AGGRESSIVELY
        # Phrases with 5+ words are almost always concatenated noise
        # Real skills: "project management" (2), "structural analysis" (2), "concrete design" (2)
        # Noise: "structural engineering design investigation analysis" (5)
        if len(words_in_phrase) >= 5:
            return True  # Reject 5+ word phrases

        # Reject phrases that appear to be multiple skills concatenated together
        # Check for unusually long strings with many nouns/skills mashed together
        # Example: "designconstruction coordination meetings site visits" (6 words, all nouns)
        if len(words_in_phrase) >= 4:
            # Count how many words don't have connecting words (and, or, of, etc.)
            connectors = ['and', 'or', 'of', 'to', 'for', 'with', 'in', 'on', 'at', 'by', 'from']
            non_connector_count = sum(1 for word in words_in_phrase if word not in connectors)

            # If 4+ words and no connectors, or 5+ words with minimal connectors, reject
            connector_count = len(words_in_phrase) - non_connector_count

            # Aggressive: If 4+ non-connector words and 0-1 connectors, likely garbage
            if non_connector_count >= 4 and connector_count <= 1:
                # Exception: Keep common professional multi-word phrases
                professional_exceptions = [
                    'certified public accountant', 'generally accepted accounting principles',
                    'international financial reporting standards', 'accounts payable clerk',
                    'accounts receivable specialist', 'financial planning and analysis'
                ]
                if phrase_lower not in professional_exceptions:
                    return True  # Reject concatenated mess like "coordination meetings site visits"

        return False  # Default: keep it

    # CRITICAL FIX: Pre-process comma-separated lists BEFORE NLP parsing
    # This fixes the issue where "Sports information, marketing and sponsorships"
    # gets parsed as one phrase "sports information marketing" instead of 3 separate skills
    def preprocess_comma_lists(text):
        """
        Splits comma-separated skill lists into individual lines for better NLP parsing.
        Handles patterns like:
        - "X, Y, and Z" -> "X\nY\nZ"
        - "A, B and C" -> "A\nB\nC"
        - "P, Q, R" -> "P\nQ\nR"
        """
        import re

        # Pattern to match comma-separated lists (2+ items with commas, optional "and")
        # Examples: "A, B, and C" or "X, Y, Z" or "P, Q and R"
        # Match groups: (item1), (item2, item3...), (and), (last_item)

        # Find lines that look like comma-separated skill lists
        # Look for patterns within sentences that have commas and potentially "and"
        lines = text.split('\n')
        processed_lines = []

        for line in lines:
            # Check if line contains comma-separated items that look like skills
            # Pattern: word/phrase, word/phrase, [and] word/phrase
            # Only split if we have 2-6 items (avoid splitting long sentences into fragments)

            # Match pattern: "Item1, Item2[, Item3...][and ItemN]"
            # This regex finds comma-separated lists with 2-6 items
            comma_list_pattern = r'\b([A-Za-z][A-Za-z\s\-]{1,30}),\s*([A-Za-z][A-Za-z\s\-]{1,30})(?:,\s*([A-Za-z][A-Za-z\s\-]{1,30}))?(?:,?\s*and\s+([A-Za-z][A-Za-z\s\-]{1,30}))?'

            matches = list(re.finditer(comma_list_pattern, line))

            if matches:
                # Replace comma-separated lists with newline-separated items
                modified_line = line
                for match in reversed(matches):  # Process in reverse to maintain positions
                    # Extract all non-None groups (the individual items)
                    items = [g for g in match.groups() if g is not None]

                    # Only split if we have 2-6 items and they look like skills (not full sentences)
                    if 2 <= len(items) <= 6:
                        # Check if items are short enough to be skills (not full sentences)
                        avg_word_count = sum(len(item.split()) for item in items) / len(items)

                        if avg_word_count <= 4:  # Skills are typically 1-4 words
                            # Replace the matched text with newline-separated items
                            replacement = '\n'.join(items)
                            modified_line = modified_line[:match.start()] + replacement + modified_line[match.end():]

                processed_lines.append(modified_line)
            else:
                processed_lines.append(line)

        return '\n'.join(processed_lines)

    # PHASE 1 PREPROCESSING: Clean text before NLP parsing
    # This fixes "french • debits", "up to", "accountant orcom" type issues
    text = clean_text_for_skill_extraction(text)

    # TEMPORARILY DISABLED: Benefits section detection is too aggressive
    # It was removing 71% of a "Head of Compensation" JD because it flagged
    # "compensation" (the job responsibility) as a benefits section
    # TODO: Need to make this much more context-aware before re-enabling
    # text = detect_and_exclude_benefits_sections(text)

    # Apply comma-list preprocessing
    text = preprocess_comma_lists(text)

    doc = nlp(text)
    candidate_skills = []

    # Collect candidate skills from entities and noun chunks with smart filtering
    for ent in doc.ents:
        if ent.label_ in ["ORG", "GPE", "PRODUCT", "SKILL", "NORP", "WORK_OF_ART"] or len(ent.text.split()) > 1:
            if not is_non_skill_phrase(ent.text):
                candidate_skills.append(ent.text.lower())

    for noun_chunk in doc.noun_chunks:
        # Only consider noun chunks between 1-5 words (avoid overly long concatenations)
        chunk_words = noun_chunk.text.split()
        if 1 < len(chunk_words) <= 5:  # Multi-word phrases, max 5 words
            if not is_non_skill_phrase(noun_chunk.text):
                candidate_skills.append(noun_chunk.text.lower())

    # Extract skills from verb-object dependencies (e.g., "managed payroll" -> "payroll")
    # This catches skills that are mentioned as actions rather than standalone nouns
    action_verbs = {'manage', 'perform', 'conduct', 'execute', 'handle', 'process',
                   'prepare', 'create', 'develop', 'maintain', 'implement', 'oversee',
                   'coordinate', 'administer', 'supervise', 'reconcile', 'analyze',
                   'review', 'ensure', 'support', 'assist', 'complete', 'generate'}

    for token in doc:
        # Look for action verbs with direct objects
        if token.lemma_ in action_verbs:
            for child in token.children:
                if child.dep_ in ['dobj', 'pobj']:  # Direct object or prepositional object
                    # Get the full noun phrase of the object
                    obj_phrase = ' '.join([t.text for t in child.subtree if t.pos_ in ['NOUN', 'PROPN', 'ADJ']])
                    if obj_phrase and len(obj_phrase.split()) <= 3:  # Keep it concise
                        if not is_non_skill_phrase(obj_phrase):
                            candidate_skills.append(obj_phrase.lower())

    # Remove duplicates while preserving order
    seen = set()
    candidate_skills = [x for x in candidate_skills if not (x in seen or seen.add(x))]

    # Attempt 1: Use semantic similarity to match against ontology
    ontology_matched_skills = []
    # Check if ontology exists and has content (handle both DataFrame and list)
    has_ontology = False
    if ontology is not None:
        if isinstance(ontology, list):
            has_ontology = len(ontology) > 0
        else:  # DataFrame
            has_ontology = not ontology.empty

    if has_ontology:
        # Extract skill labels (handle both DataFrame and list)
        if isinstance(ontology, list):
            ontology_labels = ontology
        else:  # DataFrame
            ontology_labels = ontology['preferredLabel'].tolist()

        # Use cached ontology embeddings (MAJOR PERFORMANCE FIX)
        # Previously: encoded 100k+ skills on EVERY analysis (~23s each time)
        # Now: cached after first use, subsequent analyses use cached embeddings
        _, ontology_embs = get_cached_ontology_embeddings(ontology_labels)

        # Only encode candidate skills (typically <100 skills, very fast)
        if candidate_skills:
            candidate_embs = model.encode(candidate_skills)
            for i, cand_emb in enumerate(candidate_embs):
                similarities = util.cos_sim(cand_emb, ontology_embs)[0]
                if max(similarities) > 0.55:  # Lowered threshold for better matching (was 0.6)
                    ontology_matched_skills.append(candidate_skills[i])

    # Attempt 2: Direct extraction using regex patterns
    # CRITICAL FIX: Always run regex extraction, not just when ontology finds < 5 skills
    # This ensures we catch domain-specific terms even when NLP extracts many generic phrases
    direct_extracted_skills = []

    # Extract technical skills patterns (common in tech/specialized fields)
    tech_patterns = re.compile(r'\b(?:python|java|javascript|react|aws|azure|gcp|sql|tableau|power bi|salesforce|sap|oracle|docker|kubernetes|ai|ml|machine learning|deep learning|nlp|data science|agile|scrum|jira|git|ci/cd|api|rest|graphql|tensorflow|pytorch|excel|vba|r)\b', re.IGNORECASE)
    tech_skills = tech_patterns.findall(text.lower())
    direct_extracted_skills.extend(tech_skills)

    # Extract accounting/finance skills (common in finance/accounting roles)
    # Order matters: longer phrases first to avoid partial matching
    accounting_patterns = re.compile(r'\b(?:general ledger accounting|general ledger reconciliation|accounts payable|accounts receivable|bank reconciliation|account reconciliation|month[- ]end close|year[- ]end close|financial reporting|financial statements|balance sheet|income statement|cash flow|variance analysis|cost accounting|tax preparation|general ledger|ap|ar|gl|reconciliation|journal entries|gaap|ifrs|budgeting|forecasting|payroll|bookkeeping|quickbooks|sage|netsuite|erp|cpa|audit|1099|w-2)\b', re.IGNORECASE)
    accounting_skills = accounting_patterns.findall(text.lower())
    direct_extracted_skills.extend(accounting_skills)

    # Extract soft skills and business terms
    soft_skills_patterns = re.compile(r'\b(?:leadership|management|communication|collaboration|problem solving|critical thinking|strategic planning|project management|stakeholder management|negotiation|mentoring|coaching|budget management|financial analysis|market research|sales|marketing|customer service|operations|process improvement|change management|risk management)\b', re.IGNORECASE)
    soft_skills = soft_skills_patterns.findall(text.lower())
    direct_extracted_skills.extend(soft_skills)

    # Clean and deduplicate direct extracted skills
    direct_extracted_skills = list(set([s.lower() for s in direct_extracted_skills]))

    # Combine both approaches and apply final filtering to ALL skills
    all_skills_unfiltered = list(set(ontology_matched_skills + direct_extracted_skills))

    # CRITICAL: Apply is_non_skill_phrase filter to ALL extracted skills
    all_skills = [skill for skill in all_skills_unfiltered if not is_non_skill_phrase(skill)]

    # Filter out dates, years, and year ranges that got extracted as "skills"
    # This removes: "5-7+ years", "june 2007", "3-5 years", "2007-2010", etc.
    date_year_pattern = re.compile(
        r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|'  # Dates: 12/31/2007, 1-15-2008
        r'\b\d+-\d+\+?\s*years?\b|'             # Year ranges: 5-7+ years, 3-5 years
        r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}\b|'  # june 2007
        r'\b\d{4}\s*[-–]\s*\d{4}\b|'           # 2007-2010, 2007 – 2010
        r'\b\d{4}\s*[-–]\s*present\b',         # 2007-present
        re.IGNORECASE
    )
    all_skills = [skill for skill in all_skills if not date_year_pattern.search(skill)]

    # Filter out weird n-gram combinations that don't make sense as skills
    # These are often created when NLP extracts adjacent words that shouldn't be together
    # Examples: "payroll ap", "sage financial report", "clients suppliers", "technical accounting accounts"
    weird_ngram_patterns = [
        r'\b(?:payroll|accounts)\s+(?:ap|ar)\b',  # "payroll ap", "accounts ap"
        r'\b(?:sage|quickbooks)\s+(?:financial|accounting)\s+(?:report|statement)s?\b',  # "sage financial report"
        r'\b(?:clients?|customers?)\s+(?:suppliers?|vendors?)\b',  # "clients suppliers"
        r'\b(?:technical|general)\s+accounting\s+accounts\b',  # "technical accounting accounts"
        r'\b(?:excel|powerpoint|outlook|word)\s+(?:excel|powerpoint|outlook|word)(?:\s+(?:excel|powerpoint|outlook|word))*\b',  # "excel powerpoint outlook"
        r'\b(?:microsoft|ms)\s+office\s+(?:excel|powerpoint|outlook|word)\b',  # "microsoft office word", "ms office excel"
        r'\b(?:microsoft|ms)\s+(?:excel|powerpoint|outlook|word)(?:\s+(?:excel|powerpoint|outlook|word))+\b',  # "microsoft excel word", "ms powerpoint outlook"
        r'\bgono[- ]go\b',  # "gono-go", "gono go" (should be "go/no-go")
        r'\b(?:go[/-]?no[/-]?go|no[/-]?go)\s+(?:and|or)?\s*(?:kick[- ]?off|kickoff)\s+meetings?\b',  # "go/no-go and kick-off meetings"
        r'\b(?:intent|loi)\s+(?:loi|intent)\s+requests?\b',  # "intent loi request" (broken phrase)
        r'\b(?:brochures?|documents?)\s+(?:award|submission)\s+(?:submittals?|documents?)\b',  # "brochures award submittals"
        r'\b(?:various|different|multiple)\s+(?:platforms?|pursuits?|initiatives?)\s+(?:platforms?|pursuits?|initiatives?)\b',  # "various platforms pursuits"
        # Broken concatenations of unrelated concepts
        r'\b(?:sponsorship|marketing)\s+opportunities\s+(?:trade|sales|business)\b',  # "sponsorship opportunities trade"
        r'\b(?:select|key|major)\s+accounts\s+sales\s+representatives?\b',  # "select accounts sales representatives"
        r'\b(?:client|customer)\s+proposals?\s+lead\s+(?:strategy|strategies)\b',  # "client proposals lead strategy"
        r'\bproposals?\s+lead\s+(?:strategy|strategies)\b',  # "proposals lead strategy"
        r'\b(?:accounts?|clients?)\s+(?:representatives?|reps?)\s+(?:sales|marketing)\b',  # "accounts representatives sales"
    ]
    for pattern in weird_ngram_patterns:
        pattern_re = re.compile(pattern, re.IGNORECASE)
        all_skills = [skill for skill in all_skills if not pattern_re.search(skill)]

    # If still very few skills, include high-confidence noun chunks
    if len(all_skills) < 3:
        # Add noun chunks that look like skills (2-4 words, not too common)
        for chunk in candidate_skills[:10]:  # Limit to first 10 to avoid noise
            if 2 <= len(chunk.split()) <= 4 and chunk not in all_skills:
                if not is_non_skill_phrase(chunk):  # Apply filter here too
                    all_skills.append(chunk)

    # Normalize common abbreviations and variations to canonical forms for better matching
    normalized_skills = []
    abbreviation_map = {
        # Abbreviations
        'ap': 'accounts payable',
        'a/p': 'accounts payable',
        'ar': 'accounts receivable',
        'a/r': 'accounts receivable',
        'gl': 'general ledger',
        'g/l': 'general ledger',
        'p&l': 'profit and loss',
        'cpa': 'certified public accountant',
        'gaap': 'generally accepted accounting principles',
        'ifrs': 'international financial reporting standards',

        # Skill variations to canonical forms
        'financial statement preparation': 'financial statements',
        'preparation of financial statements': 'financial statements',
        'financial report writing': 'financial reporting',
        'financial report interpretation': 'financial reporting',
        'general ledger accounting': 'general ledger',
        'account reconciliation': 'reconciliation',
        'payroll processing': 'payroll',
        'balance sheet reconciliation': 'reconciliation',
        'general ledger reconciliation': 'reconciliation',

        # Cash flow variations
        'cash flow': 'cash flow statements',
        'cash flow analysis': 'cash flow statements',
        'cash flow management': 'cash flow statements',
        'cashflow': 'cash flow statements',
    }

    for skill in all_skills:
        skill_lower = skill.lower().strip()
        # Check if skill is an abbreviation that should be normalized
        if skill_lower in abbreviation_map:
            normalized_skills.append(abbreviation_map[skill_lower])
        else:
            # Check if skill contains an abbreviation as a standalone word
            words = skill_lower.split()
            if len(words) == 1 and words[0] in abbreviation_map:
                normalized_skills.append(abbreviation_map[words[0]])
            else:
                normalized_skills.append(skill)

    # Remove duplicates after normalization
    normalized_skills = list(set(normalized_skills))

    # ========== LLM-BASED JOB TITLE INFERENCE - DISABLED ==========
    # ISSUE: This was creating massive false positives by inferring skills from
    # ANY mention of job titles in text, regardless of context.
    # Example: If a compensation JD mentions "work with engineers", it would
    # infer "python, java" etc., which then incorrectly matches with other docs.
    #
    # TODO: Re-enable with more selective approach:
    # - Only infer for PRIMARY role (not every job title mention)
    # - Require job titles to appear in specific contexts (near "position:", etc.)
    # - Consider only applying to JD, not resume
    #
    # # Common job titles to check for in text
    # COMMON_JOB_TITLES = [
    #     'athletic director', 'director', 'manager', 'coordinator', 'controller',
    #     'accounting manager', 'project manager', 'product manager', 'program manager',
    #     'software engineer', 'data analyst', 'business analyst', 'financial analyst',
    #     'marketing manager', 'sales manager', 'operations manager', 'hr manager',
    #     'accountant', 'engineer', 'developer', 'designer', 'consultant',
    #     'chief executive officer', 'ceo', 'cto', 'cfo', 'coo', 'vice president'
    # ]
    #
    # text_lower = text.lower()
    # inferred_skills = set()
    #
    # for title in COMMON_JOB_TITLES:
    #     if title in text_lower:
    #         if title not in _llm_job_title_cache:
    #             _llm_job_title_cache[title] = infer_skills_from_job_title(title)
    #         inferred_skills.update(_llm_job_title_cache[title])
    #
    # normalized_skills.extend(list(inferred_skills))
    # normalized_skills = list(set(normalized_skills))  # Remove duplicates again

    # ========== APPLY POST-EXTRACTION FILTERS ==========
    # Remove non-skill phrases that slipped through
    from utils.skill_filters import filter_skills

    # Convert to set for filtering, then back to list
    normalized_skills_set = set(normalized_skills)
    filtered_skills = filter_skills(normalized_skills_set)
    normalized_skills = list(filtered_skills)

    # ========== APPLY ADVANCED SKILL ENHANCEMENT (ENTERPRISE-GRADE) ==========
    # This layer adds capabilities beyond standard ATS systems:
    # - Synonym & abbreviation expansion (JS → JavaScript, AP → Accounts Payable)
    # - Verb-based extraction (managed budgets → budget management)
    # - Tool/Software NER (Salesforce, Workday, SAP, etc.)
    # - Contextual skill inference (Led team → team leadership)
    # - Industry-specific patterns (compensation, benefits, etc.)
    from utils.skill_enhancer import enhance_skills

    # Detect industry from text for context-aware enhancement
    detected_industries = detect_industry(text)
    primary_industry = detected_industries[0][0] if detected_industries else None

    # Apply enterprise-grade enhancement
    enhanced_skills = enhance_skills(normalized_skills, text, industry=primary_industry)

    # DEBUG: Log extracted skills for troubleshooting
    import os
    debug_log_path = os.path.join(os.getcwd(), 'skill_extraction_debug.log')
    with open(debug_log_path, 'a') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"BASE extraction: {len(normalized_skills)} skills (after filtering)\n")
        f.write(f"ENHANCED extraction: {len(enhanced_skills)} skills (+{len(enhanced_skills) - len(normalized_skills)})\n")
        f.write(f"Primary industry detected: {primary_industry}\n")
        f.write(f"\nEnhanced skills:\n")
        for skill in sorted(enhanced_skills):
            f.write(f"  - {skill}\n")
        f.write(f"{'='*80}\n")

    return enhanced_skills

def extract_seniority(experience_section, levels):
    """
    Enhanced seniority extraction supporting:
    - Multiple title patterns (IC track, management track, creative roles)
    - More date format variations
    - Better year calculation
    """
    total_years = 0
    level_score = 0
    level_count = 0
    current_year = datetime.now().year

    months = {
        'january':1, 'jan':1, 'february':2, 'feb':2, 'march':3, 'mar':3,
        'april':4, 'apr':4, 'may':5, 'june':6, 'jun':6, 'july':7, 'jul':7,
        'august':8, 'aug':8, 'september':9, 'sep':9, 'sept':9, 'october':10,
        'oct':10, 'november':11, 'nov':11, 'december':12, 'dec':12
    }

    # Expanded date patterns to catch more variations
    # Pattern 1: Month Year - Month Year (e.g., "Jan 2014 - Present", "January 2014 - Dec 2020")
    # Pattern 2: Year - Year (e.g., "2014 - Present", "2014-2020")
    # Pattern 3: X years (e.g., "10 years", "5+ years")
    years_pattern = re.compile(
        r'(?:(\w+)[\s\.]*)?\s*(\d{4})\s*(?:–|—|-|to|through)\s*(?:(\w+)[\s\.]*)?\s*(\d{4}|present|current|now|date|to date)|'  # Range with optional months
        r'(\d+)\+?\s*(?:year|yr)s?'  # "5 years" or "10+ years"
    , re.IGNORECASE)

    # Additional pattern for simple "YYYY - YYYY" or "YYYY - Present" without spaces around dash
    simple_year_pattern = re.compile(r'(\d{4})\s*[-–—]\s*(\d{4}|present|current)', re.IGNORECASE)

    # Expanded title patterns for IC track, management, creative roles, and more
    # More comprehensive pattern that catches various seniority indicators
    title_pattern = re.compile(
        r'\b('
        # Junior level
        r'junior|entry|entry-level|associate|intern|trainee|assistant|'
        # Mid level
        r'mid-level|intermediate|specialist|analyst|consultant|engineer|developer|designer|coordinator|'
        # Senior IC track
        r'senior|sr\.|lead|principal|staff|distinguished|fellow|expert|architect|'
        # Management track
        r'manager|head of|director|vp|vice president|c-level|ceo|cto|cfo|coo|cmo|president|'
        # Creative/Non-traditional
        r'freelance|contractor|founder|co-founder|owner|partner'
        r')\b',
        re.IGNORECASE
    )

    # Enhanced scoring map with more granular levels
    score_map = {
        "junior": 1,
        "mid": 2,
        "senior": 3,
        "exec": 4,
        # Additional mappings for granularity
        "entry": 1,
        "intermediate": 2,
        "staff": 3.5,  # Between senior and exec
        "principal": 3.5,
        "distinguished": 3.8,
        "fellow": 4,
        "lead": 3,
        "head": 3.5,
        "founder": 4,
        "partner": 4
    }

    # CRITICAL FIX: Collect all date ranges first, then merge overlapping ranges
    # The bug was that overlapping date ranges (e.g., 2015-2021, 2017-2021, 2019-2021)
    # were being added together, leading to inflated totals like "39 years"
    all_ranges = []  # Collect all date ranges as (start_year, start_month, end_year, end_month) tuples
    processed_ranges = set()  # Track exact (start_year, end_year) tuples to avoid exact duplicates
    explicit_years = 0  # Track years from "X years" format separately

    for line in experience_section:
        line_lower = line.lower()

        # Extract years of experience using main pattern
        years_matches = years_pattern.findall(line_lower)

        # Also check simple year pattern
        simple_matches = simple_year_pattern.findall(line_lower)

        # Process main pattern matches
        for match in years_matches:
            if match[4]:  # "X years" format (e.g., "10+ years")
                years_str = match[4]
                try:
                    explicit_years += int(years_str)
                except:
                    pass
            else:  # Date range format
                start_month = months.get(match[0], 1) if match[0] else 1
                start_year = int(match[1]) if match[1] else 0
                end_month = months.get(match[2], 12) if match[2] else 12

                # Handle various "present" indicators
                if match[3] and match[3].lower() in ['present', 'current', 'now', 'date', 'to date']:
                    end_year = current_year
                else:
                    end_year = int(match[3]) if match[3] and match[3].isdigit() else 0

                if start_year and end_year and start_year <= end_year:
                    # Check if we've already processed this EXACT range
                    range_key = (start_year, end_year)
                    if range_key not in processed_ranges:
                        # Add to collection for later merging of overlaps
                        all_ranges.append((start_year, start_month, end_year, end_month))
                        processed_ranges.add(range_key)

        # Process simple pattern matches (YYYY - YYYY or YYYY - Present)
        for match in simple_matches:
            start_year = int(match[0]) if match[0] else 0
            end_str = match[1].lower() if len(match) > 1 else ""

            if end_str in ['present', 'current', 'now']:
                end_year = current_year
            else:
                try:
                    end_year = int(end_str)
                except:
                    continue

            if start_year and end_year and start_year <= end_year:
                # Check if we've already processed this EXACT range
                range_key = (start_year, end_year)
                if range_key not in processed_ranges:
                    # Add to collection for later merging (use month 1 and 12 as defaults for simple pattern)
                    all_ranges.append((start_year, 1, end_year, 12))
                    processed_ranges.add(range_key)

        # Extract title/seniority level
        title_matches = title_pattern.findall(line_lower)
        for title_word in title_matches:
            level_count += 1

            # Check against configured levels first
            matched = False
            for lvl, keywords in levels.items():
                if any(k in title_word for k in keywords):
                    level_score += score_map.get(lvl, 2)  # Default to mid-level if unknown
                    matched = True
                    break

            # If not matched in config, use enhanced scoring
            if not matched:
                # Direct title word scoring
                if title_word in score_map:
                    level_score += score_map[title_word]
                else:
                    # Default scoring based on common patterns
                    if any(x in title_word for x in ['junior', 'entry', 'intern', 'assistant', 'associate']):
                        level_score += 1
                    elif any(x in title_word for x in ['senior', 'sr', 'lead', 'principal', 'staff', 'architect']):
                        level_score += 3
                    elif any(x in title_word for x in ['director', 'vp', 'chief', 'head', 'president', 'founder']):
                        level_score += 4
                    else:
                        level_score += 2  # Default to mid-level

    avg_level = level_score / max(1, level_count)

    # Merge overlapping date ranges to avoid double-counting
    # For example: 2015-2021, 2017-2021, 2019-2021 should be merged into 2015-2021

    if all_ranges:
        # Sort ranges by start date (year, then month)
        all_ranges.sort(key=lambda x: (x[0], x[1]))

        # Merge overlapping ranges
        merged_ranges = [all_ranges[0]]
        for current in all_ranges[1:]:
            last = merged_ranges[-1]

            # Convert to comparable dates (year + month/12)
            last_end = last[2] + last[3] / 12.0
            current_start = current[0] + current[1] / 12.0

            # If ranges overlap or touch, merge them
            if current_start <= last_end:
                # Extend the last range to include the current range
                current_end = current[2] + current[3] / 12.0
                if current_end > last_end:
                    merged_ranges[-1] = (last[0], last[1], current[2], current[3])
            else:
                # No overlap, add as separate range
                merged_ranges.append(current)

        # Calculate total years from merged ranges
        total_years = 0
        for start_year, start_month, end_year, end_month in merged_ranges:
            years = end_year - start_year + (end_month - start_month) / 12
            total_years += years
        # Combine date range years with explicit years (e.g., "10+ years")
        # Use max to avoid double-counting (e.g., if both date ranges and "X years" exist)
        total_years = max(total_years, explicit_years)
    else:
        # No date ranges found, use explicit years if available
        total_years = explicit_years

    return {
        "years": int(total_years),
        "level": avg_level,
        "level_count": level_count
    }