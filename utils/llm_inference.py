"""
Local LLM Inference using Ollama
Provides free, universal, contextual skill inference and validation
"""
import requests
import json
from typing import List, Set, Dict

# Ollama API endpoint
OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"


def call_ollama(prompt: str, max_tokens: int = 300) -> str:
    """
    Call local Ollama API for LLM inference

    Args:
        prompt: The prompt to send to the model
        max_tokens: Maximum tokens to generate

    Returns:
        Generated text from the model
    """
    try:
        response = requests.post(
            OLLAMA_API,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.3,  # Lower temperature for more deterministic output
                }
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return result['response'].strip()
        else:
            print(f"Ollama API error: {response.status_code}")
            return ""

    except requests.exceptions.ConnectionError:
        print("WARNING: Ollama is not running. Start it with: brew services start ollama")
        return ""
    except Exception as e:
        print(f"LLM inference error: {e}")
        return ""


def infer_skills_from_job_title(job_title: str) -> Set[str]:
    """
    Use LLM to infer skills from ANY job title (universal, no hardcoded mappings)

    Args:
        job_title: The job title (e.g., "DevOps Engineer", "Product Manager")

    Returns:
        Set of inferred skills
    """
    prompt = f"""You are a job skills expert. Given a job title, list the core technical and professional skills typically required.

Job Title: {job_title}

List 8-12 essential skills for this role. Format: one skill per line, lowercase, no numbers or bullets.
Focus on concrete, specific skills (technologies, methodologies, competencies).

Skills:"""

    response = call_ollama(prompt, max_tokens=200)

    if not response:
        return set()

    # Parse response into skills - extract from descriptive sentences
    skills = set()
    import re

    # Common skill-indicating words and phrases to extract
    skill_patterns = [
        r'(?:including|such as|like)\s+([^.]+)',  # "including budgeting, marketing"
        r'(?:budgeting|planning|management|marketing|fundraising|coordination|strategic planning|leadership)',
        r'(?:financial|facilities|event|program|team|budget|compliance|policy|procedure)s?\s+(?:management|planning|development|coordination)',
    ]

    for line in response.split('\n'):
        line_lower = line.strip().lower()

        # Skip meta-text
        if any(phrase in line_lower for phrase in ['here are', 'typically required', 'job title']):
            continue

        # Method 1: Extract comma-separated items after "including", "such as"
        for match in re.finditer(r'(?:including|such as|like)\s+([^.]+)', line_lower):
            items = match.group(1)
            for item in items.split(','):
                skill = item.strip()
                skill = re.sub(r'\band\b', '', skill).strip()  # Remove "and"

                # Filter out malformed skills
                if not skill or len(skill) <= 2:
                    continue
                # Skip if starts with articles/prepositions/conjunctions
                if skill.split()[0] in ['the', 'a', 'an', 'to', 'for', 'with', 'of', 'in', 'or']:
                    continue
                # Skip if contains "or" (indicates incomplete parsing like "power bi or tableau")
                if ' or ' in skill:
                    continue
                # Skip if ends with incomplete phrases
                if skill.split()[-1] in ['related', 'to', 'for', 'with', 'or']:
                    continue
                # Skip if too long
                if len(skill.split()) > 4:
                    continue

                skills.add(skill)

        # Method 2: Extract common skill words directly
        common_skills = [
            'budgeting', 'marketing', 'planning', 'fundraising', 'leadership',
            'management', 'coordination', 'strategic planning', 'event management',
            'facilities management', 'program development', 'team building',
            'financial planning', 'compliance', 'policy development', 'coaching',
            'sponsorships', 'ticket sales', 'public relations', 'athletic administration'
        ]

        for common_skill in common_skills:
            if common_skill in line_lower:
                skills.add(common_skill)

    return skills


def validate_skill_gaps_with_llm(
    resume_text: str,
    jd_text: str,
    potential_gaps: List[str],
    already_matched: List[str]
) -> tuple[List[str], List[str]]:
    """
    Use local LLM to validate if gaps are real or false positives

    Replaces expensive OpenAI API calls with free local inference

    Args:
        resume_text: Full resume text
        jd_text: Full job description text
        potential_gaps: Skills marked as missing
        already_matched: Skills already confirmed as matched

    Returns:
        Tuple of (confirmed_gaps, recovered_matches)
    """
    if not potential_gaps or len(potential_gaps) > 20:
        # Don't validate if too many gaps (would be slow)
        return potential_gaps, []

    # Sample resume and JD text to keep prompt size reasonable
    resume_sample = resume_text[:1500]  # First ~300 words
    jd_sample = jd_text[:1000]

    gaps_str = ', '.join(potential_gaps[:10])  # Validate up to 10 gaps

    prompt = f"""You are analyzing if a resume matches job requirements.

Resume snippet:
{resume_sample}

Job requirements snippet:
{jd_sample}

The candidate is missing these skills: {gaps_str}

For EACH skill listed above, determine if it's truly missing or if the resume demonstrates it with different words/context.

Format your response as:
MISSING: skill1, skill2
PRESENT: skill3, skill4

Be strict - only mark as PRESENT if clearly demonstrated in the resume."""

    response = call_ollama(prompt, max_tokens=300)

    if not response:
        return potential_gaps, []

    # Parse LLM response
    confirmed_gaps = []
    recovered_matches = []

    for line in response.split('\n'):
        line = line.strip().lower()

        if line.startswith('missing:'):
            skills_text = line.replace('missing:', '').strip()
            confirmed_gaps.extend([s.strip() for s in skills_text.split(',') if s.strip()])
        elif line.startswith('present:'):
            skills_text = line.replace('present:', '').strip()
            recovered_matches.extend([s.strip() for s in skills_text.split(',') if s.strip()])

    # Ensure we return skills that were actually in potential_gaps
    confirmed_gaps = [g for g in potential_gaps if any(g.lower() in cg for cg in confirmed_gaps)]
    recovered_matches = [g for g in potential_gaps if any(g.lower() in rm for rm in recovered_matches)]

    # If LLM didn't parse correctly, return original gaps
    if not confirmed_gaps and not recovered_matches:
        return potential_gaps, []

    return confirmed_gaps, recovered_matches


def infer_contextual_skills(text_snippet: str, context: str = "resume") -> Set[str]:
    """
    Infer implicit skills from a text snippet using contextual understanding

    Args:
        text_snippet: Text to analyze (e.g., job description, work experience)
        context: Either "resume" or "job_description"

    Returns:
        Set of inferred skills
    """
    prompt = f"""Analyze this {context} text and identify skills that are implied but not explicitly stated.

Text:
{text_snippet[:800]}

List 5-10 skills that are clearly implied by the responsibilities/requirements described.
Format: one skill per line, lowercase, no bullets.

Implied skills:"""

    response = call_ollama(prompt, max_tokens=150)

    if not response:
        return set()

    skills = set()
    for line in response.split('\n'):
        skill = line.strip().lower().lstrip('0123456789.-•* ')
        if skill and len(skill) > 2 and len(skill.split()) <= 5:
            skills.add(skill)

    return skills
