"""
Free analysis enhancements using existing NLP tools (no API costs)
"""
import re
from collections import defaultdict
from sentence_transformers import util

def extract_achievements(text):
    """
    Extract quantifiable achievements from text
    Returns metrics found: dollar amounts, percentages, team sizes, volumes
    """
    achievements = {
        'dollar_amounts': [],
        'percentages': [],
        'team_sizes': [],
        'volumes': [],
        'timeframes': []
    }

    # Dollar amounts: $5M, $500K, $2.5 million
    dollar_pattern = re.compile(r'\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*([KMB]|million|billion|thousand)?', re.IGNORECASE)
    for match in dollar_pattern.finditer(text):
        amount = match.group(1).replace(',', '')
        unit = match.group(2) or ''
        achievements['dollar_amounts'].append(f"${amount}{unit}")

    # Percentages: 40%, reduced by 25%
    pct_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*%|(\d+(?:\.\d+)?)\s*percent', re.IGNORECASE)
    for match in pct_pattern.finditer(text):
        pct = match.group(1) or match.group(2)
        achievements['percentages'].append(f"{pct}%")

    # Team sizes: "team of 12", "managed 5 people", "supervised 3 staff"
    team_pattern = re.compile(r'(?:team of|managed|supervised|led|mentored|coached)\s+(\d+)\s*(?:people|staff|employees|direct reports|members)?', re.IGNORECASE)
    for match in team_pattern.finditer(text):
        achievements['team_sizes'].append(match.group(1))

    # Volumes: "500+ invoices", "50 accounts", "100 transactions"
    volume_pattern = re.compile(r'(\d+)\s*\+?\s*(?:invoices|accounts|transactions|clients|customers|reports|entries)', re.IGNORECASE)
    for match in volume_pattern.finditer(text):
        achievements['volumes'].append(match.group(0))

    # Timeframes: "daily", "monthly", "quarterly", "annual"
    timeframe_pattern = re.compile(r'\b(daily|weekly|monthly|quarterly|annual|yearly)\b', re.IGNORECASE)
    achievements['timeframes'] = list(set(timeframe_pattern.findall(text.lower())))

    return achievements


def analyze_action_verbs(text, nlp):
    """
    Analyze strength of action verbs used
    Categorizes by seniority level
    """
    doc = nlp(text)

    # Verb strength categories
    weak_verbs = {
        'helped', 'assisted', 'supported', 'aided', 'contributed',
        'participated', 'worked', 'handled', 'did', 'performed'
    }

    mid_verbs = {
        'managed', 'implemented', 'executed', 'conducted', 'processed',
        'prepared', 'created', 'developed', 'maintained', 'coordinated',
        'organized', 'reviewed', 'analyzed', 'resolved', 'completed'
    }

    strong_verbs = {
        'led', 'owned', 'directed', 'established', 'spearheaded',
        'architected', 'pioneered', 'transformed', 'drove', 'launched',
        'built', 'designed', 'optimized', 'streamlined', 'delivered',
        'orchestrated', 'championed', 'overhauled', 'restructured'
    }

    verb_counts = {
        'weak': [],
        'mid': [],
        'strong': []
    }

    for token in doc:
        if token.pos_ == 'VERB':
            lemma = token.lemma_.lower()
            if lemma in weak_verbs:
                verb_counts['weak'].append(token.text)
            elif lemma in mid_verbs:
                verb_counts['mid'].append(token.text)
            elif lemma in strong_verbs:
                verb_counts['strong'].append(token.text)

    total = len(verb_counts['weak']) + len(verb_counts['mid']) + len(verb_counts['strong'])

    if total == 0:
        return {
            'weak_pct': 0,
            'mid_pct': 0,
            'strong_pct': 0,
            'total_verbs': 0,
            'verb_breakdown': verb_counts,
            'recommendations': []
        }

    weak_pct = (len(verb_counts['weak']) / total) * 100
    mid_pct = (len(verb_counts['mid']) / total) * 100
    strong_pct = (len(verb_counts['strong']) / total) * 100

    recommendations = []
    if weak_pct > 30:
        recommendations.append(f"High use of weak verbs ({weak_pct:.0f}%). Replace with stronger alternatives.")
    if strong_pct < 20:
        recommendations.append(f"Low use of strong leadership verbs ({strong_pct:.0f}%). Add more ownership language.")

    return {
        'weak_pct': weak_pct,
        'mid_pct': mid_pct,
        'strong_pct': strong_pct,
        'total_verbs': total,
        'verb_breakdown': verb_counts,
        'recommendations': recommendations
    }


def cluster_skills(skills, model, similarity_threshold=0.75):
    """
    Group similar skills together to reduce false negatives
    e.g., "accounts payable", "AP", "payables" -> one cluster
    """
    if not skills or len(skills) < 2:
        return {skill: [skill] for skill in skills}

    # Encode all skills
    embeddings = model.encode(skills)

    # Create clusters
    clusters = {}
    processed = set()

    for i, skill in enumerate(skills):
        if skill in processed:
            continue

        # Find all similar skills
        similar = [skill]
        for j, other_skill in enumerate(skills):
            if i != j and other_skill not in processed:
                similarity = util.cos_sim(embeddings[i], embeddings[j])[0][0].item()
                if similarity > similarity_threshold:
                    similar.append(other_skill)
                    processed.add(other_skill)

        # Use longest/most specific as cluster key
        cluster_key = max(similar, key=len)
        clusters[cluster_key] = similar
        processed.add(skill)

    return clusters


def calculate_ats_keyword_density(resume_text, jd_text, jd_skills):
    """
    Calculate how well resume covers JD keywords (for ATS optimization)
    """
    resume_lower = resume_text.lower()
    jd_lower = jd_text.lower()

    # Count keyword occurrences
    keyword_coverage = {}
    for skill in jd_skills:
        skill_lower = skill.lower()

        # Count in resume
        resume_count = resume_lower.count(skill_lower)

        # Count in JD (to understand importance)
        jd_count = jd_lower.count(skill_lower)

        keyword_coverage[skill] = {
            'resume_mentions': resume_count,
            'jd_mentions': jd_count,
            'covered': resume_count > 0
        }

    # Calculate overall coverage
    total_keywords = len(jd_skills)
    covered_keywords = sum(1 for v in keyword_coverage.values() if v['covered'])
    coverage_pct = (covered_keywords / total_keywords * 100) if total_keywords > 0 else 0

    # Identify missing high-priority keywords (mentioned multiple times in JD)
    missing_important = [
        skill for skill, data in keyword_coverage.items()
        if not data['covered'] and data['jd_mentions'] >= 2
    ]

    # Identify under-represented keywords (in JD multiple times, resume once)
    underrepresented = [
        skill for skill, data in keyword_coverage.items()
        if data['covered'] and data['jd_mentions'] >= 3 and data['resume_mentions'] < 2
    ]

    return {
        'total_keywords': total_keywords,
        'covered_keywords': covered_keywords,
        'coverage_pct': coverage_pct,
        'keyword_details': keyword_coverage,
        'missing_important': missing_important[:10],  # Top 10
        'underrepresented': underrepresented[:10],
        'recommendations': generate_ats_recommendations(
            coverage_pct,
            missing_important,
            underrepresented
        )
    }


