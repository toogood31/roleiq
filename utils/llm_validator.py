import os
import json

def validate_gaps_with_llm(resume_text, jd_text, identified_gaps, identified_matches):
    """
    Use an LLM to validate whether identified gaps are truly missing from the resume.
    This helps catch false negatives where skills are present but phrased differently.

    Returns:
        - validated_gaps: List of gaps that are truly missing
        - recovered_matches: List of "gaps" that are actually present (false positives)
    """
    # Check if API key is available
    api_key = os.environ.get('ANTHROPIC_API_KEY')

    if not api_key:
        # If no API key, skip LLM validation and return original gaps
        return identified_gaps, []

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)

        # Construct validation prompt
        prompt = f"""You are an expert resume analyst. I have analyzed a resume against a job description and identified some potential skill gaps. However, my automated extraction may have missed skills that are present but phrased differently.

**Resume Text:**
{resume_text[:3000]}  # Truncate to avoid token limits

**Job Description Text:**
{jd_text[:3000]}

**Skills Found as Matches:**
{', '.join(identified_matches[:20])}

**Potential Gaps Identified:**
{', '.join(identified_gaps[:20])}

**Task:**
For each potential gap listed above, determine if it is:
1. TRULY_MISSING: The skill/requirement is genuinely absent from the resume
2. PRESENT_DIFFERENTLY: The skill is present in the resume but described using different terminology or as part of a broader responsibility

Return your analysis as a JSON object with this structure:
{{
    "truly_missing": ["skill1", "skill2", ...],
    "present_differently": ["skill3", "skill4", ...]
}}

Be thorough but strict - only mark something as "present_differently" if you can clearly identify where it appears in the resume with similar meaning."""

        # Call Claude API
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            temperature=0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse response
        response_text = message.content[0].text

        # Extract JSON from response
        try:
            # Try to find JSON in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                validation_result = json.loads(json_str)

                validated_gaps = validation_result.get('truly_missing', identified_gaps)
                recovered_matches = validation_result.get('present_differently', [])

                return validated_gaps, recovered_matches
            else:
                # Couldn't find JSON, return original
                return identified_gaps, []

        except json.JSONDecodeError:
            # If JSON parsing fails, return original gaps
            return identified_gaps, []

    except ImportError:
        # If anthropic package not installed, skip validation
        print("Warning: anthropic package not installed. Skipping LLM validation. Install with: pip install anthropic")
        return identified_gaps, []

    except Exception as e:
        # If any error occurs, fail gracefully and return original gaps
        print(f"Warning: LLM validation failed with error: {e}")
        return identified_gaps, []
