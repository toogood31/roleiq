import streamlit as st
from utils.matcher import match_resume_jd
from utils.optimizer import generate_suggestions
from utils.parser import parse_document
from utils.analytics import track_event
from utils.auth import (
    initialize_session_state, is_authenticated,
    can_perform_analysis, increment_analysis_count
)
from utils.auth_ui import (
    show_landing_page, show_auth_form, show_user_menu
)
from utils.database import save_analysis, save_job_description
import os
from dotenv import load_dotenv
from fpdf import FPDF  # For PDF generation
import streamlit.components.v1 as components
import plotly.graph_objects as go

# Load environment variables
load_dotenv()

# Secret admin access - check for admin query parameter
# Key is now stored in .env file, not in code
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY")
query_params = st.query_params
if ADMIN_SECRET_KEY and query_params.get("admin") == ADMIN_SECRET_KEY:
    # Load and run the analytics dashboard using safe import
    import importlib.util
    analytics_path = "_pages_backup/_Analytics.py"
    if os.path.exists(analytics_path):
        spec = importlib.util.spec_from_file_location("analytics", analytics_path)
        analytics_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(analytics_module)
        st.stop()
    else:
        st.error("Analytics dashboard not found.")
        st.stop()

# ============= COLOR SCHEME CONFIGURATION =============
# Logo-matched colors (RoleSynch branding)
# To revert to original colors, swap the commented sections below

# CURRENT: Logo-matched color scheme
PRIMARY_DARK = "#1E3A5F"       # Dark navy/slate blue (from logo)
ACCENT_CYAN = "#00D4FF"        # Bright cyan/blue (from logo)
TEXT_DARK = "#1E3A5F"          # Dark navy for text
TEXT_WHITE = "#FFFFFF"         # White text
BACKGROUND_LIGHT = "#F8FAFC"   # Light grey background

# RGB versions for PDF (FPDF uses RGB tuples)
BG_HEADER_RGB = (30, 58, 95)        # Dark navy for PDF headers
ACCENT_CYAN_RGB = (0, 212, 255)     # Bright cyan for PDF accents
TEXT_DARK_RGB = (30, 58, 95)        # Dark navy for PDF text
BACKGROUND_LIGHT_RGB = (248, 250, 252)  # Light grey for PDF backgrounds

# Semantic colors (status indicators - keeping original for clarity)
SUCCESS_GREEN = "#10b981"
SUCCESS_GREEN_RGB = (16, 185, 129)
WARNING_ORANGE = "#f59e0b"
WARNING_ORANGE_RGB = (245, 158, 11)
ERROR_RED = "#ef4444"
ERROR_RED_RGB = (239, 68, 68)

# ORIGINAL: Previous color scheme (uncomment to revert, comment out CURRENT section above)
# PRIMARY_DARK = "#0A2540"       # Deep Navy
# ACCENT_CYAN = "#635BFF"        # Stripe Blue
# TEXT_DARK = "#0F172A"          # Dark Slate
# TEXT_WHITE = "#FFFFFF"
# BACKGROUND_LIGHT = "#F8FAFC"
# BG_HEADER_RGB = (10, 37, 64)
# ACCENT_CYAN_RGB = (99, 91, 255)
# TEXT_DARK_RGB = (15, 23, 42)
# BACKGROUND_LIGHT_RGB = (248, 250, 252)
# SUCCESS_GREEN = "#10b981"
# SUCCESS_GREEN_RGB = (16, 185, 129)
# WARNING_ORANGE = "#f59e0b"
# WARNING_ORANGE_RGB = (245, 158, 11)
# ERROR_RED = "#ef4444"
# ERROR_RED_RGB = (239, 68, 68)
# ======================================================

# Initialize authentication session state
initialize_session_state()

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

# Show sidebar with user menu for authenticated users, hide for unauthenticated users
if is_authenticated():
    show_user_menu()
else:
    hide_sidebar_css = """
    <style>
        [data-testid="stSidebar"] {
            display: none;
        }
    </style>
    """
    st.markdown(hide_sidebar_css, unsafe_allow_html=True)