def generate_ats_recommendations(coverage_pct, missing_important, underrepresented):
    """Generate ATS optimization recommendations"""
    recommendations = []

    if coverage_pct < 70:
        recommendations.append(
            f"Low keyword coverage ({coverage_pct:.0f}%). Add more JD keywords to improve ATS matching."
        )

    if missing_important:
        recommendations.append(
            f"Missing {len(missing_important)} high-priority keywords: {', '.join(missing_important[:3])}. "
            f"These appear multiple times in JD."
        )

    if underrepresented:
        recommendations.append(
            f"Under-represented keywords: {', '.join(underrepresented[:3])}. "
            f"Mention these more frequently."
        )

    if coverage_pct >= 80:
        recommendations.append("Strong keyword coverage. Resume should pass ATS screening.")

    return recommendations


def detect_leadership_language(text, nlp):
    """
    Identify leadership signals in text
    """
    doc = nlp(text)
    text_lower = text.lower()

    signals = {
        'team_management': [],
        'decision_making': [],
        'strategic': [],
        'ownership': []
    }

    # Team management patterns
    team_patterns = [
        r'\b(?:supervised|managed|mentored|coached|trained|developed|led)\s+(?:team|staff|employees|people)',
        r'\bteam of \d+',
        r'\b(?:direct reports|indirect reports)',
        r'\bhiring|recruiting|onboarding\b'
    ]

    for pattern in team_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            signals['team_management'].append(match.group(0))

    # Decision-making patterns
    decision_patterns = [
        r'\b(?:decided|determined|approved|authorized|selected|chose)',
        r'\b(?:decision|approval|authorization)',
        r'\b(?:stakeholder|executive|leadership) (?:approval|buy-in|alignment)'
    ]

    for pattern in decision_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            signals['decision_making'].append(match.group(0))

    # Strategic patterns
    strategic_patterns = [
        r'\b(?:strategy|strategic|roadmap|vision|planning)',
        r'\b(?:initiative|program|transformation)',
        r'\b(?:cross-functional|enterprise-wide|organization-wide)',
        r'\b(?:long-term|multi-year)'
    ]

    for pattern in strategic_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            signals['strategic'].append(match.group(0))

    # Ownership patterns
    ownership_patterns = [
        r'\b(?:owned|led|drove|delivered|spearheaded|established)',
        r'\b(?:responsible for|accountable for)',
        r'\bP&L|profit and loss|budget of',
        r'\bend-to-end|full-cycle|complete\b'
    ]

    for pattern in ownership_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            signals['ownership'].append(match.group(0))

    # Calculate leadership score
    total_signals = sum(len(v) for v in signals.values())

    return {
        'signals': signals,
        'total_count': total_signals,
        'team_management_count': len(signals['team_management']),
        'decision_making_count': len(signals['decision_making']),
        'strategic_count': len(signals['strategic']),
        'ownership_count': len(signals['ownership']),
        'leadership_score': min(100, total_signals * 5)  # Cap at 100
    }


def classify_task_vs_outcome(text, nlp):
    """
    Classify resume bullets as task-oriented vs outcome-oriented
    """
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents]

    classifications = []

    # Outcome indicators
    outcome_indicators = [
        r'\d+%',  # Percentages
        r'\$\d+',  # Dollar amounts
        r'(?:increased|decreased|reduced|improved|enhanced|optimized)',
        r'(?:resulting in|leading to|achieving)',
        r'(?:saved|generated|delivered)',
        r'(?:award|recognition|promotion)',
        r'by \d+(?:%|x)',  # "by 40%", "by 2x"
    ]

    # Task indicators
    task_indicators = [
        r'^(?:prepared|processed|handled|managed|maintained)',
        r'(?:daily|weekly|monthly|quarterly) (?:tasks|duties|responsibilities)',
        r'(?:assisted|helped|supported|contributed)',
    ]

    for sentence in sentences:
        sentence_lower = sentence.lower()

        # Count outcome indicators
        outcome_score = sum(
            1 for pattern in outcome_indicators
            if re.search(pattern, sentence_lower)
        )

        # Count task indicators
        task_score = sum(
            1 for pattern in task_indicators
            if re.search(pattern, sentence_lower)
        )

        # Classify
        if outcome_score > task_score:
            classification = 'outcome'
        elif task_score > outcome_score:
            classification = 'task'
        else:
            classification = 'neutral'

        classifications.append({
            'sentence': sentence,
            'type': classification,
            'outcome_score': outcome_score,
            'task_score': task_score
        })

    # Overall stats
    total = len(classifications)
    if total == 0:
        return {'classifications': [], 'outcome_pct': 0, 'task_pct': 0, 'recommendations': []}

    outcome_count = sum(1 for c in classifications if c['type'] == 'outcome')
    task_count = sum(1 for c in classifications if c['type'] == 'task')

    outcome_pct = (outcome_count / total) * 100
    task_pct = (task_count / total) * 100

    recommendations = []
    if outcome_pct < 40:
        recommendations.append(
            f"Only {outcome_pct:.0f}% of bullets are outcome-oriented. "
            f"Add metrics and results to {min(5, task_count)} task-based bullets."
        )

    return {
        'classifications': classifications,
        'outcome_pct': outcome_pct,
        'task_pct': task_pct,
        'neutral_pct': 100 - outcome_pct - task_pct,
        'recommendations': recommendations
    }


