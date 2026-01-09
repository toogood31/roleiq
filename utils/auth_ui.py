"""
Authentication UI Components for RoleSynch
Handles sign-in, sign-up, and landing page displays
"""

import streamlit as st
from utils.auth import (
    sign_in, sign_up, sign_out, is_authenticated,
    get_current_user, initialize_session_state
)


def show_landing_page():
    """Display the landing page for unauthenticated users"""

    # Hero Section
    st.markdown("""
    <div style='text-align: center; padding: 3rem 1rem;'>
        <h1 style='font-size: 3rem; color: #1E3A5F; margin-bottom: 1rem;'>
            Find Your Perfect Job Match with AI
        </h1>
        <p style='font-size: 1.25rem; color: #64748b; max-width: 700px; margin: 0 auto 2rem auto;'>
            RoleSynch uses advanced AI to analyze your resume against job descriptions,
            giving you instant insights and recommendations to land your dream role.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # CTA Buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Get Started Free", key="cta_signup", use_container_width=True):
                st.session_state.show_auth = "signup"
                st.rerun()
        with col_b:
            if st.button("Sign In", key="cta_signin", use_container_width=True, type="secondary"):
                st.session_state.show_auth = "signin"
                st.rerun()

    # Features Section
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("### Why Choose RoleSynch?")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        #### AI-Powered Analysis
        Get instant, detailed insights on how well your resume matches job descriptions.
        """)

    with col2:
        st.markdown("""
        #### Smart Recommendations
        Receive personalized suggestions to improve your resume for each role.
        """)

    with col3:
        st.markdown("""
        #### Track Your Progress
        Save and review all your past analyses in one place.
        """)

    # Free Trial Info
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("Start with 3 free resume analyses. No credit card required.")


def show_auth_form():
    """Display sign-in or sign-up form based on session state"""

    # Initialize session state
    if 'show_auth' not in st.session_state:
        st.session_state.show_auth = None

    if st.session_state.show_auth == "signin":
        show_signin_form()
    elif st.session_state.show_auth == "signup":
        show_signup_form()