# Display logo next to title in a clean layout
logo_path = "LOGO.png"
if os.path.exists(logo_path):
    # Create columns for logo and title alignment
    col_logo, col_title = st.columns([1, 5])

    with col_logo:
        st.image(logo_path, width=80)

    with col_title:
        # Use markdown for better vertical alignment with the logo
        st.markdown(f"<h1 style='margin-top: 10px; color: {PRIMARY_DARK};'>RoleSynch: AI Resume Matcher</h1>", unsafe_allow_html=True)
else:
    st.title("RoleSynch: AI Resume Matcher")

# Check authentication - show landing page for unauthenticated users
if not is_authenticated():
    # Show auth form FIRST (at top) if user clicked Sign In or Sign Up
    # This ensures the form appears at the top of the page
    if st.session_state.get('show_auth'):
        show_auth_form()
        st.markdown("---")

    show_landing_page()

    # Only show auth form at bottom if no form is active (initial landing state)
    if not st.session_state.get('show_auth'):
        show_auth_form()
    st.stop()

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

    # Check if user has selected a saved resume
    if 'selected_resume' in st.session_state and st.session_state.selected_resume:
        st.info(f"📄 Using saved resume: {st.session_state.selected_resume['filename']}")
        if st.button("Clear Selection", key="clear_resume_selection"):
            del st.session_state.selected_resume
            st.rerun()

    resume_file = st.file_uploader("(PDF or DOCX)", type=["pdf", "docx"], key="resume_uploader")
    # File validation feedback
    if resume_file:
        file_size = len(resume_file.getvalue()) / 1024  # KB
        st.success(f"✓ {resume_file.name} ({file_size:.1f} KB)")

        # Add Save Resume button
        if st.button("💾 Save Resume", key="save_resume_btn"):
            from utils.database import save_resume

            success, message, resume_id = save_resume(
                resume_file.name,
                resume_file.getvalue(),
                os.path.splitext(resume_file.name)[1]
            )

            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

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

# Determine if we have a resume (either uploaded or selected)
has_resume = resume_file or ('selected_resume' in st.session_state and st.session_state.selected_resume)