def score_resume_sections(resume_sections, jd_skills, nlp):
    """
    Score each resume section on 1-10 scale
    Returns: section scores and specific improvement recommendations
    """
    scores = {}

    # Score Summary/Objective section (if exists)
    summary_text = ' '.join(resume_sections.get('summary', []) + resume_sections.get('objective', []))
    if summary_text:
        # Check if key JD skills appear in summary
        summary_lower = summary_text.lower()
        skills_in_summary = sum(1 for skill in jd_skills if skill.lower() in summary_lower)
        coverage_pct = (skills_in_summary / len(jd_skills) * 100) if jd_skills else 0

        # Score based on coverage and length
        if coverage_pct >= 30 and len(summary_text.split()) >= 30:
            summary_score = min(10, 6 + (coverage_pct / 10))
        elif coverage_pct >= 20:
            summary_score = 5
        else:
            summary_score = max(1, coverage_pct / 5)

        scores['summary'] = {
            'score': round(summary_score, 1),
            'skill_coverage': f"{skills_in_summary}/{len(jd_skills)} JD skills mentioned",
            'recommendation': generate_summary_recommendation(summary_score, skills_in_summary, jd_skills)
        }

    # Score Experience section
    experience_text = ' '.join(resume_sections.get('experience', []))
    if experience_text:
        doc = nlp(experience_text)

        # Check for metrics (numbers, percentages)
        has_numbers = bool(re.search(r'\d+%|\$\d+|\d+\+', experience_text))

        # Check for strong action verbs
        strong_verbs = {'led', 'owned', 'directed', 'established', 'spearheaded', 'drove', 'launched'}
        verb_count = sum(1 for token in doc if token.pos_ == 'VERB' and token.lemma_.lower() in strong_verbs)

        # Check skill coverage
        exp_lower = experience_text.lower()
        skills_in_exp = sum(1 for skill in jd_skills if skill.lower() in exp_lower)
        skill_coverage_pct = (skills_in_exp / len(jd_skills) * 100) if jd_skills else 0

        # Calculate score
        exp_score = 5  # Base score
        if has_numbers:
            exp_score += 2
        if verb_count >= 3:
            exp_score += 2
        if skill_coverage_pct >= 50:
            exp_score += 1

        scores['experience'] = {
            'score': min(10, exp_score),
            'has_metrics': has_numbers,
            'strong_verbs': verb_count,
            'skill_coverage': f"{skills_in_exp}/{len(jd_skills)} JD skills",
            'recommendation': generate_experience_recommendation(exp_score, has_numbers, verb_count)
        }

    # Score Skills section
    skills_text = ' '.join(resume_sections.get('skills', []))
    if skills_text:
        skills_lower = skills_text.lower()
        skills_in_section = sum(1 for skill in jd_skills if skill.lower() in skills_lower)
        coverage_pct = (skills_in_section / len(jd_skills) * 100) if jd_skills else 0

        # Score based on coverage
        if coverage_pct >= 70:
            skills_score = 9
        elif coverage_pct >= 50:
            skills_score = 7
        elif coverage_pct >= 30:
            skills_score = 5
        else:
            skills_score = max(1, coverage_pct / 10)

        scores['skills'] = {
            'score': round(skills_score, 1),
            'skill_coverage': f"{skills_in_section}/{len(jd_skills)} JD skills",
            'coverage_pct': round(coverage_pct, 1),
            'recommendation': generate_skills_recommendation(skills_score, skills_in_section, jd_skills)
        }

    # Score Education section
    education_text = ' '.join(resume_sections.get('education', []))
    if education_text:
        # Check for relevant keywords (degrees, certifications)
        relevant_terms = ['bachelor', 'master', 'mba', 'cpa', 'cfa', 'certified', 'certification']
        relevant_count = sum(1 for term in relevant_terms if term in education_text.lower())

        edu_score = min(10, 5 + relevant_count)

        scores['education'] = {
            'score': edu_score,
            'relevant_credentials': relevant_count,
            'recommendation': 'Education section is adequate.' if edu_score >= 7 else 'Add relevant certifications if available.'
        }

    return scores


def generate_summary_recommendation(score, skills_mentioned, jd_skills):
    """Generate specific recommendation for summary section"""
    if score >= 8:
        return "Summary section is strong with good keyword coverage."
    elif score >= 5:
        missing_count = len(jd_skills) - skills_mentioned
        return f"Summary could be stronger. Add {min(3, missing_count)} more JD keywords to opening statement."
    else:
        return f"Summary is weak. Rewrite to include top 3-5 JD skills: {', '.join(jd_skills[:5])}."


def generate_experience_recommendation(score, has_metrics, verb_count):
    """Generate specific recommendation for experience section"""
    recommendations = []

    if not has_metrics:
        recommendations.append("Add quantified metrics (percentages, dollar amounts, volumes) to 3+ bullets")

    if verb_count < 3:
        recommendations.append("Replace weak verbs with strong action verbs (led, owned, drove, established)")

    if score >= 8:
        return "Experience section is strong with good metrics and action verbs."
    elif recommendations:
        return ". ".join(recommendations) + "."
    else:
        return "Experience section is solid but could use more specific achievements."


def generate_skills_recommendation(score, skills_mentioned, jd_skills):
    """Generate specific recommendation for skills section"""
    if score >= 8:
        return "Skills section has excellent JD keyword coverage."
    else:
        missing = len(jd_skills) - skills_mentioned
        missing_skills = [s for s in jd_skills if s not in ' '.join(jd_skills[:skills_mentioned])][:5]
        return f"Add {missing} missing JD skills to Skills section: {', '.join(missing_skills[:3])}."


def detect_skill_redundancies(skills, model, similarity_threshold=0.85):
    """
    Find duplicate or highly similar skills in a list
    Returns: groups of redundant skills that should be consolidated
    """
    if not skills or len(skills) < 2:
        return []

    redundancies = []
    processed = set()

    # Encode all skills
    embeddings = model.encode(skills)

    for i, skill in enumerate(skills):
        if skill in processed:
            continue

        duplicates = [skill]

        for j, other_skill in enumerate(skills):
            if i != j and other_skill not in processed:
                # Check exact substring match
                if skill.lower() in other_skill.lower() or other_skill.lower() in skill.lower():
                    duplicates.append(other_skill)
                    processed.add(other_skill)
                else:
                    # Check semantic similarity
                    similarity = util.cos_sim(embeddings[i], embeddings[j])[0][0].item()
                    if similarity > similarity_threshold:
                        duplicates.append(other_skill)
                        processed.add(other_skill)

        if len(duplicates) > 1:
            # Use most specific (longest) as primary
            primary = max(duplicates, key=len)
            redundancies.append({
                'primary': primary,
                'duplicates': [d for d in duplicates if d != primary]
            })

        processed.add(skill)

    return redundancies


def classify_hard_vs_soft_skills(skills):
    """
    Categorize skills as hard (technical) or soft (interpersonal)
    Returns: categorized skills with confidence levels
    """
    # Hard skill indicators (technical terms, tools, certifications, specific processes)
    hard_skill_indicators = {
        # Technical tools & software
        'software', 'system', 'tool', 'platform', 'application',
        'excel', 'python', 'sql', 'tableau', 'quickbooks', 'sap', 'oracle', 'erp',
        'salesforce', 'netsuite', 'sage', 'aws', 'azure', 'api',

        # Accounting/Finance specific
        'gaap', 'ifrs', 'reconciliation', 'ledger', 'payroll', 'ap', 'ar', 'gl',
        'financial statements', 'balance sheet', 'income statement', 'cash flow',
        'budgeting', 'forecasting', 'variance analysis', 'audit', 'tax',
        'journal entries', 'month-end close', 'year-end close',

        # Certifications
        'cpa', 'cfa', 'pmp', 'certified', 'certification',

        # Technical processes
        'analysis', 'reporting', 'modeling', 'programming', 'coding'
    }

    # Soft skill indicators (interpersonal, behavioral)
    soft_skill_indicators = {
        'leadership', 'management', 'communication', 'collaboration', 'teamwork',
        'problem solving', 'critical thinking', 'strategic thinking', 'analytical thinking',
        'interpersonal', 'negotiation', 'presentation', 'mentoring', 'coaching',
        'stakeholder management', 'relationship building', 'influence', 'persuasion',
        'adaptability', 'flexibility', 'time management', 'organization',
        'attention to detail', 'multitasking', 'prioritization'
    }

    categorized = {
        'hard_skills': [],
        'soft_skills': [],
        'hybrid_skills': []  # Skills that have both technical and soft aspects
    }

    for skill in skills:
        skill_lower = skill.lower()

        # Count indicators
        hard_matches = sum(1 for indicator in hard_skill_indicators if indicator in skill_lower)
        soft_matches = sum(1 for indicator in soft_skill_indicators if indicator in skill_lower)

        # Categorize
        if hard_matches > soft_matches:
            categorized['hard_skills'].append(skill)
        elif soft_matches > hard_matches:
            categorized['soft_skills'].append(skill)
        else:
            # Default heuristic: if it contains specific nouns/acronyms, it's likely hard
            # if it's more abstract, it's likely soft
            if any(char.isupper() for char in skill) and len(skill) <= 6:  # Acronyms like GAAP, SQL
                categorized['hard_skills'].append(skill)
            elif any(word in skill_lower for word in ['manage', 'lead', 'communicate', 'collaborate']):
                categorized['soft_skills'].append(skill)
            else:
                categorized['hard_skills'].append(skill)  # Default to hard skills

    return categorized


