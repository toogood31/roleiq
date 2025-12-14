import spacy
import json
import re
import pandas as pd
from sentence_transformers import SentenceTransformer, util
from datetime import datetime

nlp = spacy.load("en_core_web_lg")
model = SentenceTransformer('stsb-roberta-large')

# Industry classification keywords
INDUSTRY_KEYWORDS = {
    'technology': ['software', 'engineer', 'developer', 'programming', 'coding', 'ai', 'ml', 'data science', 'cloud', 'devops', 'api', 'saas', 'tech stack'],
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
        if phrase_lower.endswith(' skills') or phrase_lower.endswith(' skill'):
            # Keep technical/specific skills
            technical_prefixes = ['python', 'java', 'sql', 'excel', 'coding', 'programming',
                                'technical', 'analytical', 'communication', 'leadership',
                                'accounting', 'financial', 'data', 'project management']
            is_technical = any(prefix in phrase_lower for prefix in technical_prefixes)

            # Reject vague "X skills" like "staff skills", "work skills", "individual skills"
            vague_skill_prefixes = ['staff', 'work', 'individual', 'personal', 'professional',
                                   'general', 'basic', 'core', 'key', 'essential', 'important']
            is_vague = any(prefix in phrase_lower for prefix in vague_skill_prefixes)

            if is_vague and not is_technical:
                return True  # Reject vague skill phrases

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
            'social declarations', 'social security declarations',  # regional/foreign terms
            'verbal written presentation', 'written presentation', 'verbal presentation',
            'ongoing administration', 'ongoing support', 'ongoing maintenance',
            'teammates', 'team members', 'colleagues', 'peers', 'coworkers',
            'materials', 'documents', 'files', 'reports', 'paperwork'  # too generic without context
        ]

        # Also reject standalone vague words
        vague_single_words = [
            'book', 'books', 'experience', 'knowledge', 'understanding',
            'documents', 'document', 'wages', 'wage', 'records', 'record',
            'management', 'processes', 'duties', 'tasks', 'functions',
            'skills', 'abilities', 'field', 'area', 'department',
            'teammates', 'materials', 'files', 'reports', 'paperwork',
            'colleagues', 'peers', 'coworkers', 'administration', 'support',
            'maintenance', 'presentation', 'presentations'
        ]
        if phrase_lower in vague_single_words:
            return True

        # Reject vague two-word combinations that aren't specific skills
        vague_2word_patterns = [
            'bank documents', 'tax documents', 'financial documents',
            'annual wages', 'senior management', 'middle management',
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

        # Reject overly long phrases (likely concatenated noise from noun chunks)
        # Skills should be concise - max 5 words for compound terms
        if len(words_in_phrase) > 5:
            return True

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
    if ontology and len(ontology) > 0:
        ontology_embs = model.encode(ontology)
        candidate_embs = model.encode(candidate_skills)
        for i, cand_emb in enumerate(candidate_embs):
            similarities = util.cos_sim(cand_emb, ontology_embs)[0]
            if max(similarities) > 0.55:  # Lowered threshold for better matching (was 0.6)
                ontology_matched_skills.append(candidate_skills[i])

    # Attempt 2: Fallback - Direct extraction if ontology matching yields few results
    # This handles emerging skills, company-specific tools, industry jargon
    direct_extracted_skills = []
    if len(ontology_matched_skills) < 5:  # If we found fewer than 5 ontology matches
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

    # If still very few skills, include high-confidence noun chunks
    if len(all_skills) < 3:
        # Add noun chunks that look like skills (2-4 words, not too common)
        for chunk in candidate_skills[:10]:  # Limit to first 10 to avoid noise
            if 2 <= len(chunk.split()) <= 4 and chunk not in all_skills:
                if not is_non_skill_phrase(chunk):  # Apply filter here too
                    all_skills.append(chunk)

    # Normalize common abbreviations to full forms for better matching
    normalized_skills = []
    abbreviation_map = {
        'ap': 'accounts payable',
        'a/p': 'accounts payable',
        'ar': 'accounts receivable',
        'a/r': 'accounts receivable',
        'gl': 'general ledger',
        'g/l': 'general ledger',
        'p&l': 'profit and loss',
        'cpa': 'certified public accountant',
        'gaap': 'generally accepted accounting principles',
        'ifrs': 'international financial reporting standards'
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

    return normalized_skills

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

    for line in experience_section:
        line_lower = line.lower()

        # Extract years of experience using main pattern
        years_matches = years_pattern.findall(line_lower)

        # Also check simple year pattern
        simple_matches = simple_year_pattern.findall(line_lower)

        # Process main pattern matches
        for match in years_matches:
            if match[4]:  # "X years" format
                years_str = match[4]
                try:
                    total_years += int(years_str)
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
                    years = end_year - start_year + (end_month - start_month) / 12
                    total_years += max(0, years)  # Ensure non-negative

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
                years = end_year - start_year
                total_years += max(0, years)  # Ensure non-negative

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

    # Fallback: ALWAYS scan for earliest year in experience section as a safety check
    # Use the MAXIMUM of regex-calculated years vs fallback years to avoid undercounting
    fallback_years = 0
    if experience_section:
        all_text = ' '.join(experience_section).lower()
        # Find all 4-digit years
        year_matches = re.findall(r'\b(19\d{2}|20\d{2})\b', all_text)
        if year_matches:
            years_found = [int(y) for y in year_matches if 1990 <= int(y) <= current_year]
            if years_found:
                earliest_year = min(years_found)
                # Only count if earliest year is reasonable (within last 50 years)
                if current_year - earliest_year <= 50:
                    fallback_years = current_year - earliest_year
                    # Cap at 40 years to avoid unrealistic values
                    fallback_years = min(fallback_years, 40)

    # Use the MAXIMUM of calculated vs fallback to avoid undercounting
    # This handles cases where regex partially matches but misses some experience
    total_years = max(total_years, fallback_years)

    return {
        "years": int(total_years),
        "level": avg_level,
        "level_count": level_count
    }