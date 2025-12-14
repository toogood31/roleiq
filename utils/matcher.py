from sentence_transformers import SentenceTransformer, util
from utils.extractor import load_seniority_levels, load_ontology, extract_skills, extract_seniority, detect_industry, nlp
from utils.parser import parse_document, clean_text, extract_sections
from utils.llm_validator import validate_gaps_with_llm
from utils.ontology_utils import (
    normalize_job_title,
    detect_certifications,
    find_certification_gaps,
    match_job_titles,
    enhance_skill_matching
)
from utils.analyzers import (
    extract_achievements,
    analyze_action_verbs,
    cluster_skills,
    calculate_ats_keyword_density,
    detect_leadership_language,
    classify_task_vs_outcome,
    score_resume_sections,
    detect_skill_redundancies,
    classify_hard_vs_soft_skills,
    extract_skill_context,
    analyze_experience_progression,
    analyze_skill_cooccurrence,
    calculate_readability_score,
    infer_scope_level,
    check_consistency,
    # Tier 4 enhancements
    score_gap_severity,
    assess_skill_evidence,
    analyze_keyword_placement,
    score_resume_bullets,
    # Beta-critical enhancements
    validate_education_requirements,
    validate_years_experience
)
import os
import re

model = SentenceTransformer('stsb-roberta-large')

def get_embeddings(texts):
    return model.encode(texts, convert_to_tensor=True)

def compute_score(resume_embs, jd_embs, weights=[0.4, 0.3, 0.2, 0.1]):
    scores = [util.cos_sim(resume_embs[i], jd_embs[i])[0][0].item() for i in range(len(weights))]
    total_score = sum(s * w for s, w in zip(scores, weights)) * 100
    return total_score

def analyze_seniority(resume_seniority, jd_seniority):
    points = []
    points.append(f"Experience years: Resume {resume_seniority['years']} vs JD ~{jd_seniority['years']} - {'Similar: Good tenure alignment' if resume_seniority['years'] >= jd_seniority['years'] * 0.8 else 'Different: Gap in years - action: Add more details to bridge'}.")
    points.append(f"Seniority level: Resume average {resume_seniority['level']:.1f} vs JD's {jd_seniority['level']:.1f} - {'Similar: Comparable leadership' if resume_seniority['level'] >= jd_seniority['level'] else 'Different: Lower level - action: Highlight promotions'}.")
    points.append(f"Overall seniority: {'Strong fit' if resume_seniority['level'] >= jd_seniority['level'] else 'Partial fit - action: Build with leadership examples'} - simple explanation: Resume and JD {'align in career stage' if resume_seniority['level'] >= jd_seniority['level'] else 'differ in responsibility; JD more senior'}.")
    return points

def analyze_competencies(resume_skills, jd_skills, model):
    # First pass: exact matches
    matches = set(resume_skills) & set(jd_skills)

    # Second pass: substring/partial matches (e.g., "bank reconciliation" matches "reconciliation")
    # Check if a resume skill contains a JD skill or vice versa
    remaining_resume = set(resume_skills) - matches
    remaining_jd = set(jd_skills) - matches

    partial_matches = set()
    for r_skill in remaining_resume:
        for j_skill in remaining_jd:
            # Check if one skill is contained in the other (with word boundaries)
            r_words = set(r_skill.split())
            j_words = set(j_skill.split())
            # If JD skill is a subset of resume skill words, it's a match
            # e.g., "reconciliation" matches "bank reconciliation"
            if j_words.issubset(r_words) or r_words.issubset(j_words):
                partial_matches.add(r_skill)
                matches.add(j_skill)  # Add JD skill to matches
                break

    # Update gaps after partial matching
    gaps = set(jd_skills) - matches

    # Ontology enhancement: Check if any "skills" are actually job title variations
    ontology_matches, _ = enhance_skill_matching(list(remaining_resume - partial_matches), list(gaps))
    for ontology_match in ontology_matches:
        matches.add(ontology_match)
        if ontology_match in gaps:
            gaps.remove(ontology_match)

    # Third pass: semantic similarity for remaining gaps
    remaining_resume = remaining_resume - partial_matches
    similar = [s for s in remaining_resume if any(util.cos_sim(model.encode(s), model.encode(g))[0][0].item() > 0.55 for g in gaps)]  # Lowered from 0.7 to 0.55
    points = []
    points.append(f"Direct matches: {len(matches)} skills overlap (e.g., {', '.join(list(matches)[:2]) if matches else 'none'}) - {'Similar: Strong core alignment' if matches else 'Different: No overlap - action: Add JD skills'}.")
    points.append(f"Gaps: {len(gaps)} skills missing (e.g., {', '.join(list(gaps)[:2]) if gaps else 'none'}) - {'Different: Add to resume' if gaps else 'Similar: No gaps'} - action: Include examples for gaps.")
    points.append(f"Similar skills: {len(similar)} close to gaps (e.g., {', '.join(similar[:2]) if similar else 'none'}) - {'Similar: Partial fit' if similar else 'Different: No close matches'} - action: Rephrase to align.")
    return {'points': points, 'matches': list(matches), 'gaps': list(gaps), 'similar': similar, 'analysis': '\n'.join(points)}