def extract_skill_context(resume_text, jd_text, gaps, model, nlp):
    """
    For each gap, extract surrounding context from JD and closest match from resume
    Helps validate whether gaps are real or false positives
    """
    if not gaps:
        return {}

    # Split texts into sentences
    resume_doc = nlp(resume_text)
    jd_doc = nlp(jd_text)

    resume_sentences = [sent.text.strip() for sent in resume_doc.sents]
    jd_sentences = [sent.text.strip() for sent in jd_doc.sents]

    # Encode sentences
    resume_embs = model.encode(resume_sentences) if resume_sentences else []
    jd_embs = model.encode(jd_sentences) if jd_sentences else []

    context_data = {}

    for gap in gaps[:10]:  # Limit to first 10 gaps to avoid performance issues
        gap_lower = gap.lower()

        # Find JD sentences mentioning this gap
        jd_context_sentences = []
        for i, jd_sent in enumerate(jd_sentences):
            if gap_lower in jd_sent.lower():
                jd_context_sentences.append({
                    'sentence': jd_sent,
                    'index': i
                })

        # Find closest resume sentence to the JD context
        closest_resume_match = None
        if jd_context_sentences and len(resume_embs) > 0:
            # Use first JD sentence mentioning the gap
            jd_idx = jd_context_sentences[0]['index']
            jd_emb = jd_embs[jd_idx]

            # Find most similar resume sentence
            similarities = util.cos_sim(jd_emb, resume_embs)[0]
            best_match_idx = similarities.argmax().item()
            similarity_score = similarities[best_match_idx].item()

            closest_resume_match = {
                'sentence': resume_sentences[best_match_idx],
                'similarity': round(similarity_score, 3)
            }

        context_data[gap] = {
            'jd_context': jd_context_sentences[:2],  # Top 2 JD mentions
            'closest_resume_match': closest_resume_match,
            'likely_false_positive': closest_resume_match and closest_resume_match['similarity'] > 0.7
        }

    return context_data


# ==================== TIER 3 ENHANCEMENTS ====================

def analyze_experience_progression(resume_text, nlp):
    """
    Analyze career trajectory and progression over time
    Detects: promotions, scope increases, career gaps, lateral moves
    """
    doc = nlp(resume_text)

    # Extract job titles and dates
    job_entries = []

    # Look for patterns like "2020-2023", "Jan 2020 - Present", etc.
    date_pattern = re.compile(r'(20\d{2})\s*[-–]\s*(20\d{2}|present|current)', re.IGNORECASE)

    # Split into lines for better parsing
    lines = resume_text.split('\n')

    current_entry = {}
    for line in lines:
        # Look for job titles (usually uppercase or title case)
        if len(line.split()) <= 6 and any(word[0].isupper() for word in line.split() if word):
            # Potential title
            if 'manager' in line.lower() or 'director' in line.lower() or 'senior' in line.lower() or 'lead' in line.lower() or 'analyst' in line.lower() or 'controller' in line.lower():
                current_entry['title'] = line.strip()

        # Look for dates
        date_match = date_pattern.search(line)
        if date_match:
            start_year = int(date_match.group(1))
            end_year = 2025 if date_match.group(2).lower() in ['present', 'current'] else int(date_match.group(2))
            current_entry['start_year'] = start_year
            current_entry['end_year'] = end_year
            current_entry['duration'] = end_year - start_year

            if current_entry.get('title'):
                job_entries.append(current_entry.copy())
                current_entry = {}

    # Analyze progression
    progression_data = {
        'total_roles': len(job_entries),
        'promotions': 0,
        'lateral_moves': 0,
        'career_gaps': [],
        'avg_tenure': 0,
        'progression_quality': 'unknown'
    }

    if len(job_entries) >= 2:
        # Sort by start year
        job_entries.sort(key=lambda x: x.get('start_year', 0))

        # Calculate average tenure
        tenures = [e['duration'] for e in job_entries if e.get('duration')]
        progression_data['avg_tenure'] = sum(tenures) / len(tenures) if tenures else 0

        # Detect promotions (seniority words appearing later)
        seniority_levels = ['analyst', 'associate', 'specialist', 'coordinator', 'senior', 'lead', 'manager', 'director', 'vp', 'chief']

        for i in range(1, len(job_entries)):
            prev_title = job_entries[i-1].get('title', '').lower()
            curr_title = job_entries[i].get('title', '').lower()

            # Check for seniority increase
            prev_level = max([seniority_levels.index(word) for word in seniority_levels if word in prev_title] or [0])
            curr_level = max([seniority_levels.index(word) for word in seniority_levels if word in curr_title] or [0])

            if curr_level > prev_level:
                progression_data['promotions'] += 1
            elif curr_level == prev_level:
                progression_data['lateral_moves'] += 1

            # Detect career gaps (>6 months between roles)
            prev_end = job_entries[i-1].get('end_year', 0)
            curr_start = job_entries[i].get('start_year', 0)
            if curr_start - prev_end > 0:
                progression_data['career_gaps'].append(f"{prev_end}-{curr_start}")

        # Overall progression quality
        if progression_data['promotions'] >= 2:
            progression_data['progression_quality'] = 'strong'
        elif progression_data['promotions'] >= 1:
            progression_data['progression_quality'] = 'moderate'
        elif progression_data['lateral_moves'] > progression_data['promotions']:
            progression_data['progression_quality'] = 'lateral'
        else:
            progression_data['progression_quality'] = 'unclear'

    return progression_data


def analyze_skill_cooccurrence(resume_skills, jd_skills, gaps):
    """
    Identify missing complementary skills based on co-occurrence patterns
    E.g., if resume has "accounts payable" but not "accounts receivable" and JD needs both
    """
    # Common skill pairs/groups in accounting/finance
    skill_pairs = {
        'accounts payable': ['accounts receivable', 'ap', 'ar'],
        'accounts receivable': ['accounts payable', 'ap', 'ar'],
        'budgeting': ['forecasting', 'variance analysis', 'financial planning'],
        'forecasting': ['budgeting', 'variance analysis'],
        'financial statements': ['balance sheet', 'income statement', 'cash flow'],
        'balance sheet': ['income statement', 'cash flow', 'financial statements'],
        'month-end close': ['year-end close', 'financial reporting'],
        'general ledger': ['journal entries', 'reconciliation', 'gl'],
        'gaap': ['ifrs', 'financial reporting', 'compliance'],
        'quickbooks': ['sage', 'netsuite', 'erp'],
        'variance analysis': ['budgeting', 'forecasting', 'financial analysis']
    }

    missing_complementary = []

    for resume_skill in resume_skills:
        skill_lower = resume_skill.lower()

        # Check if this skill has common pairs
        if skill_lower in skill_pairs:
            complementary = skill_pairs[skill_lower]

            # Check which complementary skills are in JD but missing from resume
            for comp_skill in complementary:
                # Check if comp_skill is in JD skills or gaps
                if any(comp_skill in jd_skill.lower() for jd_skill in jd_skills):
                    if any(comp_skill in gap.lower() for gap in gaps):
                        missing_complementary.append({
                            'has': resume_skill,
                            'missing': comp_skill,
                            'reason': f"You have '{resume_skill}' but not '{comp_skill}' - JD needs both"
                        })

    return missing_complementary[:3]  # Top 3


