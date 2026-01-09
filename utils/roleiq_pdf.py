"""
RoleIQ-style PDF generator matching the reference format
"""
from fpdf import FPDF
import math


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


class RoleIQPDF(FPDF):
    """Custom PDF class for RoleIQ-style reports"""

    def header(self):
        """Add header with dark blue background and logo"""
        # Dark blue background bar
        self.set_fill_color(30, 58, 95)
        self.rect(0, 0, 210, 35, 'F')

        # Add logo in top right if it exists
        import os
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'LOGO.png')
        if os.path.exists(logo_path):
            self.image(logo_path, x=175, y=8, w=25)

        # Title text in white
        self.set_y(12)
        self.set_font("Arial", "B", 22)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "RoleSynch Analysis Report", ln=True, align="C")

        # Reset to normal
        self.set_y(40)
        self.set_text_color(0, 0, 0)


def draw_gauge_chart(pdf, x, y, width, score):
    """
    Draw a clean, modern semi-circular gauge chart.
    """
    # Calculate center and dimensions first
    center_x = x + width / 2
    arc_radius = width / 3.5
    arc_thickness = 5
    center_y = y + 18 + width / 4  # Lowered the gauge more

    # Draw "Match Score" label at the top (above the gauge and 50% label)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(50, 50, 50)
    label_text = "Match Score"
    label_width = pdf.get_string_width(label_text)
    pdf.set_xy(center_x - label_width / 2, y - 3)
    pdf.cell(label_width, 5, label_text, align='C')

    # Draw percentage labels with % symbol
    pdf.set_font("Arial", "", 6)
    pdf.set_text_color(120, 120, 120)

    label_radius = arc_radius + 8  # Position labels closer to the arc

    labels = [
        ("0%", 180),
        ("25%", 135),
        ("50%", 90),
        ("75%", 45),
        ("100%", 0)
    ]

    for label_text, degrees in labels:
        angle = math.radians(degrees)
        label_x = center_x + label_radius * math.cos(angle)
        label_y = center_y - label_radius * math.sin(angle)

        label_w = pdf.get_string_width(label_text)

        # Position adjustments for clean placement
        if degrees == 180:
            pdf.set_xy(label_x - label_w - 1, label_y - 1)
        elif degrees == 0:
            pdf.set_xy(label_x + 1, label_y - 1)
        elif degrees == 90:
            pdf.set_xy(label_x - label_w / 2, label_y - 4)
        elif degrees > 90:
            pdf.set_xy(label_x - label_w - 0.5, label_y - 3)
        else:
            pdf.set_xy(label_x + 0.5, label_y - 3)

        pdf.cell(label_w, 3, label_text, align='C')

    # Draw the gauge arc using filled polygons for a solid look
    inner_r = arc_radius - arc_thickness
    outer_r = arc_radius + arc_thickness
    num_segments = 100

    # Calculate score position
    score_segments = int(num_segments * (score / 100))

    # Draw background arc (light gray)
    pdf.set_fill_color(230, 230, 230)
    for i in range(num_segments):
        angle1 = math.pi - (i * math.pi / num_segments)
        angle2 = math.pi - ((i + 1) * math.pi / num_segments)

        # Create 4 points for the segment
        x1_inner = center_x + inner_r * math.cos(angle1)
        y1_inner = center_y - inner_r * math.sin(angle1)
        x1_outer = center_x + outer_r * math.cos(angle1)
        y1_outer = center_y - outer_r * math.sin(angle1)
        x2_inner = center_x + inner_r * math.cos(angle2)
        y2_inner = center_y - inner_r * math.sin(angle2)
        x2_outer = center_x + outer_r * math.cos(angle2)
        y2_outer = center_y - outer_r * math.sin(angle2)

        # Draw as filled polygon
        pdf.set_draw_color(230, 230, 230)
        pdf.set_line_width(0.1)

        # Draw filled trapezoid segment
        points = f"{x1_inner} {y1_inner} m {x1_outer} {y1_outer} l {x2_outer} {y2_outer} l {x2_inner} {y2_inner} l h f"

    # Draw colored filled arc (up to score)
    for i in range(score_segments):
        progress = i / num_segments

        # Color gradient: Red -> Yellow -> Green
        if progress < 0.4:
            t = progress / 0.4
            r, g, b = int(239), int(68 + 130 * t), int(68)
        elif progress < 0.7:
            t = (progress - 0.4) / 0.3
            r, g, b = int(239 - 30 * t), int(198 + 20 * t), int(68 - 30 * t)
        else:
            t = (progress - 0.7) / 0.3
            r, g, b = int(209 - 193 * t), int(218 + 12 * t), int(38 + 91 * t)

        angle1 = math.pi - (i * math.pi / num_segments)
        angle2 = math.pi - ((i + 1) * math.pi / num_segments)

        # Draw thick arc segment
        mid_angle = (angle1 + angle2) / 2
        for offset in range(-int(arc_thickness), int(arc_thickness) + 1):
            radius = arc_radius + offset * 0.5
            x1 = center_x + radius * math.cos(angle1)
            y1 = center_y - radius * math.sin(angle1)
            x2 = center_x + radius * math.cos(angle2)
            y2 = center_y - radius * math.sin(angle2)

            pdf.set_draw_color(r, g, b)
            pdf.set_line_width(0.6)
            pdf.line(x1, y1, x2, y2)

    # Draw clean arc edges
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.3)

    # Inner edge
    for i in range(num_segments):
        angle1 = math.pi - (i * math.pi / num_segments)
        angle2 = math.pi - ((i + 1) * math.pi / num_segments)
        x1 = center_x + inner_r * math.cos(angle1)
        y1 = center_y - inner_r * math.sin(angle1)
        x2 = center_x + inner_r * math.cos(angle2)
        y2 = center_y - inner_r * math.sin(angle2)
        pdf.line(x1, y1, x2, y2)

    # Outer edge
    for i in range(num_segments):
        angle1 = math.pi - (i * math.pi / num_segments)
        angle2 = math.pi - ((i + 1) * math.pi / num_segments)
        x1 = center_x + outer_r * math.cos(angle1)
        y1 = center_y - outer_r * math.sin(angle1)
        x2 = center_x + outer_r * math.cos(angle2)
        y2 = center_y - outer_r * math.sin(angle2)
        pdf.line(x1, y1, x2, y2)

    # Draw score percentage in center of the arc
    pdf.set_font("Arial", "B", 20)

    # Color based on score
    if score < 40:
        pdf.set_text_color(239, 68, 68)  # Red
    elif score < 70:
        pdf.set_text_color(245, 158, 11)  # Orange/Yellow
    else:
        pdf.set_text_color(16, 185, 129)  # Green

    score_text = f"{score:.1f}%"
    text_width = pdf.get_string_width(score_text)
    # Center the score in the middle of the semicircle arc
    pdf.set_xy(center_x - text_width / 2, center_y - 6)
    pdf.cell(text_width, 8, score_text, align='C')

    # Reset
    pdf.set_text_color(0, 0, 0)
    pdf.set_line_width(0.2)
    pdf.set_draw_color(0, 0, 0)