def extract_bullets(text):
    """
    Extract bullet points and sentences from text for sentence-level comparison.
    Returns a list of meaningful sentences/bullets.
    """
    bullets = []

    # Split by common bullet indicators
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        # Remove bullet characters
        line = re.sub(r'^[•\-\*\+►▪→●○]\s*', '', line)
        line = re.sub(r'^\d+\.\s*', '', line)  # Remove numbered lists

        # Skip very short lines (likely headers or noise)
        if len(line.split()) < 4:
            continue

        # Skip lines that look like section headers
        if line.isupper() or line.endswith(':'):
            continue

        bullets.append(line.lower())

    # If we didn't extract many bullets, fall back to sentence splitting
    if len(bullets) < 3:
        doc = nlp(text)
        bullets = [sent.text.lower().strip() for sent in doc.sents if len(sent.text.split()) >= 4]

    return bullets

def sentence_level_matching(resume_text, jd_text, identified_gaps, model):
    """
    Perform sentence-level comparison between resume and JD as a fallback.
    This helps catch skills that were missed by keyword extraction.

    Returns a list of gaps that appear to be false positives (actually present in resume).
    """
    resume_bullets = extract_bullets(resume_text)
    jd_bullets = extract_bullets(jd_text)

    if not resume_bullets or not jd_bullets:
        return []  # Can't perform comparison

    # Encode all bullets
    resume_embs = model.encode(resume_bullets)
    jd_embs = model.encode(jd_bullets)

    # For each identified gap, check if it appears in any JD bullet
    # and if that JD bullet has high similarity to any resume bullet
    false_positive_gaps = []

    for gap in identified_gaps:
        gap_lower = gap.lower()

        # Find JD bullets that mention this gap
        relevant_jd_bullets = []
        for i, jd_bullet in enumerate(jd_bullets):
            if gap_lower in jd_bullet:
                relevant_jd_bullets.append((i, jd_bullet))

        # For each relevant JD bullet, check if there's a similar resume bullet
        for jd_idx, jd_bullet in relevant_jd_bullets:
            jd_emb = jd_embs[jd_idx]

            # Compute similarity with all resume bullets
            similarities = util.cos_sim(jd_emb, resume_embs)[0]
            max_sim = max(similarities).item()

            # If there's high similarity (>0.65), this gap might be a false positive
            if max_sim > 0.65:
                # Find the matching resume bullet
                best_match_idx = similarities.argmax().item()
                matching_resume_bullet = resume_bullets[best_match_idx]

                # Verify the resume bullet actually relates to the skill
                # by checking if it contains related terms
                gap_words = set(gap_lower.split())
                resume_words = set(matching_resume_bullet.split())

                # If there's word overlap or high semantic similarity, mark as false positive
                if len(gap_words & resume_words) > 0 or max_sim > 0.75:
                    false_positive_gaps.append(gap)
                    break

    return false_positive_gaps

def analyze_business_context(resume_text, jd_text, model):
    doc_resume = nlp(resume_text)
    doc_jd = nlp(jd_text)
    resume_context = [ent.text.lower() for ent in doc_resume.ents if ent.label_ in ["ORG", "NORP", "GPE", "PRODUCT"]]
    jd_context = [ent.text.lower() for ent in doc_jd.ents if ent.label_ in ["ORG", "NORP", "GPE", "PRODUCT"]]
    matches = set(resume_context) & set(jd_context)
    resume_emb = model.encode(resume_text)
    jd_emb = model.encode(jd_text)
    context_sim = util.cos_sim(resume_emb, jd_emb)[0][0].item() * 100
    points = []
    points.append(f"Context similarity: {context_sim:.2f}% - {'Similar: Good industry match' if context_sim > 70 else 'Different: Partial alignment - action: Adjust resume'}.")
    points.append(f"Shared entities: {len(matches)} common (e.g., {', '.join(list(matches)[:2]) if matches else 'none'}) - {'Similar: Common background' if matches else 'Different: No shared - action: Add relevant details'}.")
    points.append(f"Overall context fit: {'Strong' if context_sim > 70 else 'Partial'} - action: Tailor to JD's environment.")
    return points  # 3 bullets