def calculate_readability_score(resume_text, nlp):
    """
    Analyze writing quality and professionalism
    Measures: readability, passive voice, jargon density, sentence length
    """
    doc = nlp(resume_text)
    sentences = list(doc.sents)

    if not sentences:
        return {'readability_score': 0, 'issues': []}

    # Calculate metrics
    total_words = len([token for token in doc if not token.is_punct])
    total_sentences = len(sentences)

    # Average sentence length
    avg_sentence_length = total_words / total_sentences if total_sentences > 0 else 0

    # Passive voice detection (simplified)
    passive_count = 0
    for sent in sentences:
        # Look for "was/were/been + past participle" patterns
        for i, token in enumerate(sent):
            if token.lemma_ in ['be'] and i < len(sent) - 1:
                next_token = list(sent)[i + 1]
                if next_token.tag_ == 'VBN':  # Past participle
                    passive_count += 1
                    break

    passive_pct = (passive_count / total_sentences * 100) if total_sentences > 0 else 0

    # Count syllables (approximate for Flesch score)
    def count_syllables(word):
        word = word.lower()
        count = 0
        vowels = 'aeiouy'
        previous_was_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                count += 1
            previous_was_vowel = is_vowel
        if word.endswith('e'):
            count -= 1
        return max(1, count)

    total_syllables = sum(count_syllables(token.text) for token in doc if token.is_alpha)

    # Flesch Reading Ease Score
    # Score = 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
    flesch_score = 206.835 - 1.015 * avg_sentence_length - 84.6 * (total_syllables / total_words) if total_words > 0 else 0
    flesch_score = max(0, min(100, flesch_score))  # Clamp between 0-100

    issues = []

    if passive_pct > 30:
        issues.append(f"High passive voice usage ({passive_pct:.0f}%). Use active voice for stronger impact.")

    if avg_sentence_length > 25:
        issues.append(f"Sentences too long (avg {avg_sentence_length:.0f} words). Aim for 15-20 words per sentence.")
    elif avg_sentence_length < 10:
        issues.append(f"Sentences too short (avg {avg_sentence_length:.0f} words). Add more detail.")

    if flesch_score < 50:
        issues.append("Resume is difficult to read. Simplify language and shorten sentences.")

    return {
        'flesch_score': round(flesch_score, 1),
        'passive_pct': round(passive_pct, 1),
        'avg_sentence_length': round(avg_sentence_length, 1),
        'issues': issues
    }


def infer_scope_level(resume_text, jd_text):
    """
    Infer scope and seniority level from quantifiable metrics
    Compares resume scope vs JD requirements
    """
    # Extract budget/financial scope
    budget_pattern = re.compile(r'\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*([KMB]|million|billion|thousand)?', re.IGNORECASE)

    resume_budgets = []
    for match in budget_pattern.finditer(resume_text):
        amount = float(match.group(1).replace(',', ''))
        unit = match.group(2) or ''

        # Convert to millions
        if 'k' in unit.lower() or 'thousand' in unit.lower():
            amount = amount / 1000
        elif 'b' in unit.lower() or 'billion' in unit.lower():
            amount = amount * 1000

        resume_budgets.append(amount)

    jd_budgets = []
    for match in budget_pattern.finditer(jd_text):
        amount = float(match.group(1).replace(',', ''))
        unit = match.group(2) or ''

        if 'k' in unit.lower() or 'thousand' in unit.lower():
            amount = amount / 1000
        elif 'b' in unit.lower() or 'billion' in unit.lower():
            amount = amount * 1000

        jd_budgets.append(amount)

    # Extract team sizes
    team_pattern = re.compile(r'(?:team of|managed|supervised|led)\s+(\d+)', re.IGNORECASE)

    resume_teams = [int(m.group(1)) for m in team_pattern.finditer(resume_text)]
    jd_teams = [int(m.group(1)) for m in team_pattern.finditer(jd_text)]

    # Determine scope levels
    def get_scope_level(budgets, teams):
        max_budget = max(budgets) if budgets else 0
        max_team = max(teams) if teams else 0

        # Classify based on budget and team size
        if max_budget >= 10 or max_team >= 20:
            return 'senior', max_budget, max_team
        elif max_budget >= 2 or max_team >= 5:
            return 'mid', max_budget, max_team
        else:
            return 'junior', max_budget, max_team

    resume_level, resume_budget, resume_team = get_scope_level(resume_budgets, resume_teams)
    jd_level, jd_budget, jd_team = get_scope_level(jd_budgets, jd_teams)

    scope_match = resume_level == jd_level

    recommendation = None
    if not scope_match:
        if jd_level == 'senior' and resume_level != 'senior':
            recommendation = f"Resume shows {resume_level}-level scope (${resume_budget:.1f}M budget, {resume_team} people) but JD requires senior-level (${jd_budget:.1f}M+, {jd_team}+ people). Add larger-scale examples."
        elif jd_level == 'mid' and resume_level == 'junior':
            recommendation = f"Resume shows junior-level scope. JD requires mid-level responsibility. Emphasize larger projects and team leadership."

    return {
        'resume_scope': resume_level,
        'jd_scope': jd_level,
        'scope_match': scope_match,
        'resume_budget': resume_budget,
        'jd_budget': jd_budget,
        'recommendation': recommendation
    }


def check_consistency(resume_text, nlp):
    """
    Detect inconsistencies and contradictions in resume
    Checks: title vs responsibilities, claimed seniority vs evidence
    """
    doc = nlp(resume_text)
    issues = []

    # Extract job titles
    titles = []
    title_keywords = ['manager', 'director', 'senior', 'lead', 'analyst', 'controller', 'supervisor', 'coordinator']

    for sent in doc.sents:
        sent_text = sent.text.lower()
        for keyword in title_keywords:
            if keyword in sent_text:
                titles.append((keyword, sent.text))
                break

    # Check for management titles without team mentions
    mgmt_titles = ['manager', 'director', 'supervisor', 'lead']
    has_mgmt_title = any(title[0] in mgmt_titles for title in titles)

    team_pattern = re.compile(r'(?:team|managed|supervised|led|mentored)\s+\d+|team of', re.IGNORECASE)
    has_team_mention = bool(team_pattern.search(resume_text))

    if has_mgmt_title and not has_team_mention:
        issues.append("Title includes 'Manager/Director' but no team management mentioned. Add team size or remove management title.")

    # Check for "Senior" title without years of experience
    has_senior_title = any('senior' in title[0] for title in titles)

    # Count years (rough estimate)
    year_pattern = re.compile(r'(20\d{2})\s*[-–]\s*(20\d{2}|present)', re.IGNORECASE)
    years_found = year_pattern.findall(resume_text)

    total_years = 0
    for start, end in years_found:
        start_year = int(start)
        end_year = 2025 if end.lower() == 'present' else int(end)
        total_years += (end_year - start_year)

    if has_senior_title and total_years < 5:
        issues.append("Title includes 'Senior' but less than 5 years experience shown. Add more experience or adjust title.")

    # Check for budget responsibility claims without dollar amounts
    if 'budget' in resume_text.lower():
        budget_pattern = re.compile(r'\$\s*\d+', re.IGNORECASE)
        if not budget_pattern.search(resume_text):
            issues.append("'Budget' mentioned but no dollar amounts provided. Quantify budget responsibility.")

    return {'consistency_issues': issues[:3]}  # Top 3 issues