if st.button("Analyze", key="analyze_btn") and has_resume:
    # Check if user can perform analysis (has free trials remaining)
    can_analyze, message = can_perform_analysis()
    if not can_analyze:
        st.error(message)
        st.stop()

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

        # Determine resume source and prepare temp file
        if resume_file:
            # Use uploaded resume
            resume_ext = os.path.splitext(resume_file.name)[1]
            temp_resume_path = f"temp_resume{resume_ext}"
            with open(temp_resume_path, "wb") as f:
                f.write(resume_file.getvalue())
            resume_filename = resume_file.name
        else:
            # Use saved resume from session state
            from utils.database import update_resume_last_used

            saved_resume = st.session_state.selected_resume
            resume_ext = saved_resume['file_type']
            temp_resume_path = f"temp_resume{resume_ext}"
            with open(temp_resume_path, "wb") as f:
                f.write(saved_resume['file_content'])
            resume_filename = saved_resume['filename']

            # Update last_used timestamp
            update_resume_last_used(saved_resume['id'])

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
            result['competency_details']['gaps'],
            result['competency_details']['similar'],
            result['seniority_analysis'],
            result['competency_details']['matches'],
            result['score'],
            result.get('industries', None),
            result.get('enhanced_analysis', None),
            result.get('field_mismatch', None)  # CRITICAL: Pass field mismatch data
        )

        # Step 5: Finalizing report
        progress_text.text("✅ Finalizing report...")
        progress_bar.progress(100)

        # Clear progress indicators
        progress_text.empty()
        progress_bar.empty()

        # Store results in session state to persist across reruns
        st.session_state.analysis_result = result
        st.session_state.analysis_suggestions = suggestions
        st.session_state.resume_file_type = resume_ext
        st.session_state.analysis_complete = True

        # Increment analysis count and decrement free trials
        increment_analysis_count()

        # Generate RoleIQ PDF report for storage
        from utils.roleiq_pdf import generate_roleiq_pdf

        # Extract detailed data for PDF generation
        comp_details = result.get('competency_details', {})

        # Extract experience analysis details
        exp_val = result.get('enhanced_analysis', {}).get('experience_validation', {})
        resume_years = exp_val.get('resume_years', 0)
        min_required = exp_val.get('min_required', '0')

        # Format min_required for display
        if min_required is not None and min_required != 0:
            years_required_str = f"{min_required}+"
        else:
            years_required_str = "0"

        # Build skill match table for PDF
        skill_match_table = []
        # Add matched skills first
        for skill in comp_details.get('matches', []):
            skill_match_table.append({'skill': skill, 'match': 'YES'})
        # Then add gap skills
        for skill in comp_details.get('gaps', []):
            skill_match_table.append({'skill': skill, 'match': 'NO'})

        pdf_analysis_data = {
            'score': result['score'],
            'summary': suggestions.get('summary', 'Analysis complete.') if isinstance(suggestions, dict) else 'Analysis complete.',
            'skill_matches': comp_details.get('matches', []),
            'skill_gaps': comp_details.get('gaps', []),
            'related_skills': comp_details.get('similar', []),
            'years_resume': resume_years,
            'years_required': years_required_str,
            'skill_match_table': skill_match_table,
            'related_skills_list': comp_details.get('similar', []),
            'recommendations': suggestions.get('optimization_points', []) if isinstance(suggestions, dict) else []
        }

        pdf_bytes = generate_roleiq_pdf(pdf_analysis_data)
        if pdf_bytes:
            # Cache PDF bytes in session state to avoid regeneration during display
            st.session_state.cached_pdf_bytes = pdf_bytes

        # Save analysis to database with PDF
        jd_filename = jd_file.name if jd_file else "Text Input"
        save_analysis(
            resume_filename=resume_filename,
            jd_filename=jd_filename,
            similarity_score=result['score'],
            results_dict=pdf_analysis_data,  # Pass the same structured data used for PDF
            pdf_bytes=pdf_bytes
        )

        # Save job description to database for analytics
        jd_content = result.get('jd_content', '')
        jd_skills_extracted = result.get('jd_skills_extracted', [])
        if jd_content:
            save_job_description(
                filename=jd_filename,
                content=jd_content,
                extracted_skills=jd_skills_extracted
            )

        # Cleanup temp analysis files
        try:
            if os.path.exists(temp_resume_path):
                os.remove(temp_resume_path)
            if jd_file and os.path.exists(jd_input):
                os.remove(jd_input)
        except Exception:
            pass  # Silently ignore cleanup errors

    except Exception as e:
        st.error(f"An error occurred during analysis: {str(e)}")
        # Cleanup temp files on error
        if os.path.exists(temp_resume_path):
            os.remove(temp_resume_path)
        if jd_file and 'temp_jd_path' in locals() and os.path.exists(temp_jd_path):
            os.remove(temp_jd_path)
        st.stop()

