"""
Semantic Skill Matching using Sentence Transformers (SBERT)
Provides meaning-based skill matching that works across any industry/job
"""
from typing import List, Tuple, Dict, Set
from sentence_transformers import SentenceTransformer, util
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Global model instance (loaded once at startup)
_model = None

def get_model():
    """Lazy load the sentence transformer model (80MB, loads in ~2-3 seconds)"""
    global _model
    if _model is None:
        # all-MiniLM-L6-v2: Fast, accurate, small (80MB)
        # Perfect balance of speed and quality for skill matching
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


# ========== BACKWARDS COMPATIBILITY FUNCTION ==========
# This function maintains compatibility with existing matcher.py code
def semantic_skill_coverage(
    resume_skills: List[str],
    jd_skills: List[str],
    exact_matches: Set[str],
    threshold: float = 0.7
) -> Dict:
    """
    Calculate semantic skill coverage using SBERT (backwards compatible)

    Args:
        resume_skills: List of skills from resume
        jd_skills: List of skills from JD
        exact_matches: Skills already matched exactly
        threshold: Minimum cosine similarity (0-1) to consider a match

    Returns:
        Dict with semantic coverage analysis
    """
    # Use the new SBERT implementation
    remaining_jd = [s for s in jd_skills if s not in exact_matches]

    if not remaining_jd or not resume_skills:
        return {
            'semantic_matches': [],
            'coverage_count': 0,
            'coverage_percentage': 0.0,
            'average_similarity': 0.0
        }

    # Find semantic matches for remaining skills
    semantic_matches = find_semantic_matches(
        resume_skills,
        remaining_jd,
        threshold=threshold,
        already_matched=exact_matches
    )

    coverage_count = len(semantic_matches)
    coverage_pct = (coverage_count / len(remaining_jd) * 100) if remaining_jd else 0
    avg_similarity = np.mean([m['score'] for m in semantic_matches]) if semantic_matches else 0.0

    return {
        'semantic_matches': semantic_matches,
        'coverage_count': coverage_count,
        'coverage_percentage': round(coverage_pct, 1),
        'average_similarity': round(float(avg_similarity), 3)
    }


def find_semantic_matches(
    resume_skills: List[str],
    jd_skills: List[str],
    threshold: float = 0.75,
    already_matched: set = None
) -> List[Dict]:
    """
    Find semantic matches between resume and JD skills using SBERT embeddings

    Args:
        resume_skills: List of skills from resume
        jd_skills: List of skills from JD
        threshold: Minimum cosine similarity (0-1) to consider a match
        already_matched: Set of JD skills already matched (to skip)

    Returns:
        List of match dicts with {resume_skill, jd_skill, score, match_type}
    """
    if not resume_skills or not jd_skills:
        return []

    # Filter out already matched JD skills
    if already_matched:
        jd_skills = [s for s in jd_skills if s not in already_matched]

    if not jd_skills:
        return []

    # Load model
    model = get_model()

    # Encode skills into semantic embeddings
    resume_embeddings = model.encode(resume_skills, convert_to_tensor=False)
    jd_embeddings = model.encode(jd_skills, convert_to_tensor=False)

    # Compute cosine similarity matrix
    # Shape: (len(resume_skills), len(jd_skills))
    similarity_matrix = cosine_similarity(resume_embeddings, jd_embeddings)

    matches = []
    matched_jd_indices = set()

    # For each JD skill, find the best matching resume skill
    for j, jd_skill in enumerate(jd_skills):
        # Get similarity scores for this JD skill across all resume skills
        scores = similarity_matrix[:, j]

        # Find best match
        best_resume_idx = np.argmax(scores)
        best_score = scores[best_resume_idx]

        # Check if it meets threshold
        if best_score >= threshold:
            matches.append({
                'resume_skill': resume_skills[best_resume_idx],
                'jd_skill': jd_skill,
                'score': float(best_score),
                'match_type': 'semantic'
            })
            matched_jd_indices.add(j)

    return matches


def calculate_semantic_score(
    resume_skills: List[str],
    jd_skills: List[str],
    threshold: float = 0.75
) -> Dict:
    """
    Calculate overall semantic match score between resume and JD

    Args:
        resume_skills: List of skills from resume
        jd_skills: List of skills from JD
        threshold: Minimum similarity to consider a match

    Returns:
        Dict with match statistics
    """
    matches = find_semantic_matches(resume_skills, jd_skills, threshold)

    total_jd_skills = len(jd_skills)
    matched_count = len(matches)
    match_percentage = (matched_count / total_jd_skills * 100) if total_jd_skills > 0 else 0

    # Calculate average similarity score
    avg_score = np.mean([m['score'] for m in matches]) if matches else 0.0

    return {
        'matches': matches,
        'matched_count': matched_count,
        'total_jd_skills': total_jd_skills,
        'match_percentage': match_percentage,
        'average_similarity': float(avg_score)
    }


def enhance_skills_with_context(skills: List[str], context: str = "") -> List[str]:
    """
    Optionally add context to skills for better semantic matching

    Args:
        skills: List of skill strings
        context: Optional context (e.g., "Software Engineering:", "Healthcare:")

    Returns:
        Skills with context prepended
    """
    if not context:
        return skills
    return [f"{context} {skill}" for skill in skills]