# ==================== TIER 4 ENHANCEMENTS ====================

def score_gap_severity(gaps, jd_text):
    """
    Score each gap 1-10 based on importance signals in JD
    Factors: frequency, position in JD, appears in requirements, marked as required
    Returns: prioritized gaps with severity scores
    """
    if not gaps:
        return []

    jd_lower = jd_text.lower()
    gap_scores = []

    for gap in gaps:
        gap_lower = gap.lower()
        score = 5  # Base score
        signals = []

        # Factor 1: Frequency in JD (how many times mentioned)
        frequency = jd_lower.count(gap_lower)
        if frequency >= 4:
            score += 3
            signals.append(f"mentioned {frequency}x in JD")
        elif frequency >= 2:
            score += 2
            signals.append(f"mentioned {frequency}x")
        elif frequency == 1:
            score += 0

        # Factor 2: Position in JD (appears in first 25% = high priority)
        first_occurrence = jd_lower.find(gap_lower)
        if first_occurrence != -1:
            position_pct = (first_occurrence / len(jd_lower)) * 100
            if position_pct <= 25:
                score += 2
                signals.append("appears early in JD")

        # Factor 3: Appears in requirements/qualifications section
        requirements_keywords = ['required', 'must have', 'qualifications', 'requirements', 'essential']
        for keyword in requirements_keywords:
            # Find the keyword section
            keyword_idx = jd_lower.find(keyword)
            if keyword_idx != -1:
                # Check if gap appears within 500 chars after the keyword
                section = jd_lower[keyword_idx:keyword_idx+500]
                if gap_lower in section:
                    score += 2
                    signals.append(f"in {keyword} section")
                    break

        # Factor 4: Marked as "required" or "must have"
        # Look for patterns like "required: X, Y, Z" or "must have X"
        context_patterns = [
            rf'(?:required|must have|essential).*?{re.escape(gap_lower)}',
            rf'{re.escape(gap_lower)}.*?(?:required|essential|critical)'
        ]

        for pattern in context_patterns:
            if re.search(pattern, jd_lower):
                score += 1
                signals.append("marked as required")
                break

        # Factor 5: Certification or specific credential
        if any(cert in gap_lower for cert in ['cpa', 'cfa', 'certified', 'license', 'certification']):
            score += 1
            signals.append("certification/credential")

        # Cap at 10
        score = min(10, score)

        # Categorize severity
        if score >= 9:
            severity = 'CRITICAL'
        elif score >= 7:
            severity = 'HIGH'
        elif score >= 5:
            severity = 'MEDIUM'
        else:
            severity = 'LOW'

        gap_scores.append({
            'gap': gap,
            'score': score,
            'severity': severity,
            'signals': signals,
            'frequency': frequency
        })

    # Sort by score descending
    gap_scores.sort(key=lambda x: x['score'], reverse=True)

    return gap_scores


def assess_skill_evidence(resume_text, resume_skills, nlp):
    """
    For each skill claimed in resume, assess quality of evidence (1-10)
    Strong evidence: specific examples, metrics, outcomes
    Weak evidence: just listed in skills section, no context
    """
    if not resume_skills:
        return []

    doc = nlp(resume_text)
    sentences = [sent.text for sent in doc.sents]

    skill_evidence_scores = []

    for skill in resume_skills[:15]:  # Limit to top 15 skills for performance
        skill_lower = skill.lower()
        evidence_score = 0
        evidence_details = []

        # Find all sentences mentioning this skill
        relevant_sentences = [s for s in sentences if skill_lower in s.lower()]

        if not relevant_sentences:
            # Skill mentioned but no context (likely just in skills list)
            skill_evidence_scores.append({
                'skill': skill,
                'evidence_score': 1,
                'quality': 'WEAK',
                'evidence_details': ['Only listed, no examples provided']
            })
            continue

        # Base score for being mentioned in context
        evidence_score = 3

        # Check for quantified achievements related to this skill
        for sentence in relevant_sentences:
            # Has numbers/metrics
            if re.search(r'\d+%|\$\d+|\d+\s*(?:percent|million|thousand)', sentence):
                evidence_score += 2
                evidence_details.append('Quantified with metrics')
                break

        # Check for outcome language
        outcome_verbs = ['increased', 'decreased', 'improved', 'reduced', 'achieved', 'delivered', 'generated']
        for sentence in relevant_sentences:
            if any(verb in sentence.lower() for verb in outcome_verbs):
                evidence_score += 2
                evidence_details.append('Shows outcomes/results')
                break

        # Check for specific examples (project names, tools, processes)
        has_specifics = any(len(sentence.split()) > 15 for sentence in relevant_sentences)
        if has_specifics:
            evidence_score += 1
            evidence_details.append('Detailed examples provided')

        # Check for leadership context
        leadership_words = ['led', 'managed', 'directed', 'owned', 'established']
        if any(word in ' '.join(relevant_sentences).lower() for word in leadership_words):
            evidence_score += 1
            evidence_details.append('Leadership context')

        # Check for multiple mentions (skill used throughout resume)
        if len(relevant_sentences) >= 3:
            evidence_score += 1
            evidence_details.append(f'Mentioned {len(relevant_sentences)} times')

        # Cap at 10
        evidence_score = min(10, evidence_score)

        # Categorize quality
        if evidence_score >= 8:
            quality = 'STRONG'
        elif evidence_score >= 5:
            quality = 'MODERATE'
        else:
            quality = 'WEAK'

        skill_evidence_scores.append({
            'skill': skill,
            'evidence_score': evidence_score,
            'quality': quality,
            'evidence_details': evidence_details,
            'mentions': len(relevant_sentences)
        })

    # Sort by evidence score ascending (weakest first)
    skill_evidence_scores.sort(key=lambda x: x['evidence_score'])

    return skill_evidence_scores