def match_resume_jd(resume_file, jd_file_or_text, ontology_path, seniority_path):
    """
    Match resume against job description with comprehensive error handling

    Returns: analysis dict or error dict with {'error': message, 'error_type': type}
    """
    try:
        # Parse resume with validation
        try:
            resume_text = parse_document(resume_file)
        except Exception as e:
            return {
                'error': f'Failed to parse resume: {str(e)}',
                'error_type': 'PARSE_ERROR',
                'details': 'Resume file may be corrupted, password-protected, or in an unsupported format.'
            }

        # Parse JD with validation
        try:
            if os.path.isfile(jd_file_or_text): # If JD is a file path
                jd_text = parse_document(jd_file_or_text)
            else: # If JD is text
                jd_text = clean_text(jd_file_or_text)
        except Exception as e:
            return {
                'error': f'Failed to parse job description: {str(e)}',
                'error_type': 'PARSE_ERROR',
                'details': 'Job description file may be corrupted or in an unsupported format.'
            }

        # Validate minimum content length
        if len(resume_text.strip()) < 50:
            return {
                'error': 'Resume is too short or empty',
                'error_type': 'VALIDATION_ERROR',
                'details': f'Resume contains only {len(resume_text.strip())} characters. Minimum 50 required.'
            }

        if len(jd_text.strip()) < 50:
            return {
                'error': 'Job description is too short or empty',
                'error_type': 'VALIDATION_ERROR',
                'details': f'Job description contains only {len(jd_text.strip())} characters. Minimum 50 required.'
            }

        # Warn for very long documents (but continue processing)
        if len(resume_text) > 50000:
            print(f"WARNING: Very long resume ({len(resume_text)} chars). Processing may be slow.")

        if len(jd_text) > 50000:
            print(f"WARNING: Very long job description ({len(jd_text)} chars). Processing may be slow.")

    except Exception as e:
        return {
            'error': f'Unexpected validation error: {str(e)}',
            'error_type': 'VALIDATION_ERROR'
        }

    # Main processing with error handling
    try:
        # Detect industries for both resume and JD
        resume_industries = detect_industry(resume_text)
        jd_industries = detect_industry(jd_text)

        resume_sections = extract_sections(resume_text)
        jd_sections = extract_sections(jd_text)
        resume_skills = extract_skills(resume_text, load_ontology(ontology_path))
        jd_skills = extract_skills(jd_text, load_ontology(ontology_path))
        resume_seniority = extract_seniority(resume_sections['experience'], load_seniority_levels(seniority_path))
        jd_seniority = extract_seniority(jd_sections['experience'], load_seniority_levels(seniority_path))
        resume_embs = get_embeddings([' '.join(resume_sections.get(k, [])) for k in ["skills", "experience", "education", "other"]])
        jd_embs = get_embeddings([' '.join(jd_sections.get(k, [])) for k in ["skills", "experience", "education", "other"]])
        score = compute_score(resume_embs, jd_embs)
        seniority_points = analyze_seniority(resume_seniority, jd_seniority)
        comp_analysis = analyze_competencies(resume_skills, jd_skills, model)

        # Apply sentence-level matching to filter out false positive gaps
        initial_gaps = comp_analysis['gaps']
        false_positive_gaps = sentence_level_matching(resume_text, jd_text, initial_gaps, model)

        # Remove false positives from gaps and move them to matches
        filtered_gaps = [g for g in initial_gaps if g not in false_positive_gaps]
        comp_analysis['matches'].extend(false_positive_gaps)  # Add recovered skills to matches

        # Apply LLM validation as final validation layer (if API key available)
        validated_gaps, llm_recovered_matches = validate_gaps_with_llm(
            resume_text,
            jd_text,
            filtered_gaps,
            comp_analysis['matches']
        )

        # Update gaps and matches based on LLM validation
        comp_analysis['gaps'] = validated_gaps
        comp_analysis['matches'].extend(llm_recovered_matches)

        context_points = analyze_business_context(resume_text, jd_text, model)
        role_fit_points = seniority_points + comp_analysis['points'] + context_points # Combine for 4-5+ bullets

        # NEW: Run free enhancement analyzers
        resume_achievements = extract_achievements(resume_text)
        resume_verb_analysis = analyze_action_verbs(resume_text, nlp)
        resume_leadership = detect_leadership_language(resume_text, nlp)
        resume_task_outcome = classify_task_vs_outcome(resume_text, nlp)

        # Cluster skills to improve matching
        resume_skill_clusters = cluster_skills(resume_skills, model)
        jd_skill_clusters = cluster_skills(jd_skills, model)

        # ATS keyword density analysis
        ats_analysis = calculate_ats_keyword_density(resume_text, jd_text, jd_skills)

        # Tier 2 analyzers
        section_scores = score_resume_sections(resume_sections, jd_skills, nlp)
        skill_redundancies = detect_skill_redundancies(resume_skills, model)
        skill_categorization = classify_hard_vs_soft_skills(comp_analysis['gaps'])
        gap_context = extract_skill_context(resume_text, jd_text, comp_analysis['gaps'], model, nlp)

        # Tier 3 analyzers
        experience_progression = analyze_experience_progression(resume_text, nlp)
        skill_cooccurrence = analyze_skill_cooccurrence(resume_skills, jd_skills, comp_analysis['gaps'])
        readability = calculate_readability_score(resume_text, nlp)
        scope_analysis = infer_scope_level(resume_text, jd_text)
        consistency_check = check_consistency(resume_text, nlp)

        # Tier 4 analyzers
        gap_severity = score_gap_severity(comp_analysis['gaps'], jd_text)
        skill_evidence = assess_skill_evidence(resume_text, resume_skills, nlp)
        keyword_placement = analyze_keyword_placement(resume_text, jd_skills)
        bullet_quality = score_resume_bullets(resume_text, nlp)

        # Ontology-based enhancements
        # Determine primary industry for certification detection
        primary_industry = jd_industries[0] if jd_industries else None
        certification_gaps = find_certification_gaps(resume_text, jd_text, primary_industry)

        # Beta-critical validators
        education_validation = validate_education_requirements(resume_text, jd_text)
        experience_validation = validate_years_experience(resume_seniority['years'], jd_text)

        return {
        "score": score,
        "role_fit_points": role_fit_points,
        "comp_details": {
            'matches': comp_analysis['matches'],
            'gaps': comp_analysis['gaps'],
            'similar': comp_analysis['similar']
        },
        "seniority_analysis": ' '.join(seniority_points),
        "comp_analysis": comp_analysis['analysis'],
        "industries": {
            'resume': resume_industries,
            'jd': jd_industries
        },
        # NEW: Enhanced analysis results
        "enhanced_analysis": {
            'achievements': resume_achievements,
            'verb_strength': resume_verb_analysis,
            'leadership_signals': resume_leadership,
            'task_vs_outcome': resume_task_outcome,
            'skill_clusters': {
                'resume': resume_skill_clusters,
                'jd': jd_skill_clusters
            },
            'ats_optimization': ats_analysis,
            # Tier 2 enhancements
            'section_scores': section_scores,
            'skill_redundancies': skill_redundancies,
            'gap_categorization': skill_categorization,
            'gap_context': gap_context,
            # Tier 3 enhancements
            'experience_progression': experience_progression,
            'skill_cooccurrence': skill_cooccurrence,
            'readability': readability,
            'scope_analysis': scope_analysis,
            'consistency_check': consistency_check,
            # Tier 4 enhancements
            'gap_severity': gap_severity,
            'skill_evidence': skill_evidence,
            'keyword_placement': keyword_placement,
            'bullet_quality': bullet_quality,
            # Ontology enhancements
            'certification_gaps': certification_gaps,
            # Beta-critical validators
            'education_validation': education_validation,
            'experience_validation': experience_validation
        }
    }

    except Exception as e:
        # Catch any errors during processing and return gracefully
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR during resume matching: {error_trace}")

        return {
            'error': f'Analysis failed: {str(e)}',
            'error_type': 'PROCESSING_ERROR',
            'details': 'An unexpected error occurred during analysis. Please check your files and try again.'
        }