def draw_metric_box(pdf, x, y, width, height, number, label, bg_color):
    """
    Draw a colored box with large number and label
    """
    # Draw background
    pdf.set_fill_color(*bg_color)
    pdf.rect(x, y, width, height, 'F')

    # Draw large number - smaller
    pdf.set_font("Arial", "B", 24)
    pdf.set_text_color(255, 255, 255)
    num_str = str(number)
    num_width = pdf.get_string_width(num_str)
    pdf.set_xy(x, y + height / 3.5)
    pdf.cell(width, 8, num_str, align='C')

    # Draw label - smaller
    pdf.set_font("Arial", "B", 8)
    pdf.set_xy(x, y + height - 10)
    pdf.cell(width, 6, label, align='C')

    # Reset
    pdf.set_text_color(0, 0, 0)


def generate_roleiq_pdf(analysis_data):
    """
    Generate a RoleIQ-style PDF matching the reference format

    Args:
        analysis_data: Dictionary with keys:
            - score: Overall match score (0-100)
            - summary: Summary text paragraph
            - skill_matches: List of matched skills
            - skill_gaps: List of missing skills
            - related_skills: List of related skills
            - years_resume: Years of experience on resume
            - years_required: Years required by JD
            - skill_match_table: List of dicts with 'skill' and 'match' (YES/NO)
            - related_skills_list: List of skill names
            - recommendations: List of recommendation strings
    """
    pdf = RoleIQPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Start content below header (header is 35mm)
    pdf.set_y(45)

    # ===== GAUGE CHART =====
    gauge_y = pdf.get_y()
    draw_gauge_chart(pdf, 60, gauge_y, 90, analysis_data.get('score', 0))
    pdf.set_y(gauge_y + 52)

    # ===== SUMMARY SECTION =====
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(99, 102, 241)  # Blue color
    pdf.cell(0, 6, "Summary", ln=True)

    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(0, 0, 0)
    summary = sanitize_text(analysis_data.get('summary', 'No summary available.'))
    pdf.multi_cell(0, 4, summary)
    pdf.ln(4)

    # ===== SKILLS ANALYSIS OVERVIEW =====
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(0, 6, "Skills Analysis Overview", ln=True)
    pdf.ln(3)

    # Three metric boxes - smaller
    box_width = 56
    box_height = 28
    box_y = pdf.get_y()
    spacing = 8

    # Green box - Skills Matched
    matched_count = len(analysis_data.get('skill_matches', []))
    draw_metric_box(pdf, 15, box_y, box_width, box_height,
                    matched_count, "Skills Matched", (16, 185, 129))

    # Red box - Skill Gaps
    gaps_count = len(analysis_data.get('skill_gaps', []))
    draw_metric_box(pdf, 15 + box_width + spacing, box_y, box_width, box_height,
                    gaps_count, "Skill Gaps", (239, 68, 68))

    # Orange box - Related Skills
    related_count = len(analysis_data.get('related_skills', []))
    draw_metric_box(pdf, 15 + (box_width + spacing) * 2, box_y, box_width, box_height,
                    related_count, "Related Skills", (245, 158, 11))

    pdf.set_y(box_y + box_height + 8)

    # ===== EXPERIENCE ANALYSIS =====
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(0, 6, "Experience Analysis:", ln=True)
    pdf.ln(3)

    box_y = pdf.get_y()

    # Blue box - Years on Resume
    years_resume = analysis_data.get('years_resume', 0)
    draw_metric_box(pdf, 15, box_y, box_width, box_height,
                    years_resume, "Years on Resume", (99, 102, 241))

    # Purple box - Years Required
    years_required = analysis_data.get('years_required', '0')
    draw_metric_box(pdf, 15 + box_width + spacing, box_y, box_width, box_height,
                    str(years_required), "Years Required", (168, 85, 247))

    # Green box - OK/Meets Requirement
    draw_metric_box(pdf, 15 + (box_width + spacing) * 2, box_y, box_width, box_height,
                    "OK", "Meets Requirement", (16, 185, 129))

    pdf.set_y(box_y + box_height + 6)

    # Experience match text
    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(0, 0, 0)
    exp_text = f"- Experience Match: Your {years_resume} years meets the {years_required} year requirement, positioning you as a qualified candidate."
    pdf.multi_cell(0, 4, exp_text)
    pdf.ln(4)

    # ===== ROLE FIT ANALYSIS =====
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(0, 6, "Role Fit Analysis", ln=True)
    pdf.ln(2)

    # Where Resume Aligns Well
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(0, 5, "Where the Resume Aligns Well:", ln=True)
    pdf.ln(1)

    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 4, f"- Strong expertise in core requirements, demonstrating {matched_count} direct skill matches.")
    pdf.ln(2)

    # Skill Match Analysis Table
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 5, f"Skill Match Analysis ({matched_count} Matches, {gaps_count} Gaps):", ln=True)
    pdf.ln(1)

    # Table header
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(140, 6, "Skill from Job Description", 1, 0, 'L', True)
    pdf.cell(40, 6, "Match", 1, 1, 'C', True)

    # Table rows
    pdf.set_font("Arial", "", 7)
    skill_table = analysis_data.get('skill_match_table', [])
    for item in skill_table[:20]:  # Limit to first 20 to avoid overflow
        skill_name = sanitize_text(item.get('skill', ''))
        match_status = item.get('match', 'NO')

        # Set color based on match status
        if match_status == 'YES':
            pdf.set_text_color(0, 128, 0)  # Green
        else:
            pdf.set_text_color(255, 0, 0)  # Red

        pdf.cell(140, 5, skill_name, 1, 0, 'L')
        pdf.cell(40, 5, match_status, 1, 1, 'C')

    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    # Background demonstrates text
    pdf.set_font("Arial", "", 8)
    pdf.multi_cell(0, 4, "- Background demonstrates relevant professional experience and capability to contribute to similar roles.")
    pdf.ln(1)

    # Experience with related skills
    pdf.multi_cell(0, 4, f"- Experience with {related_count} skills could be rephrased to better mirror job description terminology.")
    pdf.ln(3)

    # ===== RELATED SKILLS TABLE =====
    if analysis_data.get('related_skills_list'):
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 5, f"Related Skills - Consider Rewording ({related_count}):", ln=True)
        pdf.ln(1)

        # Table header with beige background
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(255, 250, 205)  # Light yellow/beige
        pdf.cell(0, 6, "Skills That Could Be Reworded", 1, 1, 'L', True)

        # Table rows
        pdf.set_font("Arial", "", 7)
        for skill in analysis_data.get('related_skills_list', [])[:30]:
            pdf.cell(0, 5, sanitize_text(skill), 1, 1, 'L')

        pdf.ln(3)

    # ===== RESUME OPTIMIZATION GUIDANCE =====
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(0, 6, "Resume Optimization Guidance", ln=True)
    pdf.ln(2)

    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 4, "To maintain your strong position, update your resume with the following enhancements:")
    pdf.ln(2)

    # Numbered recommendations
    pdf.set_font("Arial", "", 8)
    recommendations = analysis_data.get('recommendations', [])
    for i, rec in enumerate(recommendations, 1):
        pdf.set_font("Arial", "B", 8)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(8, 4, f"{i}.", 0, 0)
        pdf.set_font("Arial", "", 8)
        pdf.set_text_color(0, 0, 0)
        # Calculate width for multi_cell
        remaining_width = pdf.w - pdf.l_margin - pdf.r_margin - 8
        y_before = pdf.get_y()
        pdf.multi_cell(remaining_width, 4, sanitize_text(rec))
        pdf.ln(1)

    # ===== FOOTER =====
    pdf.ln(6)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(0, 4, "RoleSynch by TooGood", 0, 1, 'C')

    # Return PDF as bytes
    try:
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        return pdf_bytes
    except Exception as e:
        return None