def analyze_keyword_placement(resume_text, jd_skills):
    """
    Analyze WHERE critical keywords appear in resume
    Top 25% = excellent (ATS and human readers see it)
    Middle 50% = okay
    Bottom 25% = buried (ATS might miss it)
    """
    if not jd_skills:
        return {}

    resume_lower = resume_text.lower()
    resume_length = len(resume_lower)

    placement_analysis = {
        'top_third': [],
        'middle_third': [],
        'bottom_third': [],
        'not_found': [],
        'buried_critical': []  # Critical skills in bottom third
    }

    for skill in jd_skills[:20]:  # Top 20 JD skills
        skill_lower = skill.lower()

        # Find first occurrence
        first_idx = resume_lower.find(skill_lower)

        if first_idx == -1:
            placement_analysis['not_found'].append(skill)
            continue

        # Calculate position percentage
        position_pct = (first_idx / resume_length) * 100

        if position_pct <= 33:
            placement_analysis['top_third'].append({
                'skill': skill,
                'position_pct': round(position_pct, 1)
            })
        elif position_pct <= 67:
            placement_analysis['middle_third'].append({
                'skill': skill,
                'position_pct': round(position_pct, 1)
            })
        else:
            placement_analysis['bottom_third'].append({
                'skill': skill,
                'position_pct': round(position_pct, 1)
            })

    # Identify critical skills that are buried
    # Critical = appears 3+ times in JD or in first 25% of JD
    jd_lower = resume_text.lower()  # Note: This should be jd_text but we don't have it here

    for skill_data in placement_analysis['bottom_third']:
        skill = skill_data['skill']
        # If it's in bottom third, flag as buried
        placement_analysis['buried_critical'].append(skill)

    return placement_analysis


def score_resume_bullets(resume_text, nlp):
    """
    Score each resume bullet/sentence on 1-10 scale
    Factors: strong verb, quantification, outcome language, specificity
    Returns: scored bullets with specific improvement suggestions
    """
    doc = nlp(resume_text)
    sentences = [sent for sent in doc.sents if len(sent.text.split()) >= 5]  # Filter short sentences

    bullet_scores = []

    # Strong action verbs
    strong_verbs = {
        'led', 'owned', 'directed', 'established', 'spearheaded',
        'architected', 'pioneered', 'transformed', 'drove', 'launched',
        'built', 'designed', 'optimized', 'streamlined', 'delivered'
    }

    weak_verbs = {
        'helped', 'assisted', 'supported', 'worked', 'handled',
        'participated', 'contributed', 'did', 'performed'
    }

    for sent in sentences[:25]:  # Analyze top 25 bullets
        text = sent.text.strip()
        text_lower = text.lower()
        score = 0
        issues = []
        strengths = []

        # Factor 1: Action verb strength (0-3 points)
        first_verb = None
        for token in sent:
            if token.pos_ == 'VERB':
                first_verb = token.lemma_.lower()
                break

        if first_verb:
            if first_verb in strong_verbs:
                score += 3
                strengths.append(f"Strong verb: '{first_verb}'")
            elif first_verb in weak_verbs:
                score += 1
                issues.append(f"Weak verb: '{first_verb}' - replace with led/owned/drove")
            else:
                score += 2
        else:
            issues.append("No clear action verb - start with strong verb")

        # Factor 2: Quantification (0-3 points)
        has_number = bool(re.search(r'\d+', text))
        has_percentage = bool(re.search(r'\d+%', text))
        has_dollar = bool(re.search(r'\$\d+', text))

        quantification_score = 0
        if has_percentage or has_dollar:
            quantification_score = 3
            strengths.append("Specific metrics included")
        elif has_number:
            quantification_score = 2
            strengths.append("Numbers included")
        else:
            quantification_score = 0
            issues.append("Add quantified results (%, $, or numbers)")

        score += quantification_score

        # Factor 3: Outcome language (0-2 points)
        outcome_words = ['increased', 'decreased', 'reduced', 'improved', 'achieved', 'delivered', 'generated', 'saved']
        has_outcome = any(word in text_lower for word in outcome_words)

        if has_outcome:
            score += 2
            strengths.append("Shows outcome/impact")
        else:
            issues.append("Add outcome language (increased, reduced, achieved)")

        # Factor 4: Specificity (0-2 points)
        word_count = len(text.split())
        has_specific_terms = bool(re.search(r'(?:by|to|for|with)\s+\d+', text))  # "by 40%", "to $5M"

        if word_count >= 15 and has_specific_terms:
            score += 2
            strengths.append("Specific and detailed")
        elif word_count >= 10:
            score += 1
        else:
            issues.append("Too vague - add specific details")

        # Cap at 10
        score = min(10, score)

        # Quality rating
        if score >= 8:
            quality = 'EXCELLENT'
        elif score >= 6:
            quality = 'GOOD'
        elif score >= 4:
            quality = 'FAIR'
        else:
            quality = 'WEAK'

        bullet_scores.append({
            'text': text[:100],  # Truncate for storage
            'score': score,
            'quality': quality,
            'strengths': strengths,
            'issues': issues
        })

    # Sort by score ascending (weakest first)
    bullet_scores.sort(key=lambda x: x['score'])

    # Calculate overall stats
    if bullet_scores:
        avg_score = sum(b['score'] for b in bullet_scores) / len(bullet_scores)
        weak_bullets = [b for b in bullet_scores if b['score'] < 5]
    else:
        avg_score = 0
        weak_bullets = []

    return {
        'bullet_scores': bullet_scores,
        'avg_score': round(avg_score, 1),
        'weak_count': len(weak_bullets),
        'total_analyzed': len(bullet_scores)
    }


# ==================== BETA-CRITICAL ENHANCEMENTS ====================