# Display results from session state (persists across reruns like PDF download)
if st.session_state.get('analysis_complete', False):
    result = st.session_state.analysis_result
    suggestions = st.session_state.analysis_suggestions

    st.success("Analysis Complete!")
    st.markdown("<hr>", unsafe_allow_html=True)

    # Match Score - Circular Gauge Chart
    score_value = result['score']

    # Determine color based on score
    if score_value >= 80:
        color = "#00cc66"  # Green
    elif score_value >= 60:
        color = "#ffaa00"  # Orange
    else:
        color = "#ff4444"  # Red

    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score_value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Match Score", 'font': {'size': 24, 'color': TEXT_DARK}},
        number = {'suffix': "%", 'font': {'size': 48, 'color': color}},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': TEXT_DARK},
            'bar': {'color': color, 'thickness': 0.75},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#E0E0E0",
            'steps': [
                {'range': [0, 60], 'color': '#FFE5E5'},
                {'range': [60, 80], 'color': '#FFF4E0'},
                {'range': [80, 100], 'color': '#E5FFE5'}
            ],
            'threshold': {
                'line': {'color': TEXT_DARK, 'width': 4},
                'thickness': 0.75,
                'value': score_value
            }
        }
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=20, r=40, t=60, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={'family': "Arial, sans-serif"}
    )

    # Center the gauge
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.plotly_chart(fig, use_container_width=True)

    # Save gauge chart as image for PDF (optional - PDF uses its own gauge)
    gauge_image_path = "temp_gauge.png"
    try:
        fig.write_image(gauge_image_path, width=600, height=300)
    except Exception as e:
        # Kaleido/browser issues shouldn't crash the app - PDF has its own gauge chart
        print(f"Warning: Could not save gauge image: {e}")

    st.markdown("")
    st.markdown("")

    # Executive Summary with styled header
    st.markdown("""
    <div style="background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
                padding: 15px 20px;
                border-radius: 8px;
                margin-bottom: 20px;">
        <h2 style="color: white; margin: 0; font-size: 1.5em;">📋 Executive Summary</h2>
    </div>
    """, unsafe_allow_html=True)

    if isinstance(suggestions, dict) and 'summary' in suggestions:
        st.markdown(f"""
        <div style="background-color: #f8f9fa;
                    padding: 20px;
                    border-left: 4px solid #6366f1;
                    border-radius: 4px;
                    margin-bottom: 30px;">
            <p style="font-size: 1.05em; line-height: 1.7; margin: 0; color: #1f2937;">
                {suggestions['summary']}
            </p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("")

    # Role Fit Analysis - Structured like the example
    st.markdown("""
    <div style="background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
                padding: 15px 20px;
                border-radius: 8px;
                margin-bottom: 25px;">
        <h2 style="color: white; margin: 0; font-size: 1.5em;">🎯 Role Fit Analysis</h2>
    </div>
    """, unsafe_allow_html=True)

    comp_details = result['competency_details']
    field_mismatch = result.get('field_mismatch', {})

    # CRITICAL: If there's a CRITICAL field mismatch, show different messaging
    if field_mismatch.get('severity') == 'CRITICAL':
        st.markdown("""
        <div style="background-color: #fef2f2;
                    padding: 20px;
                    border-left: 4px solid #ef4444;
                    border-radius: 4px;
                    margin-bottom: 25px;">
            <h3 style="color: #991b1b; margin-top: 0;">⚠️ Professional Field Alignment</h3>
        </div>
        """, unsafe_allow_html=True)
        st.write(f"• {field_mismatch.get('explanation', 'This role is in a different professional field.')}")
        st.markdown("")
        st.write("• Focus on roles within your current professional field for the best match.")
        st.markdown("")
        st.write("• If transitioning fields, seek hybrid roles or gain foundational credentials first.")
        st.markdown("")
        st.markdown("")
    else:
        # Normal role fit analysis

        # VISUAL METRICS CARDS - Dashboard-style skill overview
        st.markdown("""
        <h3 style="color: #374151; margin-bottom: 15px;">📊 Skills Analysis Overview</h3>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)

        match_count = len(comp_details.get('matches', []))
        gap_count = len(comp_details.get('gaps', []))
        similar_count = len(comp_details.get('similar', []))

        with col1:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                        padding: 20px;
                        border-radius: 10px;
                        text-align: center;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h2 style="color: white; margin: 0; font-size: 2.5em;">{match_count}</h2>
                <p style="color: #f0fdf4; margin: 5px 0 0 0; font-size: 0.9em;">Skills Matched</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                        padding: 20px;
                        border-radius: 10px;
                        text-align: center;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h2 style="color: white; margin: 0; font-size: 2.5em;">{gap_count}</h2>
                <p style="color: #fef2f2; margin: 5px 0 0 0; font-size: 0.9em;">Skill Gaps</p>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                        padding: 20px;
                        border-radius: 10px;
                        text-align: center;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h2 style="color: white; margin: 0; font-size: 2.5em;">{similar_count}</h2>
                <p style="color: #fefce8; margin: 5px 0 0 0; font-size: 0.9em;">Related Skills</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")
        st.markdown("")

        # Experience Analysis
        if 'enhanced_analysis' in result and 'experience_validation' in result['enhanced_analysis']:
            exp_val = result['enhanced_analysis']['experience_validation']

            st.write("**Experience Analysis:**")
            st.markdown("")

            # Display experience comparison
            resume_years = exp_val.get('resume_years', 0)
            min_required = exp_val.get('min_required')
            meets_minimum = exp_val.get('meets_minimum', False)
            overqualified = exp_val.get('overqualified', False)

            if min_required is not None:
                col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 1])

                with col_exp1:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
                                padding: 15px;
                                border-radius: 10px;
                                text-align: center;
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <h3 style="color: white; margin: 0; font-size: 1.8em;">{resume_years}</h3>
                        <p style="color: #e0e7ff; margin: 5px 0 0 0; font-size: 0.85em;">Years on Resume</p>
                    </div>
                    """, unsafe_allow_html=True)

                with col_exp2:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
                                padding: 15px;
                                border-radius: 10px;
                                text-align: center;
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <h3 style="color: white; margin: 0; font-size: 1.8em;">{min_required}+</h3>
                        <p style="color: #ede9fe; margin: 5px 0 0 0; font-size: 0.85em;">Years Required</p>
                    </div>
                    """, unsafe_allow_html=True)

                with col_exp3:
                    # Determine icon and color based on experience match
                    if meets_minimum:
                        icon = "✓"
                        bg_color = "linear-gradient(135deg, #10b981 0%, #059669 100%)"
                        text_color = "#f0fdf4"
                        status_text = "Meets Requirement"
                    else:
                        gap = min_required - resume_years
                        icon = "⚠"
                        bg_color = "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)"
                        text_color = "#fefce8"
                        status_text = f"{gap} Year Gap"

                    st.markdown(f"""
                    <div style="background: {bg_color};
                                padding: 15px;
                                border-radius: 10px;
                                text-align: center;
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <h3 style="color: white; margin: 0; font-size: 1.8em;">{icon}</h3>
                        <p style="color: {text_color}; margin: 5px 0 0 0; font-size: 0.85em;">{status_text}</p>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("")

                # Provide contextual analysis
                if overqualified:
                    st.write(f"• **Overqualified:** You have {resume_years} years of experience for a role requiring {min_required}+ years. This positions you as a highly experienced candidate, though you may need to address potential overqualification concerns.")
                elif meets_minimum:
                    st.write(f"• **Experience Match:** Your {resume_years} years of experience meets the {min_required}+ year requirement, positioning you as a qualified candidate for this role.")
                else:
                    gap = min_required - resume_years
                    if gap >= 3:
                        st.write(f"• **Significant Experience Gap:** The role requires {min_required}+ years, but your resume shows {resume_years} years ({gap} year gap). This may significantly impact your candidacy. Consider highlighting transferable experience or targeting roles better aligned with your experience level.")
                    else:
                        st.write(f"• **Moderate Experience Gap:** You have {resume_years} years vs. {min_required}+ years required ({gap} year gap). Emphasize relevant accomplishments and rapid skill development to bridge this gap.")

                st.markdown("")
            else:
                st.write(f"• **Experience on Resume:** {resume_years} years of relevant professional experience identified.")
                st.markdown("")

        st.markdown("<hr>", unsafe_allow_html=True)

        # Where Resume Aligns Well WITH SKILL TAGS
        st.write("**Where the Resume Aligns Well (✔️):**")
        st.markdown("")

        if comp_details['matches']:
            matches = comp_details['matches']
            if len(matches) > 0:
                # First bullet: primary skill matches with context
                if len(matches) >= 3:
                    st.write(f"• **Core Competency Alignment ({match_count} skills matched):** Your resume demonstrates direct experience in key requirements for this role. This positions you as a strong candidate with the technical foundation needed.")
                    st.markdown("")
                elif len(matches) == 2:
                    st.write(f"• **Key Skill Match ({match_count} skills):** You have demonstrated experience in critical requirements for this position.")
                    st.markdown("")
                elif len(matches) == 1:
                    st.write(f"• **Primary Skill Match:** Your proven capability directly addresses a core job requirement, though additional skill development may strengthen your candidacy.")
                    st.markdown("")

                # Display matched skills as green tags
                st.markdown("**Matched Skills:**")
                skill_tags_html = ""
                for skill in matches:
                    skill_tags_html += f'<span style="display: inline-block; background-color: #10b981; color: white; padding: 6px 12px; margin: 4px; border-radius: 6px; font-size: 0.9em; font-weight: 500;">{skill}</span> '
                st.markdown(skill_tags_html, unsafe_allow_html=True)
                st.markdown("")
        else:
            st.write("• **Limited Keyword Overlap:** Your resume shows few direct skill matches with this job description. Consider either (1) rephrasing your experience to mirror the JD terminology, or (2) targeting roles more aligned with your background.")
            st.markdown("")

        # Add contextual strength assessment based on score
        score = result['score']
        if score >= 80:
            st.write("• **Strong Positioning:** Your background aligns well with this role's requirements, making you a competitive candidate. Focus optimization on closing remaining gaps.")
        elif score >= 60:
            st.write("• **Moderate Fit:** You have foundational qualifications for this role, but strengthening key areas will significantly improve your candidacy.")
        else:
            st.write("• **Development Opportunity:** While you have some relevant experience, substantial gaps suggest this role may be a stretch. Consider roles that better leverage your current expertise or invest in upskilling.")
        st.markdown("")

        # Where Resume Does Not Fully Align WITH SKILL TAGS
        st.markdown("")
        st.write("**Where the Resume Does Not Fully Align (⚠️):**")
        st.markdown("")

        if comp_details['gaps']:
            gaps = comp_details['gaps']

            # Priority gaps with strategic guidance
            if len(gaps) >= 3:
                st.write(f"• **Critical Skill Gaps ({gap_count} missing):** The job description explicitly requires skills which are not prominently featured on your resume. These gaps may significantly impact your candidacy. Priority action: Add examples demonstrating these skills or explain how your experience translates to these requirements.")
                st.markdown("")
            elif len(gaps) == 2:
                st.write(f"• **Key Missing Requirements ({gap_count} gaps):** Your resume does not explicitly mention requirements which appear in the job description. Consider adding specific examples or rephrasing existing experience to address these areas.")
                st.markdown("")
            elif len(gaps) == 1:
                st.write(f"• **Single Gap Identified:** The role requires a skill which is not clearly evident on your resume. While this may not be a dealbreaker, addressing it could strengthen your application.")
                st.markdown("")

            # Display gap skills as red tags
            st.markdown("**Missing Skills:**")
            skill_tags_html = ""
            for skill in gaps:
                skill_tags_html += f'<span style="display: inline-block; background-color: #ef4444; color: white; padding: 6px 12px; margin: 4px; border-radius: 6px; font-size: 0.9em; font-weight: 500;">{skill}</span> '
            st.markdown(skill_tags_html, unsafe_allow_html=True)
            st.markdown("")
        else:
            st.write("• **Comprehensive Coverage:** Your resume addresses all major requirements from the job description. Focus on refining presentation and quantifying impact.")
            st.markdown("")

        # Similar skills with actionable guidance AND SKILL TAGS
        if comp_details['similar']:
            similar_count = len(comp_details['similar'])
            if similar_count <= 3:
                st.write(f"• **Terminology Alignment Opportunity:** You have experience which relates to JD requirements but uses different wording. Mirror the job description's exact language to improve ATS matching.")
            else:
                st.write(f"• **Multiple Terminology Gaps ({similar_count} skills):** Your experience is relevant but phrased differently than the JD. Update your resume to use the employer's preferred terms for stronger keyword alignment.")

            # Display similar skills as orange/yellow tags
            st.markdown("**Related Skills (Consider Rewording):**")
            skill_tags_html = ""
            for skill in comp_details['similar']:
                skill_tags_html += f'<span style="display: inline-block; background-color: #f59e0b; color: white; padding: 6px 12px; margin: 4px; border-radius: 6px; font-size: 0.9em; font-weight: 500;">{skill}</span> '
            st.markdown(skill_tags_html, unsafe_allow_html=True)
            st.markdown("")
    
        st.markdown("<hr>", unsafe_allow_html=True)
    
    # Resume Optimization Guidance with styled header
    st.markdown("""
    <div style="background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
                padding: 15px 20px;
                border-radius: 8px;
                margin-bottom: 25px;
                margin-top: 30px;">
        <h2 style="color: white; margin: 0; font-size: 1.5em;">💡 Resume Optimization Guidance</h2>
    </div>
    """, unsafe_allow_html=True)

    if result['score'] >= 90:
        target_text = "maintain your strong position"
    elif result['score'] >= 80:
        target_text = "push your match score closer to 95%"
    elif result['score'] >= 70:
        target_text = "strengthen your alignment to 85-90%"
    else:
        target_text = "significantly improve your match score"

    st.markdown(f"""
    <div style="background-color: #f8f9fa;
                padding: 15px 20px;
                border-left: 4px solid #6366f1;
                border-radius: 4px;
                margin-bottom: 20px;">
        <p style="font-size: 1.0em; font-style: italic; margin: 0; color: #4b5563;">
            To {target_text}, update your resume with the following enhancements:
        </p>
    </div>
    """, unsafe_allow_html=True)

    if isinstance(suggestions, dict) and 'optimization_points' in suggestions:
        for i, point in enumerate(suggestions['optimization_points'], 1):
            st.markdown(f"""
            <div style="background-color: #ffffff;
                        padding: 15px 20px;
                        margin-bottom: 12px;
                        border-left: 3px solid #6366f1;
                        border-radius: 4px;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <p style="margin: 0; color: #1f2937; line-height: 1.6;">
                    <span style="color: #6366f1; font-weight: bold; margin-right: 8px;">{i}.</span>{point}
                </p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.write("Continue to refine your resume to match job description terminology and requirements.")

    # Generate PDF using the RoleIQ PDF generator
    from utils.roleiq_pdf import generate_roleiq_pdf

    # Extract experience analysis details
    exp_val = result.get('enhanced_analysis', {}).get('experience_validation', {})
    resume_years = exp_val.get('resume_years', 0)
    min_required = exp_val.get('min_required', '0')

    # Format min_required for display
    if min_required is not None and min_required != 0:
        years_required_str = f"{min_required}+"
    else:
        years_required_str = "0"

    # Build skill match table for PDF
    skill_match_table = []
    # Add matched skills first
    for skill in comp_details.get('matches', []):
        skill_match_table.append({'skill': skill, 'match': 'YES'})
    # Then add gap skills
    for skill in comp_details.get('gaps', []):
        skill_match_table.append({'skill': skill, 'match': 'NO'})

    # Build analysis data structure for RoleIQ PDF
    analysis_data = {
        'score': result['score'],
        'summary': suggestions.get('summary', 'Analysis complete.') if isinstance(suggestions, dict) else 'Analysis complete.',
        'skill_matches': comp_details.get('matches', []),
        'skill_gaps': comp_details.get('gaps', []),
        'related_skills': comp_details.get('similar', []),
        'years_resume': resume_years,
        'years_required': years_required_str,
        'skill_match_table': skill_match_table,
        'related_skills_list': comp_details.get('similar', []),
        'recommendations': suggestions.get('optimization_points', []) if isinstance(suggestions, dict) else []
    }

    # Use cached PDF if available, otherwise generate it
    pdf_bytes = st.session_state.get('cached_pdf_bytes')
    if pdf_bytes is None:
        pdf_bytes = generate_roleiq_pdf(analysis_data)

    # Provide download button
    if pdf_bytes:
        st.download_button(
            "📥 Download PDF Report",
            pdf_bytes,
            file_name="roleiq_analysis.pdf",
            mime="application/pdf"
        )
    else:
        st.error("Failed to generate PDF. Please try again.")

    # Track successful analysis completion (only on first run, not on reruns)
    if not st.session_state.get('tracking_sent', False):
        track_event('analysis_complete', {
            'match_score': result['score'],
            'has_gaps': len(result['competency_details']['gaps']) > 0,
            'resume_file_type': st.session_state.get('resume_file_type', '.pdf')
        }, GA_MEASUREMENT_ID)
        st.session_state.tracking_sent = True

    # Track PDF download availability (actual download can't be tracked with st.download_button)
    if not st.session_state.get('pdf_tracking_sent', False):
        track_event('pdf_download', {
            'match_score': result['score']
        }, GA_MEASUREMENT_ID)
        st.session_state.pdf_tracking_sent = True

    # Cleanup temp PDF files (only these are created in display block)
    try:
        if os.path.exists("analysis_report.pdf"):
            os.remove("analysis_report.pdf")
        if os.path.exists("gauge_chart.png"):
            os.remove("gauge_chart.png")
    except Exception:
        pass  # Silently ignore cleanup errors

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; font-style: italic;'>RoleSynch by TooGood</p>", unsafe_allow_html=True)
