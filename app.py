import streamlit as st
from utils.matcher import match_resume_jd
from utils.optimizer import generate_suggestions
from utils.parser import parse_document
from utils.analytics import track_event
import os
from fpdf import FPDF  # For PDF generation
import streamlit.components.v1 as components

# Initialize session state for "Analyze Another" functionality
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False

# Google Analytics - Replace with your GA4 Measurement ID
GA_MEASUREMENT_ID = "G-XXXXXXXXXX"  # TODO: Replace with your actual GA4 ID

# Inject Google Analytics
if GA_MEASUREMENT_ID != "G-XXXXXXXXXX":
    ga_script = f"""
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{GA_MEASUREMENT_ID}');
    </script>
    """
    components.html(ga_script, height=0)

# Hide sidebar from regular users
hide_sidebar_css = """
<style>
    [data-testid="stSidebar"] {
        display: none;
    }
</style>
"""
st.markdown(hide_sidebar_css, unsafe_allow_html=True)

st.title("RoleIQ: AI Resume Matcher")

# Show "Analyze Another" button if analysis is complete
if st.session_state.analysis_complete:
    if st.button("🔄 Analyze Another Resume", key="reset_btn", type="primary"):
        track_event('analyze_another_clicked', {}, GA_MEASUREMENT_ID)
        st.session_state.analysis_complete = False
        st.rerun()

# Side by side layout for uploads
col1, col2 = st.columns(2)

with col1:
    st.subheader("Upload Resume")
    resume_file = st.file_uploader("(PDF or DOCX)", type=["pdf", "docx"], key="resume_uploader")
    # File validation feedback
    if resume_file:
        file_size = len(resume_file.getvalue()) / 1024  # KB
        st.success(f"✓ {resume_file.name} ({file_size:.1f} KB)")

with col2:
    st.subheader("Job Description")
    jd_file = st.file_uploader("(PDF or DOCX - Optional)", type=["pdf", "docx"], key="jd_uploader")
    if jd_file:
        file_size = len(jd_file.getvalue()) / 1024  # KB
        st.success(f"✓ {jd_file.name} ({file_size:.1f} KB)")
    jd_text = st.text_area("Or enter/paste JD here", height=200)
    if jd_text and not jd_file:
        char_count = len(jd_text)
        st.info(f"ℹ️ {char_count} characters entered")