def show_signin_form():
    """Display the sign-in form"""

    st.markdown("### Sign In to RoleSynch")

    with st.form("signin_form"):
        email = st.text_input("Email", key="signin_email")
        password = st.text_input("Password", type="password", key="signin_password")

        col1, col2 = st.columns([1, 1])
        with col1:
            submit = st.form_submit_button("Sign In", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("Cancel", use_container_width=True, type="secondary")

        if submit:
            if email and password:
                success, message, user_data = sign_in(email, password)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Please enter both email and password")

        if cancel:
            st.session_state.show_auth = None
            st.rerun()

    # Link to sign up
    st.markdown("Don't have an account?")
    if st.button("Create Account", key="switch_to_signup"):
        st.session_state.show_auth = "signup"
        st.rerun()


def show_signup_form():
    """Display the sign-up form"""

    st.markdown("### Create Your Free Account")

    with st.form("signup_form"):
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password (min 6 characters)", type="password", key="signup_password")
        password_confirm = st.text_input("Confirm Password", type="password", key="signup_password_confirm")

        col1, col2 = st.columns([1, 1])
        with col1:
            submit = st.form_submit_button("Create Account", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("Cancel", use_container_width=True, type="secondary")

        if submit:
            if email and password and password_confirm:
                if password != password_confirm:
                    st.error("Passwords do not match")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    success, message, user_data = sign_up(email, password)
                    if success:
                        st.success(message)
                        st.info("You can now sign in with your email and password.")
                        st.session_state.show_auth = "signin"
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.warning("Please fill in all fields")

        if cancel:
            st.session_state.show_auth = None
            st.rerun()

    # Link to sign in
    st.markdown("Already have an account?")
    if st.button("Sign In", key="switch_to_signin"):
        st.session_state.show_auth = "signin"
        st.rerun()


def show_user_menu():
    """Display user menu for authenticated users"""
    from utils.database import get_user_resumes, delete_resume
    import base64

    user = get_current_user()
    if not user:
        return

    with st.sidebar:
        st.markdown(f"**Signed in as:**")
        st.markdown(f"{user['email']}")

        # Show unlimited for admins
        if user.get('is_admin', False):
            st.markdown(f"**Free analyses remaining:** Unlimited (Admin)")
        else:
            st.markdown(f"**Free analyses remaining:** {user['free_trials_remaining']}")

        if st.button("Sign Out", key="signout_btn"):
            sign_out()
            st.rerun()

        st.markdown("---")

        # Create tabs for different sections
        tab1, tab2, tab3 = st.tabs(["Stats", "Resumes", "History"])

        with tab1:
            st.markdown("### Quick Stats")
            st.markdown(f"Total analyses: {user['analysis_count']}")

        with tab2:
            st.markdown("### Saved Resumes")

            # Get user's saved resumes
            resumes = get_user_resumes()

            if resumes:
                for resume in resumes:
                    # Display upload date
                    upload_date = resume.get('uploaded_at')
                    if upload_date:
                        date_str = upload_date.strftime("%m/%d/%Y")
                    else:
                        date_str = "N/A"

                    st.markdown(f"**{resume['filename']}** - *Uploaded: {date_str}*")

                    col1, col2, col3 = st.columns([2, 1, 1])

                    with col1:
                        # Make resume selectable
                        if st.button("Select", key=f"select_{resume['id']}", use_container_width=True):
                            # Store selected resume in session state
                            st.session_state.selected_resume = resume
                            st.toast(f"Selected: {resume['filename']}")

                    with col2:
                        # Download button
                        st.download_button(
                            label="⬇️",
                            data=resume['file_content'],
                            file_name=resume['filename'],
                            mime="application/octet-stream",
                            key=f"download_{resume['id']}",
                            use_container_width=True
                        )

                    with col3:
                        if st.button("❌", key=f"delete_{resume['id']}", use_container_width=True):
                            if delete_resume(resume['id']):
                                st.success("Deleted")
                                st.rerun()
                            else:
                                st.error("Error")

                    st.markdown("---")

                # Show selected resume info
                if 'selected_resume' in st.session_state:
                    st.success(f"✓ Using: {st.session_state.selected_resume['filename']}")
            else:
                st.info("No saved resumes yet. Upload a resume and click 'Save Resume' to store it for future analyses.")

        with tab3:
            st.markdown("### Analysis History")

            # Get user's analysis history
            from utils.database import get_user_analyses, delete_analysis

            analyses = get_user_analyses(limit=10)

            if analyses:
                # Show selected analysis details at the top if one is selected
                if 'selected_analysis' in st.session_state:
                    analysis = st.session_state.selected_analysis
                    st.markdown("#### 📋 Selected Analysis Details")
                    st.markdown(f"**Resume:** {analysis.get('resume_filename', 'Unknown')}")
                    st.markdown(f"**Job Description:** {analysis.get('jd_filename', 'Unknown')}")
                    st.markdown(f"**Overall Score:** {analysis.get('similarity_score', 0):.2f}%")

                    # Show skill match details
                    skill_match = analysis.get('skill_match', {})
                    if skill_match:
                        st.markdown("**Skill Match:**")
                        st.write(f"- Matched: {len(skill_match.get('matches', []))}")
                        st.write(f"- Missing: {len(skill_match.get('gaps', []))}")
                        st.write(f"- Similar: {len(skill_match.get('similar', []))}")

                    # Add PDF download button - regenerate PDF using RoleIQ format
                    col_a, col_b = st.columns([1, 1])
                    with col_a:
                        # Regenerate PDF using RoleIQ PDF generator (same as main analysis)
                        from utils.roleiq_pdf import generate_roleiq_pdf

                        # Get data directly from stored RoleIQ format (new analyses)
                        # or fallback to legacy skill_match format (old analyses)
                        skill_matches = analysis.get('skill_matches', [])
                        skill_gaps = analysis.get('skill_gaps', [])
                        related_skills = analysis.get('related_skills', [])

                        # Fallback to legacy format if new format is empty
                        if not skill_matches and not skill_gaps:
                            skill_match = analysis.get('skill_match', {})
                            skill_matches = skill_match.get('matches', [])
                            skill_gaps = skill_match.get('gaps', [])
                            related_skills = skill_match.get('similar', [])

                        # Get skill match table directly or build it
                        skill_match_table = analysis.get('skill_match_table', [])
                        if not skill_match_table:
                            for skill in skill_matches:
                                skill_match_table.append({'skill': skill, 'match': 'YES'})
                            for skill in skill_gaps:
                                skill_match_table.append({'skill': skill, 'match': 'NO'})

                        # Get experience data
                        years_resume = analysis.get('years_resume', 0)
                        years_required = analysis.get('years_required', '0')

                        # Get summary directly or build it
                        summary = analysis.get('summary', '')
                        if not summary:
                            summary = f"Analysis complete. {len(skill_matches)} matched skills, {len(skill_gaps)} skill gaps, and {len(related_skills)} related skills identified."

                        # Get recommendations
                        recommendations = analysis.get('recommendations', [])

                        # Build RoleIQ PDF data structure
                        roleiq_data = {
                            'score': analysis.get('similarity_score', 0),
                            'summary': summary,
                            'skill_matches': skill_matches,
                            'skill_gaps': skill_gaps,
                            'related_skills': related_skills,
                            'years_resume': years_resume,
                            'years_required': years_required,
                            'skill_match_table': skill_match_table,
                            'related_skills_list': related_skills,
                            'recommendations': recommendations
                        }

                        pdf_bytes = generate_roleiq_pdf(roleiq_data)
                        if not pdf_bytes:
                            # Fallback to stored PDF if regeneration fails
                            pdf_bytes = analysis.get('pdf_report')

                        if pdf_bytes:
                            st.download_button(
                                label="📥 Download Full Report (PDF)",
                                data=pdf_bytes,
                                file_name=f"RoleSynch_Analysis_{analysis.get('resume_filename', 'report').replace('.pdf', '').replace('.docx', '')}.pdf",
                                mime="application/pdf",
                                key="pdf_download_btn",
                                use_container_width=True
                            )
                        else:
                            st.warning("PDF report not available for this analysis")

                    with col_b:
                        if st.button("Close Details", key="close_details", use_container_width=True):
                            del st.session_state.selected_analysis
                            st.rerun()

                    st.markdown("---")

                # List all analyses
                for analysis in analyses:
                    # Display analysis date and score
                    analysis_date = analysis.get('timestamp')
                    if analysis_date:
                        date_str = analysis_date.strftime("%m/%d/%Y %I:%M %p")
                    else:
                        date_str = "N/A"

                    score = analysis.get('similarity_score', 0)

                    # Color code the score
                    if score >= 75:
                        score_color = "#10b981"  # Green
                    elif score >= 50:
                        score_color = "#f59e0b"  # Orange
                    else:
                        score_color = "#ef4444"  # Red

                    st.markdown(f"**{analysis.get('resume_filename', 'Unknown')}** vs **{analysis.get('jd_filename', 'Unknown')}**")
                    st.markdown(f"*{date_str}* - <span style='color: {score_color}; font-weight: bold;'>Score: {score:.2f}%</span>", unsafe_allow_html=True)

                    col1, col2 = st.columns([3, 1])

                    with col1:
                        # View details button
                        if st.button("View Details", key=f"view_{analysis['id']}", use_container_width=True):
                            st.session_state.selected_analysis = analysis
                            st.rerun()

                    with col2:
                        # Delete button
                        if st.button("❌", key=f"delete_analysis_{analysis['id']}", use_container_width=True):
                            if delete_analysis(analysis['id']):
                                st.success("Deleted")
                                st.rerun()
                            else:
                                st.error("Error")

                    st.markdown("---")
            else:
                st.info("No analysis history yet. Complete an analysis to see it here!")
