"""
PDF generator for comprehensive analysis reports from history
"""
from fpdf import FPDF


def generate_comprehensive_pdf(analysis):
    """
    Generate a comprehensive PDF report that matches the full analysis display.
    This includes all sections: metadata, scores, skills, experience, industry,
    education, and recommendations.

    Args:
        analysis: Dictionary containing complete analysis data from Firestore

    Returns:
        bytes: PDF file as bytes, or None if generation fails
    """
    def sanitize_text(text):
        """Replace unicode characters that can't be encoded in latin-1"""
        if not text:
            return text
        # Replace smart quotes and apostrophes with ASCII equivalents
        replacements = {
            '\u2019': "'",  # Right single quotation mark
            '\u2018': "'",  # Left single quotation mark
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark
            '\u2013': '-',  # En dash
            '\u2014': '--', # Em dash
            '\u2026': '...', # Horizontal ellipsis
        }
        for unicode_char, ascii_char in replacements.items():
            text = text.replace(unicode_char, ascii_char)
        # Remove any remaining non-latin-1 characters
        text = text.encode('latin-1', errors='ignore').decode('latin-1')
        return text

    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # ===== HEADER WITH LOGO =====
        import os

        # Add colored background bar at the top
        pdf.set_fill_color(30, 58, 95)  # Dark blue background matching logo
        pdf.rect(0, 0, 210, 35, 'F')  # Full width (A4 = 210mm), 35mm height

        # Add logo in top right corner
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'LOGO.png')
        if os.path.exists(logo_path):
            # Place logo in top right corner (25mm wide)
            # A4 width = 210mm, logo width = 25mm, margin = 10mm
            pdf.image(logo_path, x=175, y=8, w=25)

        # Add title text on the left side in white
        pdf.set_y(12)  # Position vertically in the header
        pdf.set_font("Arial", "B", 22)
        pdf.set_text_color(255, 255, 255)  # White text
        pdf.cell(0, 10, "Analysis Report", ln=True, align="L")

        # Reset to normal positioning below header
        pdf.set_y(38)
        pdf.set_text_color(0, 0, 0)  # Reset to black text

        # ===== METADATA =====
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(0, 0, 0)

        timestamp = analysis.get('timestamp')
        if timestamp:
            date_str = timestamp.strftime("%B %d, %Y at %I:%M %p")
        else:
            date_str = "N/A"

        pdf.cell(0, 6, f"Analysis Date: {date_str}", ln=True)
        pdf.cell(0, 6, f"Resume: {analysis.get('resume_filename', 'Unknown')}", ln=True)
        pdf.cell(0, 6, f"Job Description: {analysis.get('jd_filename', 'Unknown')}", ln=True)
        pdf.ln(8)

        # ===== OVERALL SCORE =====
        score = analysis.get('similarity_score', 0)
        pdf.set_font("Arial", "B", 18)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, f"Overall Match Score: {score}%", ln=True, align="C", fill=True)
        pdf.ln(5)

        # Score interpretation
        pdf.set_font("Arial", "", 10)
        if score >= 75:
            interpretation = "Excellent match! Your resume strongly aligns with the job requirements."
        elif score >= 50:
            interpretation = "Good match. Your resume shows relevant experience with some gaps to address."
        else:
            interpretation = "Moderate match. Consider highlighting more relevant skills or targeting roles that better fit your background."
        pdf.multi_cell(0, 6, interpretation)
        pdf.ln(5)

        # ===== DETAILED SKILL ANALYSIS =====
        skill_match = analysis.get('skill_match', {})

        if skill_match:
            pdf.set_font("Arial", "B", 14)
            pdf.set_text_color(30, 58, 95)
            pdf.cell(0, 8, "Detailed Skill Analysis", ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

            # Matched Skills - handle both 'matches' and 'common_skills'
            matches = skill_match.get('matches', []) or skill_match.get('common_skills', [])
            if matches:
                pdf.set_font("Arial", "B", 11)
                pdf.set_fill_color(16, 185, 129)  # Green
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 7, f"  Matched Skills ({len(matches)})", ln=True, fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "", 9)

                if len(matches) > 1:
                    pdf.multi_cell(0, 5, f"Your resume demonstrates {len(matches)} skills that directly match job requirements, showing strong alignment with the role's core competencies.")
                elif len(matches) == 1:
                    pdf.multi_cell(0, 5, "Your proven capability directly addresses a core job requirement, though additional skill development may strengthen your candidacy.")

                pdf.ln(2)
                pdf.set_font("Arial", "", 9)
                # Show all matched skills
                for skill in matches:
                    pdf.cell(0, 5, f"  * {sanitize_text(skill)}", ln=True)
                pdf.ln(3)

            # Missing Skills (Gaps)
            gaps = skill_match.get('gaps', [])
            if gaps:
                pdf.set_font("Arial", "B", 11)
                pdf.set_fill_color(239, 68, 68)  # Red
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 7, f"  Missing Skills ({len(gaps)})", ln=True, fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "", 9)

                if len(gaps) > 3:
                    pdf.multi_cell(0, 5, f"The job description lists {len(gaps)} required skills not clearly evident on your resume. Consider acquiring these skills or explicitly highlighting relevant experience.")
                elif len(gaps) > 1:
                    pdf.multi_cell(0, 5, f"Your resume is missing {len(gaps)} skills from the job requirements. Address these gaps through training or by reframing existing experience.")
                elif len(gaps) == 1:
                    pdf.multi_cell(0, 5, "The role requires a skill which is not clearly evident on your resume. While this may not be a dealbreaker, addressing it could strengthen your application.")

                pdf.ln(2)
                pdf.set_font("Arial", "", 9)
                # Show all missing skills
                for skill in gaps:
                    pdf.cell(0, 5, f"  * {sanitize_text(skill)}", ln=True)
                pdf.ln(3)

            # Similar Skills (Terminology Gaps)
            similar = skill_match.get('similar', [])
            if similar:
                pdf.set_font("Arial", "B", 11)
                pdf.set_fill_color(245, 158, 11)  # Orange
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 7, f"  Related Skills - Consider Rewording ({len(similar)})", ln=True, fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "I", 9)

                if len(similar) == 1:
                    pdf.multi_cell(0, 5, "You have experience which relates to JD requirements but uses different wording. Mirror the job description's exact language to improve ATS matching.")
                else:
                    pdf.multi_cell(0, 5, f"Your experience is relevant but phrased differently than the JD ({len(similar)} skills). Update your resume to use the employer's preferred terms for stronger keyword alignment.")

                pdf.ln(2)
                pdf.set_font("Arial", "", 9)
                # Show all similar skills
                for skill in similar:
                    pdf.cell(0, 5, f"  * {sanitize_text(skill)}", ln=True)
                pdf.ln(5)

        # ===== EXPERIENCE ANALYSIS =====
        experience_match = analysis.get('experience_match', {})
        if experience_match:
            pdf.set_font("Arial", "B", 14)
            pdf.set_text_color(30, 58, 95)
            pdf.cell(0, 8, "Experience Analysis", ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

            exp_score = experience_match.get('score', 0)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, f"Experience Match Score: {exp_score}%", ln=True)
            pdf.ln(2)

            details = experience_match.get('details', {})
            if details:
                # Relevant Experience Matches
                exp_matches = details.get('matches', [])
                if exp_matches:
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 6, "Relevant Experience:", ln=True)
                    pdf.set_font("Arial", "", 9)
                    for match in exp_matches:
                        pdf.multi_cell(0, 5, f"  * {sanitize_text(match)}")
                    pdf.ln(2)

                # Experience Gaps
                exp_gaps = details.get('gaps', [])
                if exp_gaps:
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 6, "Experience Gaps:", ln=True)
                    pdf.set_font("Arial", "", 9)
                    for gap in exp_gaps:
                        pdf.multi_cell(0, 5, f"  * {sanitize_text(gap)}")
                    pdf.ln(2)

            pdf.ln(3)

        # ===== INDUSTRY MATCH =====
        industry_match = analysis.get('industry_match', {})
        if industry_match:
            pdf.set_font("Arial", "B", 14)
            pdf.set_text_color(30, 58, 95)
            pdf.cell(0, 8, "Industry Alignment", ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

            ind_score = industry_match.get('score', 0)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, f"Industry Match Score: {ind_score}%", ln=True)

            ind_details = industry_match.get('details', {})
            if ind_details:
                pdf.set_font("Arial", "", 9)
                if ind_details.get('matches'):
                    matches_text = ', '.join([sanitize_text(m) for m in ind_details.get('matches', [])])
                    pdf.multi_cell(0, 5, f"Industry Alignment: {matches_text}")

            pdf.ln(3)

        # ===== EDUCATION MATCH =====
        education_match = analysis.get('education_match', {})
        if education_match:
            pdf.set_font("Arial", "B", 14)
            pdf.set_text_color(30, 58, 95)
            pdf.cell(0, 8, "Education Requirements", ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

            edu_score = education_match.get('score', 0)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, f"Education Match Score: {edu_score}%", ln=True)

            edu_details = education_match.get('details', {})
            if edu_details:
                pdf.set_font("Arial", "", 9)
                if edu_details.get('matches'):
                    matches_text = ', '.join([sanitize_text(m) for m in edu_details.get('matches', [])])
                    pdf.multi_cell(0, 5, f"Education: {matches_text}")
                if edu_details.get('gaps'):
                    gaps_text = ', '.join([sanitize_text(g) for g in edu_details.get('gaps', [])])
                    pdf.multi_cell(0, 5, f"Requirements: {gaps_text}")

            pdf.ln(3)

        # ===== RECOMMENDATIONS =====
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            pdf.set_font("Arial", "B", 14)
            pdf.set_text_color(30, 58, 95)
            pdf.cell(0, 8, "Resume Optimization Recommendations", ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

            pdf.set_font("Arial", "", 9)
            for i, rec in enumerate(recommendations, 1):
                pdf.set_font("Arial", "B", 9)
                pdf.cell(10, 5, f"{i}.", ln=False)
                pdf.set_font("Arial", "", 9)
                # Calculate remaining width for multi_cell
                remaining_width = pdf.w - pdf.l_margin - pdf.r_margin - 10
                # Save X position
                x_pos = pdf.get_x()
                y_pos = pdf.get_y()
                pdf.multi_cell(remaining_width, 5, sanitize_text(rec))
                pdf.ln(1)

        # ===== FOOTER =====
        pdf.ln(10)
        pdf.set_font("Arial", "I", 8)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 5, "Generated by RoleSynch - AI Resume Matcher by TooGood", ln=True, align="C")
        pdf.cell(0, 5, f"Report generated on {date_str}", ln=True, align="C")

        # Return PDF as bytes
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        return pdf_bytes

    except Exception as e:
        return None