if st.button("Analyze", key="analyze_btn") and resume_file:
    jd_input = ""
    if jd_file:
        # Save and parse JD file with extension
        jd_ext = os.path.splitext(jd_file.name)[1]
        temp_jd_path = f"temp_jd{jd_ext}"
        with open(temp_jd_path, "wb") as f:
            f.write(jd_file.getvalue())
        jd_input = temp_jd_path
    elif jd_text:
        jd_input = jd_text
    else:
        st.error("Please provide a Job Description via upload or text.")
        st.stop()

    # Progress indicator
    progress_text = st.empty()
    progress_bar = st.progress(0)

    try:
        # Step 1: Parse documents
        progress_text.text("📄 Parsing documents...")
        progress_bar.progress(20)

        # Save uploaded resume with extension
        resume_ext = os.path.splitext(resume_file.name)[1]
        temp_resume_path = f"temp_resume{resume_ext}"
        with open(temp_resume_path, "wb") as f:
            f.write(resume_file.getvalue())

        # Step 2: Extract skills and content
        progress_text.text("🔍 Extracting skills and analyzing content...")
        progress_bar.progress(40)

        result = match_resume_jd(
            temp_resume_path,
            jd_input,
            'data/ontologies/esco_skills_en.csv',
            'data/ontologies/seniority_levels.json'
        )

        # Check for errors
        if 'error' in result:
            # Track error event
            track_event('error_occurred', {
                'error_type': result['error_type'],
                'error_message': result['error']
            }, GA_MEASUREMENT_ID)

            st.error(f"**{result['error_type']}:** {result['error']}")
            if 'details' in result:
                st.info(result['details'])
            # Cleanup temp files
            if os.path.exists(temp_resume_path):
                os.remove(temp_resume_path)
            if jd_file and os.path.exists(jd_input):
                os.remove(jd_input)
            st.stop()

        # Step 3: Computing match score
        progress_text.text("📊 Computing match score...")
        progress_bar.progress(60)

        # Step 4: Generating recommendations
        progress_text.text("💡 Generating personalized recommendations...")
        progress_bar.progress(80)

        suggestions = generate_suggestions(
            result['comp_details']['gaps'],
            result['comp_details']['similar'],
            result['seniority_analysis'],
            result['comp_details']['matches'],
            result['score'],
            result.get('industries', None),
            result.get('enhanced_analysis', None)
        )

        # Step 5: Finalizing report
        progress_text.text("✅ Finalizing report...")
        progress_bar.progress(100)

        # Clear progress indicators
        progress_text.empty()
        progress_bar.empty()

    except Exception as e:
        st.error(f"An error occurred during analysis: {str(e)}")
        # Cleanup temp files on error
        if os.path.exists(temp_resume_path):
            os.remove(temp_resume_path)
        if jd_file and 'temp_jd_path' in locals() and os.path.exists(temp_jd_path):
            os.remove(temp_jd_path)
        st.stop()

    st.success("Analysis Complete!")
    st.markdown("<hr>", unsafe_allow_html=True)

    # Match Score
    st.write(f"**Match Score:** {result['score']:.0f}%")
    st.markdown("")

    # Executive Summary
    st.subheader("Summary")
    if isinstance(suggestions, dict) and 'summary' in suggestions:
        st.write(suggestions['summary'])
    st.markdown("<hr>", unsafe_allow_html=True)

    # Role Fit Analysis - Structured like the example
    st.subheader("Role Fit Analysis")
    comp_details = result['comp_details']

    # Where Resume Aligns Well
    st.write("**Where the Resume Aligns Well (✔️):**")
    st.markdown("")

    if comp_details['matches']:
        # Group matches into meaningful bullets
        matches = comp_details['matches']
        if len(matches) > 0:
            # Create narrative bullets based on matches
            match_groups = []
            # First bullet: primary skill matches
            if len(matches) >= 3:
                match_groups.append(f"Strong expertise in {', '.join(matches[:3])}, directly matching core job requirements.")
            elif len(matches) == 2:
                match_groups.append(f"Demonstrated experience in {matches[0]} and {matches[1]}, aligning with key job requirements.")
            elif len(matches) == 1:
                match_groups.append(f"Proven capability in {matches[0]}, matching a critical job requirement.")

            # Additional matches if present
            if len(matches) > 3:
                remaining = matches[3:]
                if len(remaining) <= 3:
                    match_groups.append(f"Additional alignment in {', '.join(remaining)}.")
                else:
                    match_groups.append(f"Additional alignment in {', '.join(remaining[:3])}, among other areas.")

            for match_point in match_groups:
                st.write(f"• {match_point}")
                st.markdown("")
    else:
        st.write("• Limited direct skill matches found. Focus on highlighting transferable experience.")
        st.markdown("")

    # Add generic strength points
    st.write("• Background demonstrates relevant professional experience and capability to contribute to similar roles.")
    st.markdown("")

    # Where Resume Does Not Fully Align
    st.markdown("")
    st.write("**Where the Resume Does Not Fully Align (⚠️):**")
    st.markdown("")

    if comp_details['gaps']:
        gaps = comp_details['gaps']
        # Create narrative bullets for gaps
        gap_points = []

        if len(gaps) >= 3:
            gap_points.append(f"Limited explicit experience with {gaps[0]}, {gaps[1]}, and {gaps[2]}, which are mentioned in the job description.")
        elif len(gaps) == 2:
            gap_points.append(f"Missing direct mention of {gaps[0]} and {gaps[1]} in current resume.")
        elif len(gaps) == 1:
            gap_points.append(f"No explicit reference to {gaps[0]}, which is specified in the job requirements.")

        if len(gaps) > 3:
            additional_gaps = gaps[3:6]
            if additional_gaps:
                gap_points.append(f"Additional gaps in {', '.join(additional_gaps)}{' and others' if len(gaps) > 6 else ''}.")

        for gap_point in gap_points:
            st.write(f"• {gap_point}")
            st.markdown("")
    else:
        st.write("• No significant gaps identified between resume and job requirements.")
        st.markdown("")

    # Similar skills that could be rephrased
    if comp_details['similar']:
        similar_text = ', '.join(comp_details['similar'][:3])
        st.write(f"• Experience with {similar_text} could be rephrased to better mirror job description terminology.")
        st.markdown("")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Resume Optimization Guidance
    st.subheader("Resume Optimization Guidance")

    if result['score'] >= 90:
        target_text = "maintain your strong position"
    elif result['score'] >= 80:
        target_text = "push your match score closer to 95%"
    elif result['score'] >= 70:
        target_text = "strengthen your alignment to 85-90%"
    else:
        target_text = "significantly improve your match score"

    st.write(f"*To {target_text}, update your resume with the following enhancements:*")
    st.markdown("")

    if isinstance(suggestions, dict) and 'optimization_points' in suggestions:
        for i, point in enumerate(suggestions['optimization_points'], 1):
            st.write(f"{i}. {point}")
            st.markdown("")
    else:
        st.write("Continue to refine your resume to match job description terminology and requirements.")

    # Generate PDF with modern color scheme
    # Color palette (RGB values):
    # Ink Black: (1, 22, 30)
    # Dark Teal: (18, 69, 89)
    # Air Force Blue: (89, 131, 146)
    # Ash Grey: (174, 195, 176)
    # Beige: (239, 246, 224)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    # Header with colored background
    pdf.set_fill_color(18, 69, 89)  # Dark Teal background
    pdf.rect(0, 0, 210, 40, 'F')  # Full width header

    # Title
    pdf.set_text_color(239, 246, 224)  # Beige text
    pdf.set_font("Arial", 'B', size=18)
    pdf.cell(0, 25, "WorkAlign Analysis Report", ln=True, align='C')
    pdf.set_text_color(1, 22, 30)  # Reset to Ink Black
    pdf.ln(10)

    # Match Score with highlighted box
    pdf.set_fill_color(89, 131, 146)  # Air Force Blue background
    pdf.set_text_color(239, 246, 224)  # Beige text
    pdf.set_font("Arial", 'B', size=16)
    pdf.cell(0, 12, f"Match Score: {result['score']:.0f}%", ln=True, align='C', fill=True)
    pdf.set_text_color(1, 22, 30)  # Reset to Ink Black
    pdf.ln(5)

    # Executive Summary Section
    pdf.set_fill_color(239, 246, 224)  # Beige background
    pdf.rect(10, pdf.get_y(), 190, 8, 'F')
    pdf.set_text_color(18, 69, 89)  # Dark Teal text
    pdf.set_font("Arial", 'B', size=14)
    pdf.cell(0, 8, "Summary", ln=True)
    pdf.set_text_color(1, 22, 30)  # Ink Black
    pdf.set_font("Arial", size=11)
    if isinstance(suggestions, dict) and 'summary' in suggestions:
        pdf.multi_cell(0, 6, suggestions['summary'])
    pdf.ln(5)

    # Role Fit Analysis Section Header
    pdf.set_fill_color(239, 246, 224)  # Beige background
    pdf.rect(10, pdf.get_y(), 190, 8, 'F')
    pdf.set_text_color(18, 69, 89)  # Dark Teal text
    pdf.set_font("Arial", 'B', size=14)
    pdf.cell(0, 8, "Role Fit Analysis", ln=True)
    pdf.set_text_color(1, 22, 30)  # Ink Black
    pdf.ln(2)

    # Where Resume Aligns Well
    pdf.set_text_color(89, 131, 146)  # Air Force Blue
    pdf.set_font("Arial", 'B', size=12)
    pdf.cell(0, 7, "Where the Resume Aligns Well:", ln=True)
    pdf.set_text_color(1, 22, 30)  # Ink Black
    pdf.ln(1)

    pdf.set_font("Arial", size=10)
    if comp_details['matches']:
        matches = comp_details['matches']
        # Primary matches
        if len(matches) >= 3:
            pdf.multi_cell(0, 5, f"- Strong expertise in {', '.join(matches[:3])}, directly matching core job requirements.")
            pdf.ln(1)
        elif len(matches) >= 1:
            pdf.multi_cell(0, 5, f"- Demonstrated experience in {', '.join(matches)}, aligning with key job requirements.")
            pdf.ln(1)

        # Additional matches
        if len(matches) > 3:
            remaining = matches[3:]
            if len(remaining) <= 3:
                pdf.multi_cell(0, 5, f"- Additional alignment in {', '.join(remaining)}.")
            else:
                pdf.multi_cell(0, 5, f"- Additional alignment in {', '.join(remaining[:3])}, among other areas.")
            pdf.ln(1)
    else:
        pdf.multi_cell(0, 5, "- Limited direct skill matches found. Focus on highlighting transferable experience.")
        pdf.ln(1)

    pdf.multi_cell(0, 5, "- Background demonstrates relevant professional experience and capability to contribute to similar roles.")
    pdf.ln(3)

    # Where Resume Does Not Fully Align
    pdf.set_text_color(89, 131, 146)  # Air Force Blue
    pdf.set_font("Arial", 'B', size=12)
    pdf.cell(0, 7, "Where the Resume Does Not Fully Align:", ln=True)
    pdf.set_text_color(1, 22, 30)  # Ink Black
    pdf.ln(1)

    pdf.set_font("Arial", size=10)
    if comp_details['gaps']:
        gaps = comp_details['gaps']
        if len(gaps) >= 3:
            pdf.multi_cell(0, 5, f"- Limited explicit experience with {gaps[0]}, {gaps[1]}, and {gaps[2]}, which are mentioned in the job description.")
            pdf.ln(1)
        elif len(gaps) >= 1:
            pdf.multi_cell(0, 5, f"- Missing direct mention of {', '.join(gaps[:2])} in current resume.")
            pdf.ln(1)

        if len(gaps) > 3:
            additional_gaps = gaps[3:6]
            if additional_gaps:
                pdf.multi_cell(0, 5, f"- Additional gaps in {', '.join(additional_gaps)}{' and others' if len(gaps) > 6 else ''}.")
                pdf.ln(1)
    else:
        pdf.multi_cell(0, 5, "- No significant gaps identified between resume and job requirements.")
        pdf.ln(1)

    if comp_details['similar']:
        similar_text = ', '.join(comp_details['similar'][:3])
        pdf.multi_cell(0, 5, f"- Experience with {similar_text} could be rephrased to better mirror job description terminology.")
        pdf.ln(1)

    pdf.ln(4)

    # Resume Optimization Guidance Section Header
    pdf.set_fill_color(239, 246, 224)  # Beige background
    pdf.rect(10, pdf.get_y(), 190, 8, 'F')
    pdf.set_text_color(18, 69, 89)  # Dark Teal text
    pdf.set_font("Arial", 'B', size=14)
    pdf.cell(0, 8, "Resume Optimization Guidance", ln=True)
    pdf.set_text_color(1, 22, 30)  # Ink Black
    pdf.ln(2)

    # Target intro text
    if result['score'] >= 90:
        target_text = "maintain your strong position"
    elif result['score'] >= 80:
        target_text = "push your match score closer to 95%"
    elif result['score'] >= 70:
        target_text = "strengthen your alignment to 85-90%"
    else:
        target_text = "significantly improve your match score"

    pdf.set_font("Arial", 'I', size=10)
    pdf.set_text_color(18, 69, 89)  # Dark Teal for intro text
    pdf.multi_cell(0, 5, f"To {target_text}, update your resume with the following enhancements:")
    pdf.set_text_color(1, 22, 30)  # Ink Black
    pdf.ln(2)

    # Optimization bullets with colored numbers
    pdf.set_font("Arial", size=10)
    if isinstance(suggestions, dict) and 'optimization_points' in suggestions:
        for i, point in enumerate(suggestions['optimization_points'], 1):
            # Add colored bullet point
            pdf.set_text_color(89, 131, 146)  # Air Force Blue for numbers
            pdf.set_font("Arial", 'B', size=10)
            pdf.cell(8, 5, f"{i}.", 0, 0)
            pdf.set_text_color(1, 22, 30)  # Ink Black for text
            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 5, point)
            pdf.ln(1)
    else:
        pdf.multi_cell(0, 5, "Continue to refine your resume to match job description terminology and requirements.")

    # Footer with subtle branding
    pdf.ln(5)
    pdf.set_y(-25)
    pdf.set_fill_color(174, 195, 176)  # Ash Grey background
    pdf.rect(0, pdf.get_y(), 210, 25, 'F')
    pdf.set_text_color(18, 69, 89)  # Dark Teal text
    pdf.set_font("Arial", 'I', size=9)
    pdf.cell(0, 10, "Generated by RoleIQ - AI Resume Matcher", 0, 0, 'C')

    pdf_output = "analysis_report.pdf"
    pdf.output(pdf_output)
    with open(pdf_output, "rb") as f:
        pdf_bytes = f.read()
    st.download_button(
        "📥 Download PDF Report",
        pdf_bytes,
        file_name="roleiq_analysis.pdf",
        mime="application/pdf"
    )

    # Track successful analysis completion
    track_event('analysis_complete', {
        'match_score': result['score'],
        'has_gaps': len(result['comp_details']['gaps']) > 0,
        'resume_file_type': os.path.splitext(resume_file.name)[1]
    }, GA_MEASUREMENT_ID)

    # Track PDF download availability (actual download can't be tracked with st.download_button)
    track_event('pdf_download', {
        'match_score': result['score']
    }, GA_MEASUREMENT_ID)

    # Mark analysis as complete to show "Analyze Another" button
    st.session_state.analysis_complete = True

    # Cleanup temp files
    try:
        if os.path.exists(temp_resume_path):
            os.remove(temp_resume_path)
        if jd_file and os.path.exists(jd_input):
            os.remove(jd_input)
        if os.path.exists(pdf_output):
            os.remove(pdf_output)
    except Exception:
        pass  # Silently ignore cleanup errors
