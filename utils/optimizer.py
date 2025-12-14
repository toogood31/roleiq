def generate_suggestions(gaps, similar, seniority_analysis, matches, score, industries=None, enhanced_analysis=None):
    """Generate executive-style suggestions with narrative summary and detailed guidance."""

    # Generate executive summary
    summary_parts = []

    # Assess overall alignment
    if score >= 85:
        alignment = "aligns very strongly with"
    elif score >= 70:
        alignment = "aligns well with"
    elif score >= 55:
        alignment = "shows moderate alignment with"
    else:
        alignment = "shows some gaps relative to"

    # Build strength narrative
    strength_areas = []
    if matches:
        strength_areas = matches[:4]  # Top skills that match

    strength_narrative = f", especially in {', '.join(strength_areas)}" if strength_areas else ""

    # Build gap narrative
    gap_narrative = ""
    if gaps:
        if len(gaps) <= 3:
            gap_narrative = f"The primary gaps are around {', '.join(gaps)}."
        else:
            gap_narrative = f"Key gaps include {', '.join(gaps[:3])}, among others."
    else:
        gap_narrative = "There are no significant skill gaps identified."

    summary = f"Your background {alignment} the role{strength_narrative}. {gap_narrative}"

    # Generate detailed optimization bullets
    optimization_points = []
    tier4_points = []  # Collect Tier 4 recommendations separately to prioritize them

    if gaps:
        # Prioritize top 3-5 gaps
        top_gaps = gaps[:5]
        if len(top_gaps) <= 2:
            optimization_points.append(
                f"Add explicit examples demonstrating {' and '.join(top_gaps)} to directly address the missing requirements in the job description."
            )
        else:
            optimization_points.append(
                f"Add explicit examples demonstrating {', '.join(top_gaps[:2])}, and {top_gaps[2]} to directly address the missing requirements."
            )

    if similar:
        # Suggest rephrasing similar skills
        top_similar = similar[:3]
        if len(top_similar) == 1:
            optimization_points.append(
                f"Rephrase your experience with {top_similar[0]} to use terminology that more closely matches the job description requirements."
            )
        else:
            optimization_points.append(
                f"Rephrase your experience with {', '.join(top_similar[:2])} to use terminology that more closely matches the job description requirements."
            )

    # DEBUG: Print Tier 4 data to diagnose why recommendations aren't showing
    if enhanced_analysis:
        print("\n=== TIER 4 DEBUG ===")
        gap_severity_debug = enhanced_analysis.get('gap_severity', [])
        print(f"Gap Severity Data: {gap_severity_debug}")

        skill_evidence_debug = enhanced_analysis.get('skill_evidence', [])
        print(f"Skill Evidence Data: {skill_evidence_debug[:3] if skill_evidence_debug else 'None'}")

        keyword_placement_debug = enhanced_analysis.get('keyword_placement', {})
        print(f"Keyword Placement Keys: {keyword_placement_debug.keys() if keyword_placement_debug else 'None'}")

        bullet_quality_debug = enhanced_analysis.get('bullet_quality', {})
        print(f"Bullet Quality Data: weak_count={bullet_quality_debug.get('weak_count', 0)}, avg_score={bullet_quality_debug.get('avg_score', 0)}")
        print("===================\n")

    # Add seniority-specific guidance (enhanced with verb analysis and leadership signals)
    if enhanced_analysis:
        verb_analysis = enhanced_analysis.get('verb_strength', {})
        leadership = enhanced_analysis.get('leadership_signals', {})
        achievements = enhanced_analysis.get('achievements', {})
        task_outcome = enhanced_analysis.get('task_vs_outcome', {})
        section_scores = enhanced_analysis.get('section_scores', {})
        skill_redundancies = enhanced_analysis.get('skill_redundancies', [])
        gap_categorization = enhanced_analysis.get('gap_categorization', {})
        gap_context = enhanced_analysis.get('gap_context', {})

        # Verb strength recommendations
        if verb_analysis.get('weak_pct', 0) > 25:
            optimization_points.append(
                f"Replace weak action verbs (currently {verb_analysis['weak_pct']:.0f}% of bullets) with stronger leadership language like 'led', 'owned', 'directed', or 'established'."
            )

        # Task vs outcome recommendations
        if task_outcome.get('outcome_pct', 100) < 40:
            optimization_points.append(
                f"Transform task-based bullets into outcome-based achievements by adding specific metrics, percentages, or dollar amounts to demonstrate impact."
            )

        # Leadership signal recommendations
        if leadership.get('leadership_score', 100) < 40:
            optimization_points.append(
                "Add leadership context by highlighting team management, decision-making authority, strategic planning, or P&L ownership to demonstrate seniority."
            )

        # Achievement-specific recommendations
        if not any([achievements.get('dollar_amounts'), achievements.get('percentages'), achievements.get('team_sizes')]):
            optimization_points.append(
                "Quantify your impact by adding dollar amounts, efficiency percentages, team sizes, or transaction volumes to demonstrate scope and results."
            )

        # Section-level recommendations (Tier 2)
        if section_scores:
            # Find weakest section
            weakest_section = None
            weakest_score = 11  # Start higher than max score

            for section_name, section_data in section_scores.items():
                if section_data['score'] < weakest_score:
                    weakest_score = section_data['score']
                    weakest_section = (section_name, section_data)

            # Add specific recommendation for weakest section
            if weakest_section and weakest_score < 6:
                section_name, section_data = weakest_section
                recommendation = section_data.get('recommendation', '')
                if recommendation and recommendation not in optimization_points:
                    optimization_points.append(recommendation)

        # Skill redundancy recommendations (Tier 2)
        if skill_redundancies and len(skill_redundancies) >= 2:
            # Show user they have redundant skills
            primary_example = skill_redundancies[0]['primary']
            dupes = skill_redundancies[0]['duplicates']
            optimization_points.append(
                f"Remove redundant skills to save space - you list '{primary_example}' multiple times as: {', '.join(dupes[:2])}. Keep the most specific version only."
            )

        # Hard vs soft skill gap prioritization (Tier 2)
        if gap_categorization:
            hard_gaps = gap_categorization.get('hard_skills', [])
            soft_gaps = gap_categorization.get('soft_skills', [])

            # Prioritize hard skill gaps
            if hard_gaps and len(hard_gaps) >= 2:
                optimization_points.append(
                    f"Critical hard skill gaps to address: {', '.join(hard_gaps[:3])}. These technical skills are essential for the role."
                )

        # Gap context validation (Tier 2) - identify likely false positives
        if gap_context:
            false_positive_gaps = [
                gap for gap, context in gap_context.items()
                if context.get('likely_false_positive', False)
            ]

            if false_positive_gaps:
                # Don't add a negative point, but adjust existing gap recommendations
                # This is handled internally - gaps are already filtered by LLM validation
                pass

        # Tier 3: Experience progression recommendations
        experience_progression = enhanced_analysis.get('experience_progression', {})
        if experience_progression:
            progression_quality = experience_progression.get('progression_quality', 'unclear')
            promotions = experience_progression.get('promotions', 0)
            career_gaps = experience_progression.get('career_gaps', [])

            if progression_quality == 'lateral' and promotions == 0:
                optimization_points.append(
                    "Highlight career growth by emphasizing scope increases, new responsibilities, or leadership opportunities at each role, even if titles remained similar."
                )
            elif career_gaps and len(career_gaps) > 0:
                optimization_points.append(
                    f"Address career gaps or short tenures by briefly explaining transitions (e.g., contract work, further education, or strategic career moves)."
                )

        # Tier 3: Skill co-occurrence recommendations
        skill_cooccurrence = enhanced_analysis.get('skill_cooccurrence', [])
        if skill_cooccurrence and len(skill_cooccurrence) > 0:
            # Get first missing complementary skill
            first_pair = skill_cooccurrence[0]
            optimization_points.append(
                f"Add complementary skill '{first_pair['missing']}' - you have '{first_pair['has']}' but the role requires both."
            )

        # Tier 3: Readability recommendations
        readability = enhanced_analysis.get('readability', {})
        if readability:
            passive_pct = readability.get('passive_pct', 0)
            avg_sentence_length = readability.get('avg_sentence_length', 0)
            issues = readability.get('issues', [])

            if passive_pct > 30:
                optimization_points.append(
                    f"Reduce passive voice (currently {passive_pct:.0f}% of sentences) by using active, direct language like 'I led' instead of 'was responsible for'."
                )
            elif avg_sentence_length > 25 and 'long' in str(issues):
                optimization_points.append(
                    "Simplify complex sentences by breaking them into shorter, punchier statements that are easier for recruiters to scan quickly."
                )

        # Tier 3: Scope level mismatch recommendations
        scope_analysis = enhanced_analysis.get('scope_analysis', {})
        if scope_analysis:
            recommendation = scope_analysis.get('recommendation')
            if recommendation:
                optimization_points.append(recommendation)

        # Tier 3: Consistency issue recommendations
        consistency_check = enhanced_analysis.get('consistency_check', {})
        if consistency_check:
            consistency_issues = consistency_check.get('consistency_issues', [])
            if consistency_issues and len(consistency_issues) > 0:
                # Add the first consistency issue as a recommendation
                optimization_points.append(consistency_issues[0])

        # Tier 4: Gap severity recommendations (prioritize critical gaps)
        gap_severity = enhanced_analysis.get('gap_severity', [])
        if gap_severity and len(gap_severity) > 0:
            # Get critical and high priority gaps
            critical_gaps = [g for g in gap_severity if g['severity'] in ['CRITICAL', 'HIGH']]
            print(f"DEBUG: Found {len(critical_gaps)} critical/high gaps out of {len(gap_severity)} total gaps")
            if critical_gaps:
                # Focus on top critical gap with specific context
                top_gap = critical_gaps[0]
                gap_name = top_gap['gap']
                signals = top_gap.get('signals', [])
                frequency = top_gap.get('frequency', 0)

                # Build detailed recommendation
                detail = f"mentioned {frequency}x in JD" if frequency > 1 else ""
                if signals and len(signals) > 0:
                    detail = ', '.join(signals[:2])

                rec = f"PRIORITY: Add '{gap_name}' - this critical skill ({detail}). Provide specific example demonstrating this capability."
                tier4_points.append(rec)
                print(f"DEBUG: Added gap severity recommendation (TIER 4): {rec[:80]}...")

        # Tier 4: Skill evidence recommendations (identify weak skill claims)
        skill_evidence = enhanced_analysis.get('skill_evidence', [])
        if skill_evidence and len(skill_evidence) > 0:
            # Get skills with weak evidence
            weak_evidence = [s for s in skill_evidence if s['quality'] == 'WEAK']
            print(f"DEBUG: Found {len(weak_evidence)} weak evidence skills out of {len(skill_evidence)} total skills")
            if weak_evidence:
                # Pick first weak skill
                weak_skill = weak_evidence[0]
                skill_name = weak_skill['skill']
                rec = f"Strengthen '{skill_name}' claim - currently only listed without examples. Add specific project where you used this skill with quantified results."
                tier4_points.append(rec)
                print(f"DEBUG: Added skill evidence recommendation (TIER 4): {rec[:80]}...")

        # Tier 4: Keyword placement recommendations (flag buried keywords)
        keyword_placement = enhanced_analysis.get('keyword_placement', {})
        if keyword_placement:
            buried = keyword_placement.get('buried_critical', [])
            bottom_third = keyword_placement.get('bottom_third', [])
            print(f"DEBUG: Keyword placement - buried={len(buried) if buried else 0}, bottom_third={len(bottom_third) if bottom_third else 0}")

            if buried and len(buried) > 0:
                # Flag first buried critical keyword
                buried_skill = buried[0]
                rec = f"Move '{buried_skill}' higher in resume - currently buried in bottom third where ATS may miss it. Add to summary or top third of experience section."
                tier4_points.append(rec)
                print(f"DEBUG: Added keyword placement recommendation (TIER 4): {rec[:80]}...")
            elif bottom_third and len(bottom_third) > 1:
                # General placement recommendation
                first_skill = bottom_third[0]['skill']
                position = bottom_third[0]['position_pct']
                rec = f"Improve keyword visibility - '{first_skill}' appears at {position:.0f}% through resume. Move important skills to top 30% for better ATS scoring."
                tier4_points.append(rec)
                print(f"DEBUG: Added keyword placement recommendation (TIER 4): {rec[:80]}...")

        # Tier 4: Bullet quality recommendations (specific rewrites)
        bullet_quality = enhanced_analysis.get('bullet_quality', {})
        if bullet_quality:
            weak_count = bullet_quality.get('weak_count', 0)
            avg_score = bullet_quality.get('avg_score', 0)
            bullet_scores = bullet_quality.get('bullet_scores', [])
            print(f"DEBUG: Bullet quality - weak_count={weak_count}, avg_score={avg_score}, threshold check: {weak_count >= 3 and avg_score < 5.5}")

            if weak_count >= 3 and avg_score < 5.5:
                # Get weakest bullet
                if bullet_scores and len(bullet_scores) > 0:
                    weakest = bullet_scores[0]  # Already sorted ascending
                    issues = weakest.get('issues', [])
                    if issues:
                        # Provide specific rewrite guidance
                        primary_issue = issues[0]
                        rec = f"Rewrite {weak_count} weak bullets - example issue: {primary_issue}. Transform task statements into achievement statements with metrics."
                        tier4_points.append(rec)
                        print(f"DEBUG: Added bullet quality recommendation (TIER 4): {rec[:80]}...")

        # Ontology: Certification gap recommendations (dealbreaker alerts)
        certification_gaps = enhanced_analysis.get('certification_gaps', {})
        if certification_gaps:
            missing_critical = certification_gaps.get('missing_critical', [])
            missing_valuable = certification_gaps.get('missing_valuable', [])
            has_certifications = certification_gaps.get('has_certifications', False)

            print(f"DEBUG: Certification gaps - critical={len(missing_critical)}, valuable={len(missing_valuable)}, has_certs={has_certifications}")

            # Critical certifications are potential dealbreakers
            if missing_critical:
                for cert in missing_critical[:2]:  # Top 2 critical certifications
                    cert_name = cert['name']
                    cert_full = cert['full_name']
                    rec = f"DEALBREAKER: Job requires {cert_name} ({cert_full}) certification not found in resume. Add this credential or explain equivalent experience."
                    tier4_points.append(rec)
                    print(f"DEBUG: Added critical certification gap (TIER 4): {rec[:80]}...")

            # Valuable certifications are competitive advantages
            elif missing_valuable and not has_certifications:
                # Only suggest if resume has no certifications at all
                top_valuable = missing_valuable[0]
                cert_name = top_valuable['name']
                cert_full = top_valuable['full_name']
                rec = f"Consider adding {cert_name} ({cert_full}) certification - highly valued for this role and would strengthen your candidacy."
                optimization_points.append(rec)  # Lower priority than Tier 4
                print(f"DEBUG: Added valuable certification suggestion: {rec[:80]}...")

        # Beta-critical: Education validation recommendations
        education_validation = enhanced_analysis.get('education_validation', {})
        if education_validation and education_validation.get('severity') != 'NONE':
            severity = education_validation.get('severity')
            degree_gap = education_validation.get('degree_level_gap')
            field_gap = education_validation.get('field_of_study_gap')
            gpa_gap = education_validation.get('gpa_gap')

            print(f"DEBUG: Education validation - severity={severity}, degree_gap={degree_gap is not None}, field_gap={field_gap is not None}")

            if degree_gap and severity == 'DEALBREAKER':
                required_degree = degree_gap['required']
                found_degree = degree_gap['found']
                rec = f"DEALBREAKER: Job requires {required_degree.upper()} degree - resume shows {found_degree}. This may disqualify your application."
                tier4_points.append(rec)
                print(f"DEBUG: Added education dealbreaker (TIER 4): {rec[:80]}...")
            elif degree_gap and severity == 'WARNING':
                required_degree = degree_gap['required']
                rec = f"Job prefers {required_degree.upper()} degree. Consider highlighting equivalent experience or ongoing education to compensate."
                optimization_points.append(rec)

            if field_gap and field_gap.get('found') == False:
                required_field = field_gap['required_field']
                rec = f"DEALBREAKER: Job requires {required_field.title()} background. Emphasize relevant coursework, projects, or self-study in this field."
                tier4_points.append(rec)
                print(f"DEBUG: Added field of study dealbreaker (TIER 4): {rec[:80]}...")

            if gpa_gap:
                required_gpa = gpa_gap['required']
                found_gpa = gpa_gap['found']
                if found_gpa and found_gpa < required_gpa:
                    rec = f"GPA below requirement ({found_gpa} vs {required_gpa}). Consider removing GPA and highlighting academic achievements instead."
                    optimization_points.append(rec)
                elif not found_gpa:
                    rec = f"Job requires {required_gpa} GPA. Add your GPA if it meets requirement, or emphasize academic projects and achievements."
                    optimization_points.append(rec)

        # Beta-critical: Experience validation recommendations
        experience_validation = enhanced_analysis.get('experience_validation', {})
        if experience_validation and experience_validation.get('severity') != 'NONE':
            severity = experience_validation.get('severity')
            meets_minimum = experience_validation.get('meets_minimum')
            min_required = experience_validation.get('min_required')
            resume_years = experience_validation.get('resume_years')
            overqualified = experience_validation.get('overqualified')

            print(f"DEBUG: Experience validation - severity={severity}, meets_min={meets_minimum}, required={min_required}, resume={resume_years}")

            if not meets_minimum and severity == 'DEALBREAKER':
                gap = min_required - resume_years
                rec = f"DEALBREAKER [v5-FIXED]: Job requires {min_required}+ years experience - resume shows {resume_years} years ({gap} year gap). This is a significant barrier."
                tier4_points.append(rec)
                print(f"DEBUG: Added experience dealbreaker (TIER 4): {rec[:80]}...")
            elif not meets_minimum and severity == 'WARNING':
                rec = f"Resume shows {resume_years} years vs {min_required}+ required. Emphasize depth of impact and advanced responsibilities to compensate."
                optimization_points.append(rec)

            if overqualified:
                rec = f"You may be overqualified ({resume_years} years for {min_required}+ role). Tailor resume to focus on relevant skills rather than full career scope."
                optimization_points.append(rec)

    elif "Different" in seniority_analysis or "gap" in seniority_analysis.lower():
        optimization_points.append(
            "Expand your leadership and responsibility narrative by highlighting specific promotions, team leadership, cross-functional influence, or strategic initiatives you've owned."
        )
    else:
        optimization_points.append(
            "Strengthen your impact statements with quantifiable metrics (revenue impact, team size, budget managed, efficiency gains) to reinforce your seniority level."
        )

    # Add strategic suggestions
    if matches and len(matches) >= 3:
        optimization_points.append(
            f"Emphasize your strongest alignments ({', '.join(matches[:3])}) by moving them higher in your resume and adding specific achievement examples."
        )

    # Industry-specific guidance
    if industries:
        jd_industries = industries.get('jd', [])
        resume_industries = industries.get('resume', [])

        if jd_industries and len(jd_industries) > 0:
            primary_jd_industry = jd_industries[0][0]

            # Check if there's an industry mismatch
            if resume_industries and len(resume_industries) > 0:
                primary_resume_industry = resume_industries[0][0]
                if primary_jd_industry != primary_resume_industry and primary_jd_industry != 'general':
                    # Provide industry transition guidance
                    optimization_points.append(
                        f"Since this role is in {primary_jd_industry}, emphasize transferable skills and any exposure to {primary_jd_industry}-related projects, tools, or cross-functional work."
                    )

            # Add industry-specific best practices
            industry_tips = {
                'technology': "Include specific technologies, programming languages, and frameworks. Quantify impact with metrics like performance improvements, user adoption, or system reliability.",
                'finance': "Highlight regulatory knowledge, financial metrics managed (AUM, revenue, P&L), and any relevant certifications (CFA, CPA, Series licenses).",
                'healthcare': "Emphasize patient outcomes, compliance with healthcare regulations (HIPAA), and experience with clinical systems or healthcare technology.",
                'marketing': "Showcase campaign results with specific metrics (ROI, conversion rates, engagement). Include tools/platforms expertise (Google Analytics, HubSpot, etc.).",
                'sales': "Lead with revenue impact, quota attainment percentages, deal sizes, and customer retention metrics. Highlight CRM expertise and sales methodologies.",
                'hr': "Quantify talent metrics (time-to-fill, retention rates, employee satisfaction scores). Mention HRIS systems and employment law knowledge.",
                'creative': "Ensure your portfolio is prominently mentioned. Describe creative projects with measurable business impact (brand awareness, engagement, conversions).",
                'legal': "Highlight bar admissions, practice areas, case outcomes, and regulatory expertise. Include any published work or speaking engagements."
            }

            if primary_jd_industry in industry_tips and len(optimization_points) < 5:
                optimization_points.append(industry_tips[primary_jd_industry])

    # ATS optimization (enhanced with keyword density analysis)
    if enhanced_analysis:
        ats_analysis = enhanced_analysis.get('ats_optimization', {})
        coverage_pct = ats_analysis.get('coverage_pct', 0)
        missing_important = ats_analysis.get('missing_important', [])

        if coverage_pct < 70 and missing_important:
            optimization_points.append(
                f"Improve ATS keyword coverage (currently {coverage_pct:.0f}%) by adding high-priority terms: {', '.join(missing_important[:3])}."
            )
        elif coverage_pct >= 70:
            optimization_points.append(
                "Mirror key phrases from the job description in your resume to improve ATS matching and keyword relevance, particularly in your summary and core competencies sections."
            )
    else:
        optimization_points.append(
            "Mirror key phrases from the job description in your resume to improve ATS matching and keyword relevance, particularly in your summary and core competencies sections."
        )

    # Ensure we have at least 4 points (will be capped at 8)
    if len(optimization_points) < 4:
        optimization_points.append(
            "Review each bullet point to ensure it demonstrates measurable outcomes and uses active, results-oriented language."
        )

    # Prioritize Tier 4 recommendations by placing them first
    final_recommendations = tier4_points + optimization_points

    return {
        'summary': summary,
        'optimization_points': final_recommendations[:8],  # Tier 4 first, then Tier 1-3, cap at 8
        'industries': industries  # Pass through for display
    }