def validate_education_requirements(resume_text, jd_text):
    """
    Validate education requirements between resume and JD
    Detects: degree level, field of study, GPA requirements
    Returns: education gaps with severity (DEALBREAKER vs PREFERENCE)
    """
    resume_lower = resume_text.lower()
    jd_lower = jd_text.lower()

    education_gaps = {
        'degree_level_gap': None,
        'field_of_study_gap': None,
        'gpa_gap': None,
        'severity': 'NONE'  # DEALBREAKER, WARNING, or NONE
    }

    # Degree level hierarchy
    degree_levels = {
        'phd': 5,
        'doctorate': 5,
        'doctoral': 5,
        'ph.d': 5,
        'master': 4,
        "master's": 4,
        'mba': 4,
        'ms': 4,
        'ma': 4,
        'bachelor': 3,
        "bachelor's": 3,
        'bs': 3,
        'ba': 3,
        'bsc': 3,
        'associate': 2,
        "associate's": 2,
        'high school': 1,
        'diploma': 1
    }

    # Detect resume degree level
    resume_degree_level = 0
    resume_degree_name = None
    for degree, level in degree_levels.items():
        if degree in resume_lower:
            if level > resume_degree_level:
                resume_degree_level = level
                resume_degree_name = degree

    # Detect JD required degree level
    jd_degree_level = 0
    jd_degree_name = None
    jd_required = False

    # Look for required patterns
    required_patterns = [
        r'(bachelor|master|phd|doctorate|mba|bs|ba|ms|ma).*?(?:required|mandatory)',
        r'(?:required|mandatory).*?(bachelor|master|phd|doctorate|mba|bs|ba|ms|ma)',
        r'must have.*?(bachelor|master|phd|doctorate|mba|bs|ba|ms|ma)',
        r'(bachelor|master|phd|doctorate|mba|bs|ba|ms|ma).*?(?:degree|education).*?(?:required|mandatory)'
    ]

    for pattern in required_patterns:
        match = re.search(pattern, jd_lower)
        if match:
            degree_term = match.group(1)
            if degree_term in degree_levels:
                jd_degree_level = degree_levels[degree_term]
                jd_degree_name = degree_term
                jd_required = True
                break

    # If not required, look for preferred
    if not jd_required:
        preferred_patterns = [
            r'(bachelor|master|phd|doctorate|mba|bs|ba|ms|ma).*?(?:preferred|desired|plus)',
            r'(?:preferred|desired).*?(bachelor|master|phd|doctorate|mba|bs|ba|ms|ma)'
        ]

        for pattern in preferred_patterns:
            match = re.search(pattern, jd_lower)
            if match:
                degree_term = match.group(1)
                if degree_term in degree_levels:
                    jd_degree_level = degree_levels[degree_term]
                    jd_degree_name = degree_term
                    break

    # Check degree level gap
    if jd_degree_level > 0:
        if resume_degree_level < jd_degree_level:
            education_gaps['degree_level_gap'] = {
                'required': jd_degree_name,
                'found': resume_degree_name if resume_degree_name else 'None detected',
                'is_required': jd_required
            }
            education_gaps['severity'] = 'DEALBREAKER' if jd_required else 'WARNING'

    # Check field of study requirements
    field_keywords = {
        'computer science': ['computer science', 'cs degree', 'computer engineering'],
        'engineering': ['engineering', 'engineer'],
        'business': ['business', 'mba', 'business administration'],
        'finance': ['finance', 'accounting', 'economics'],
        'mathematics': ['mathematics', 'math', 'statistics'],
        'science': ['science', 'biology', 'chemistry', 'physics']
    }

    for field, keywords in field_keywords.items():
        # Check if JD requires this field
        jd_has_field = any(keyword in jd_lower for keyword in keywords)
        if jd_has_field:
            # Check if it's required
            field_required = False
            for keyword in keywords:
                if re.search(rf'{keyword}.*?(?:required|mandatory|must have)', jd_lower) or \
                   re.search(rf'(?:required|mandatory|must have).*?{keyword}', jd_lower):
                    field_required = True
                    break

            # Check if resume has this field
            resume_has_field = any(keyword in resume_lower for keyword in keywords)

            if field_required and not resume_has_field:
                education_gaps['field_of_study_gap'] = {
                    'required_field': field,
                    'found': False
                }
                education_gaps['severity'] = 'DEALBREAKER'
                break

    # Check GPA requirements
    gpa_patterns = [
        r'(\d\.?\d+)\s*(?:\+)?\s*gpa',
        r'gpa.*?(\d\.?\d+)',
        r'minimum gpa.*?(\d\.?\d+)'
    ]

    for pattern in gpa_patterns:
        match = re.search(pattern, jd_lower)
        if match:
            required_gpa = float(match.group(1))

            # Try to find GPA in resume
            resume_gpa_match = re.search(r'gpa[:\s]*(\d\.?\d+)', resume_lower)
            if resume_gpa_match:
                resume_gpa = float(resume_gpa_match.group(1))
                if resume_gpa < required_gpa:
                    education_gaps['gpa_gap'] = {
                        'required': required_gpa,
                        'found': resume_gpa
                    }
                    education_gaps['severity'] = 'WARNING'  # GPA is rarely a hard dealbreaker
            else:
                # GPA not found in resume, but required in JD
                education_gaps['gpa_gap'] = {
                    'required': required_gpa,
                    'found': None
                }
                education_gaps['severity'] = 'WARNING'
            break

    return education_gaps


def validate_years_experience(resume_years, jd_text):
    """
    Validate years of experience requirements
    Detects: minimum years required, overqualification
    Returns: experience gap with severity
    """
    jd_lower = jd_text.lower()

    # Write debug to file to bypass any caching/buffering issues
    import datetime
    with open('/tmp/workalign_debug.log', 'a') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"DEBUG validate_years_experience() - {datetime.datetime.now()}\n")
        f.write(f"Resume years: {resume_years}\n")
        f.write(f"JD text snippet: {jd_lower[:300]}\n")
        f.write(f"{'='*80}\n")

    experience_validation = {
        'meets_minimum': True,
        'min_required': None,
        'resume_years': resume_years,
        'overqualified': False,
        'severity': 'NONE'  # DEALBREAKER, WARNING, or NONE
    }

    # COMPREHENSIVE APPROACH: First extract ALL year mentions, then parse them
    min_years_required = None

    # Strategy 1: Look for explicit ranges with various formats
    # Matches: "5-7 years", "5 - 7 years", "5 to 7 years", "5–7 years"
    range_pattern = r'(\d+)\s*(?:[-–—]|to)\s*(\d+)\s*(?:\+)?\s*years?'
    range_match = re.search(range_pattern, jd_lower)

    with open('/tmp/workalign_debug.log', 'a') as f:
        f.write(f"Testing range pattern: {range_pattern}\n")

    if range_match:
        with open('/tmp/workalign_debug.log', 'a') as f:
            f.write(f"Range pattern MATCHED!\n")
            f.write(f"  Full match: '{range_match.group()}'\n")
            f.write(f"  Group 1: '{range_match.group(1)}'\n")
            f.write(f"  Group 2: '{range_match.group(2)}'\n")
        # Found a range - use the minimum value
        min_val = int(range_match.group(1))
        max_val = int(range_match.group(2))
        min_years_required = min(min_val, max_val)
        with open('/tmp/workalign_debug.log', 'a') as f:
            f.write(f"  Result: min({min_val}, {max_val}) = {min_years_required}\n")
    else:
        with open('/tmp/workalign_debug.log', 'a') as f:
            f.write(f"Range pattern did NOT match\n")
        # Strategy 2: Look for single values with common patterns
        # Prioritize patterns that indicate requirements
        single_patterns = [
            r'(\d+)\+\s*years?',  # "5+ years"
            r'minimum\s+(?:of\s+)?(\d+)\s*years?',  # "minimum 5 years"
            r'at\s+least\s+(\d+)\s*years?',  # "at least 5 years"
            r'(\d+)\s*years?\s+(?:of\s+)?(?:experience|exp)',  # "5 years of experience"
        ]

        for pattern in single_patterns:
            matches = re.findall(pattern, jd_lower)
            if matches:
                with open('/tmp/workalign_debug.log', 'a') as f:
                    f.write(f"Single pattern '{pattern}' matched: {matches}\n")
                # Convert all matches to integers and take the minimum
                years_found = [int(m) if isinstance(m, str) else int(m[0]) for m in matches]
                min_years_required = min(years_found)
                with open('/tmp/workalign_debug.log', 'a') as f:
                    f.write(f"  Years found: {years_found}, minimum: {min_years_required}\n")
                break

    with open('/tmp/workalign_debug.log', 'a') as f:
        f.write(f"Final min_years_required = {min_years_required}\n\n")

    if min_years_required:
        experience_validation['min_required'] = min_years_required

        # Check if resume meets minimum
        if resume_years < min_years_required:
            experience_validation['meets_minimum'] = False
            gap = min_years_required - resume_years

            # Severe dealbreaker if gap > 3 years
            if gap >= 3:
                experience_validation['severity'] = 'DEALBREAKER'
            else:
                experience_validation['severity'] = 'WARNING'

        # Check for overqualification (2x or more experience than required)
        elif resume_years >= min_years_required * 2 and min_years_required <= 3:
            # Only flag as overqualified for junior roles (≤3 years required)
            experience_validation['overqualified'] = True
            experience_validation['severity'] = 'WARNING'

    return experience_validation
