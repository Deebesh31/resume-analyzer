import streamlit as st
import PyPDF2
import io
import os
import re
import google.generativeai as genai
from dotenv import load_dotenv
from collections import Counter
import matplotlib.pyplot as plt
from datetime import datetime

load_dotenv()

st.set_page_config(
    page_title="AI Resume Analyzer Pro", 
    page_icon="📄", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 1rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        height: 3em;
        border-radius: 8px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .score-excellent { color: #4CAF50; font-weight: bold; }
    .score-good { color: #8BC34A; font-weight: bold; }
    .score-average { color: #FFC107; font-weight: bold; }
    .score-poor { color: #FF5722; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("📄 AI Resume Analyzer Pro")
st.markdown("**Advanced AI-powered resume analysis with comprehensive insights**")

# Initialize session state
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []
if 'current_resume_text' not in st.session_state:
    st.session_state.current_resume_text = None
if 'previous_score' not in st.session_state:
    st.session_state.previous_score = None

# Sidebar
with st.sidebar:
    st.header("⚙️ Analysis Settings")
    
    analysis_mode = st.radio(
        "Analysis Mode",
        ["Quick Scan", "Standard Analysis", "Deep Dive", "ATS Optimization"],
        index=1
    )
    
    st.markdown("---")
    st.header("🎯 Focus Areas")
    
    focus_areas = st.multiselect(
        "Select Focus Areas",
        ["Content Quality", "Skills Presentation", "Experience Impact", 
         "Formatting & Structure", "ATS Compatibility", "Keywords Optimization",
         "Achievements Quantification", "Action Verbs", "Grammar & Clarity"],
        default=["Content Quality", "Skills Presentation", "ATS Compatibility"]
    )
    
    st.markdown("---")
    st.header("📊 Additional Features")
    
    enable_scoring = st.checkbox("Resume Scoring", value=True)
    enable_statistics = st.checkbox("Statistics Dashboard", value=True)
    enable_ats_check = st.checkbox("ATS Compatibility Check", value=True)
    enable_keyword_analysis = st.checkbox("Keyword Analysis", value=False)
    enable_action_verbs = st.checkbox("Action Verb Analysis", value=False)
    
    st.markdown("---")
    st.info("💡 **Pro Tip:** Use ATS Optimization mode for applicant tracking system compatibility")

# Check API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    st.error("⚠️ GEMINI_API_KEY not found! Please add it to your .env file.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

# Main content tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📤 Upload & Analyze", 
    "🎯 Job Matcher", 
    "📝 Cover Letter Generator",
    "📊 History & Comparison",
    "🔧 Resume Tools"
])

# Helper functions
def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + '\n'
        return text
    except Exception as e:
        raise Exception(f"Error reading PDF: {str(e)}")

def extract_text_from_file(uploaded_file):
    if uploaded_file.type == "application/pdf":
        return extract_text_from_pdf(io.BytesIO(uploaded_file.read()))
    elif uploaded_file.type == "text/plain":
        return uploaded_file.read().decode("utf-8")
    else:
        raise Exception("Unsupported file format")

def calculate_resume_statistics(text):
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    
    # Common action verbs
    action_verbs = [
        'achieved', 'improved', 'trained', 'managed', 'created', 'designed', 
        'developed', 'led', 'increased', 'decreased', 'launched', 'implemented',
        'coordinated', 'analyzed', 'solved', 'optimized', 'streamlined', 'built'
    ]
    
    text_lower = text.lower()
    action_verb_count = sum(text_lower.count(verb) for verb in action_verbs)
    
    # Find quantifiable achievements (numbers)
    numbers = re.findall(r'\b\d+[%]?\b', text)
    quantifiable_achievements = len(numbers)
    
    # Email and phone detection
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    phones = re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text)
    
    return {
        'word_count': len(words),
        'sentence_count': len([s for s in sentences if s.strip()]),
        'action_verb_count': action_verb_count,
        'quantifiable_achievements': quantifiable_achievements,
        'has_email': len(emails) > 0,
        'has_phone': len(phones) > 0,
        'avg_sentence_length': len(words) / max(len([s for s in sentences if s.strip()]), 1)
    }

def check_ats_compatibility(text):
    issues = []
    score = 100
    
    # Check for complex formatting indicators
    if text.count('|') > 5:
        issues.append("⚠️ Tables detected - may not be ATS-friendly")
        score -= 15
    
    if len(re.findall(r'[^\x00-\x7F]+', text)) > 10:
        issues.append("⚠️ Special characters detected - use standard ASCII")
        score -= 10
    
    # Check for contact info
    if not re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
        issues.append("❌ No email address found")
        score -= 20
    
    if not re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text):
        issues.append("⚠️ No phone number detected")
        score -= 10
    
    # Check for sections
    common_sections = ['experience', 'education', 'skills', 'summary']
    found_sections = sum(1 for section in common_sections if section in text.lower())
    
    if found_sections < 3:
        issues.append("⚠️ Missing common resume sections")
        score -= 15
    
    if score >= 80:
        status = "✅ Excellent"
        color = "score-excellent"
    elif score >= 60:
        status = "✔️ Good"
        color = "score-good"
    elif score >= 40:
        status = "⚠️ Needs Improvement"
        color = "score-average"
    else:
        status = "❌ Poor"
        color = "score-poor"
    
    return score, issues, status, color

def calculate_overall_score(text, stats):
    score = 0
    max_score = 100
    
    # Word count (20 points)
    if 400 <= stats['word_count'] <= 800:
        score += 20
    elif 300 <= stats['word_count'] <= 1000:
        score += 15
    else:
        score += 10
    
    # Action verbs (20 points)
    if stats['action_verb_count'] >= 15:
        score += 20
    elif stats['action_verb_count'] >= 10:
        score += 15
    elif stats['action_verb_count'] >= 5:
        score += 10
    else:
        score += 5
    
    # Quantifiable achievements (20 points)
    if stats['quantifiable_achievements'] >= 10:
        score += 20
    elif stats['quantifiable_achievements'] >= 5:
        score += 15
    elif stats['quantifiable_achievements'] >= 3:
        score += 10
    else:
        score += 5
    
    # Contact information (20 points)
    if stats['has_email'] and stats['has_phone']:
        score += 20
    elif stats['has_email'] or stats['has_phone']:
        score += 10
    
    # Sentence structure (20 points)
    if 15 <= stats['avg_sentence_length'] <= 25:
        score += 20
    elif 10 <= stats['avg_sentence_length'] <= 30:
        score += 15
    else:
        score += 10
    
    return min(score, max_score)

def analyze_keywords(resume_text, job_description):
    resume_words = set(re.findall(r'\b[a-z]{3,}\b', resume_text.lower()))
    jd_words = set(re.findall(r'\b[a-z]{3,}\b', job_description.lower()))
    
    # Common stop words to exclude
    stop_words = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'will', 'are', 'have', 'has', 'been', 'were', 'was'}
    
    resume_words -= stop_words
    jd_words -= stop_words
    
    matching_keywords = resume_words & jd_words
    missing_keywords = jd_words - resume_words
    
    # Calculate match percentage
    if len(jd_words) > 0:
        match_percentage = (len(matching_keywords) / len(jd_words)) * 100
    else:
        match_percentage = 0
    
    return {
        'match_percentage': match_percentage,
        'matching_keywords': list(matching_keywords)[:20],
        'missing_keywords': list(missing_keywords)[:20],
        'total_jd_keywords': len(jd_words),
        'total_resume_keywords': len(resume_words)
    }

def suggest_action_verbs(text):
    weak_verbs = ['responsible for', 'worked on', 'helped', 'assisted', 'did', 'made', 'handled']
    strong_verbs = {
        'responsible for': ['managed', 'oversaw', 'directed', 'coordinated'],
        'worked on': ['developed', 'created', 'built', 'designed'],
        'helped': ['supported', 'facilitated', 'enabled', 'contributed to'],
        'assisted': ['collaborated', 'partnered', 'coordinated with'],
        'did': ['executed', 'performed', 'completed', 'delivered'],
        'made': ['created', 'produced', 'generated', 'developed'],
        'handled': ['managed', 'processed', 'coordinated', 'executed']
    }
    
    suggestions = []
    text_lower = text.lower()
    
    for weak in weak_verbs:
        if weak in text_lower:
            suggestions.append({
                'weak': weak,
                'strong': strong_verbs[weak],
                'count': text_lower.count(weak)
            })
    
    return suggestions

def generate_pdf_report(analysis_text, stats, score):
    report = f"""
===========================================
AI RESUME ANALYZER PRO - ANALYSIS REPORT
===========================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

OVERALL SCORE: {score}/100

STATISTICS:
-----------
Word Count: {stats['word_count']}
Sentence Count: {stats['sentence_count']}
Action Verbs Used: {stats['action_verb_count']}
Quantifiable Achievements: {stats['quantifiable_achievements']}
Contact Info Complete: {'Yes' if stats['has_email'] and stats['has_phone'] else 'No'}

DETAILED ANALYSIS:
------------------
{analysis_text}

===========================================
© 2025 AI Resume Analyzer Pro. All rights reserved.
"""
    return report

# TAB 1: Upload & Analyze
with tab1:
    st.header("📤 Upload Your Resume")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Choose your resume file",
            type=["pdf", "txt"],
            help="Supported formats: PDF, TXT"
        )
    
    with col2:
        if uploaded_file:
            st.success("✅ File uploaded!")
            st.caption(f"📄 {uploaded_file.name}")
            st.caption(f"💾 {uploaded_file.size / 1024:.1f} KB")
    
    job_role = st.text_input(
        "🎯 Target Job Role (Optional)",
        placeholder="e.g., Senior Software Engineer, Data Analyst",
        help="Helps tailor the analysis to your target position"
    )
    
    analyze_btn = st.button("🚀 Analyze Resume", type="primary", use_container_width=True)
    
    if analyze_btn and uploaded_file:
        with st.spinner("🔍 Analyzing your resume... Please wait."):
            try:
                file_content = extract_text_from_file(uploaded_file)
                st.session_state.current_resume_text = file_content
                
                if not file_content.strip():
                    st.error("❌ File appears empty or unreadable")
                    st.stop()
                
                # Calculate statistics
                stats = calculate_resume_statistics(file_content)
                
                # Calculate overall score
                overall_score = calculate_overall_score(file_content, stats)
                
                # Display Score Card
                if enable_scoring:
                    st.markdown("---")
                    st.subheader("📊 Resume Score")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if overall_score >= 80:
                            st.metric("Overall Score", f"{overall_score}/100", "Excellent", delta_color="normal")
                        elif overall_score >= 60:
                            st.metric("Overall Score", f"{overall_score}/100", "Good", delta_color="normal")
                        elif overall_score >= 40:
                            st.metric("Overall Score", f"{overall_score}/100", "Average", delta_color="inverse")
                        else:
                            st.metric("Overall Score", f"{overall_score}/100", "Needs Work", delta_color="inverse")
                    
                    with col2:
                        word_score = "✅" if 400 <= stats['word_count'] <= 800 else "⚠️"
                        st.metric("Word Count", stats['word_count'], word_score)
                    
                    with col3:
                        verb_score = "✅" if stats['action_verb_count'] >= 10 else "⚠️"
                        st.metric("Action Verbs", stats['action_verb_count'], verb_score)
                    
                    with col4:
                        achieve_score = "✅" if stats['quantifiable_achievements'] >= 5 else "⚠️"
                        st.metric("Achievements", stats['quantifiable_achievements'], achieve_score)
                    
                    # Progress bar
                    st.progress(overall_score / 100)
                    
                    # Compare with previous
                    if st.session_state.previous_score:
                        improvement = overall_score - st.session_state.previous_score
                        if improvement > 0:
                            st.success(f"🎉 Improved by {improvement} points from last analysis!")
                        elif improvement < 0:
                            st.warning(f"⚠️ Score decreased by {abs(improvement)} points")
                        else:
                            st.info("Score unchanged from last analysis")
                    
                    st.session_state.previous_score = overall_score
                
                # Statistics Dashboard
                if enable_statistics:
                    st.markdown("---")
                    st.subheader("📈 Resume Statistics")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total Words", stats['word_count'])
                        st.metric("Sentences", stats['sentence_count'])
                    
                    with col2:
                        st.metric("Avg Sentence Length", f"{stats['avg_sentence_length']:.1f} words")
                        st.metric("Action Verbs", stats['action_verb_count'])
                    
                    with col3:
                        st.metric("Numbers/Metrics", stats['quantifiable_achievements'])
                        contact_status = "✅ Complete" if stats['has_email'] and stats['has_phone'] else "⚠️ Incomplete"
                        st.metric("Contact Info", contact_status)
                
                # ATS Compatibility Check
                if enable_ats_check:
                    st.markdown("---")
                    st.subheader("🤖 ATS Compatibility Check")
                    
                    ats_score, ats_issues, ats_status, ats_color = check_ats_compatibility(file_content)
                    
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.markdown(f"### <span class='{ats_color}'>{ats_score}/100</span>", unsafe_allow_html=True)
                        st.markdown(f"**Status:** {ats_status}")
                    
                    with col2:
                        if ats_issues:
                            st.markdown("**Issues Found:**")
                            for issue in ats_issues:
                                st.markdown(f"- {issue}")
                        else:
                            st.success("✅ No major ATS compatibility issues detected!")
                
                # Action Verb Analysis
                if enable_action_verbs:
                    st.markdown("---")
                    st.subheader("💪 Action Verb Analysis")
                    
                    verb_suggestions = suggest_action_verbs(file_content)
                    
                    if verb_suggestions:
                        st.warning(f"Found {len(verb_suggestions)} weak phrases that can be improved:")
                        
                        for suggestion in verb_suggestions:
                            with st.expander(f"Replace '{suggestion['weak']}' ({suggestion['count']} occurrences)"):
                                st.markdown("**Suggested stronger alternatives:**")
                                for strong in suggestion['strong']:
                                    st.markdown(f"- {strong}")
                    else:
                        st.success("✅ Great use of action verbs!")
                
                # AI Analysis
                st.markdown("---")
                st.subheader("🤖 AI-Powered Analysis")
                
                # Generate prompt based on mode
                mode_instructions = {
                    "Quick Scan": "Provide a brief overview with 3-5 key points only.",
                    "Standard Analysis": "Provide detailed analysis with specific examples and recommendations.",
                    "Deep Dive": "Provide comprehensive analysis with examples, industry comparisons, and step-by-step improvements.",
                    "ATS Optimization": "Focus specifically on ATS compatibility, keyword optimization, and formatting for applicant tracking systems."
                }
                
                prompt = f"""You are an expert resume reviewer with 15+ years of experience in HR and recruitment.

**Analysis Mode:** {analysis_mode}
{mode_instructions[analysis_mode]}

**Focus Areas:** {', '.join(focus_areas)}

**Target Role:** {job_role if job_role else 'General applications'}

**Resume Statistics:**
- Word Count: {stats['word_count']}
- Action Verbs: {stats['action_verb_count']}
- Quantifiable Achievements: {stats['quantifiable_achievements']}
- Overall Score: {overall_score}/100

**Resume Content:**
{file_content}

Please provide structured feedback in this format:

## 🎯 Executive Summary
[Brief overall assessment]

## ✅ Key Strengths
[3-5 specific strengths with examples]

## 🔧 Areas for Improvement
[Specific issues with examples from resume]

## 💡 Actionable Recommendations
[Concrete, prioritized suggestions]

## 🚀 Next Steps
[Immediate actions to take]

Be specific, constructive, and actionable."""

                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                response = model.generate_content(prompt)
                
                st.markdown(response.text)
                
                # Save to history
                st.session_state.analysis_history.append({
                    'timestamp': datetime.now(),
                    'filename': uploaded_file.name,
                    'score': overall_score,
                    'analysis': response.text,
                    'stats': stats
                })
                
                # Download options
                st.markdown("---")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.download_button(
                        label="📥 Download Analysis (TXT)",
                        data=response.text,
                        file_name=f"analysis_{uploaded_file.name.split('.')[0]}_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                with col2:
                    full_report = generate_pdf_report(response.text, stats, overall_score)
                    st.download_button(
                        label="📄 Download Full Report",
                        data=full_report,
                        file_name=f"full_report_{uploaded_file.name.split('.')[0]}_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("💡 Try a different file or check your API configuration")

# TAB 2: Job Matcher
with tab2:
    st.header("🎯 Resume-Job Description Matcher")
    st.markdown("Compare your resume against a job description to see how well they match")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Resume")
        resume_file = st.file_uploader("Upload Resume", type=["pdf", "txt"], key="matcher_resume")
        
        if resume_file:
            resume_text = extract_text_from_file(resume_file)
            st.text_area("Resume Preview", resume_text[:500] + "...", height=200, disabled=True)
    
    with col2:
        st.subheader("📋 Job Description")
        job_description = st.text_area(
            "Paste Job Description Here",
            height=200,
            placeholder="Paste the full job description here..."
        )
    
    if st.button("🔍 Analyze Match", use_container_width=True) and resume_file and job_description:
        with st.spinner("Analyzing match..."):
            try:
                resume_text = extract_text_from_file(resume_file)
                
                # Keyword analysis
                if enable_keyword_analysis:
                    keyword_analysis = analyze_keywords(resume_text, job_description)
                    
                    st.markdown("---")
                    st.subheader("📊 Match Analysis")
                    
                    # Match percentage with visual
                    match_pct = keyword_analysis['match_percentage']
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Match Score", f"{match_pct:.1f}%")
                        st.progress(match_pct / 100)
                    
                    with col2:
                        st.metric("Matching Keywords", len(keyword_analysis['matching_keywords']))
                    
                    with col3:
                        st.metric("Missing Keywords", len(keyword_analysis['missing_keywords']))
                    
                    # Display keywords
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.success("**✅ Matching Keywords:**")
                        if keyword_analysis['matching_keywords']:
                            for kw in keyword_analysis['matching_keywords'][:15]:
                                st.markdown(f"- {kw}")
                        else:
                            st.info("No matching keywords found")
                    
                    with col2:
                        st.warning("**⚠️ Missing Important Keywords:**")
                        if keyword_analysis['missing_keywords']:
                            for kw in keyword_analysis['missing_keywords'][:15]:
                                st.markdown(f"- {kw}")
                        else:
                            st.success("All major keywords covered!")
                
                # AI-powered matching analysis
                st.markdown("---")
                st.subheader("🤖 AI Match Analysis")
                
                match_prompt = f"""Analyze how well this resume matches the job description.

**Job Description:**
{job_description}

**Resume:**
{resume_text}

Provide analysis in this format:

## 📊 Overall Match Assessment
[Percentage estimate and summary]

## ✅ Strong Matches
[Skills/experience that align well]

## ⚠️ Gaps Identified
[Missing qualifications or skills]

## 💡 Recommendations
[How to improve the match]

## 🎯 Application Strategy
[Tips for applying to this role]"""

                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                response = model.generate_content(match_prompt)
                
                st.markdown(response.text)
                
                # Download match report
                st.download_button(
                    label="📥 Download Match Report",
                    data=response.text,
                    file_name=f"job_match_report_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# TAB 3: Cover Letter Generator
with tab3:
    st.header("📝 AI Cover Letter Generator")
    st.markdown("Generate a tailored cover letter based on your resume and job description")
    
    col1, col2 = st.columns(2)
    
    with col1:
        cl_resume = st.file_uploader("Upload Your Resume", type=["pdf", "txt"], key="cl_resume")
    
    with col2:
        cl_tone = st.selectbox(
            "Cover Letter Tone",
            ["Professional", "Enthusiastic", "Formal", "Creative", "Conversational"]
        )
    
    cl_job_desc = st.text_area(
        "Job Description",
        height=150,
        placeholder="Paste the job description here..."
    )
    
    cl_company = st.text_input("Company Name", placeholder="e.g., Google, Microsoft")
    cl_role = st.text_input("Job Title", placeholder="e.g., Senior Software Engineer")
    
    if st.button("✨ Generate Cover Letter", use_container_width=True) and cl_resume and cl_job_desc:
        with st.spinner("Crafting your cover letter..."):
            try:
                resume_text = extract_text_from_file(cl_resume)
                
                cl_prompt = f"""Generate a professional cover letter based on this information:

**Candidate's Resume:**
{resume_text}

**Job Description:**
{cl_job_desc}

**Company:** {cl_company if cl_company else '[Company Name]'}
**Role:** {cl_role if cl_role else '[Job Title]'}
**Tone:** {cl_tone}

Create a compelling cover letter that:
1. Opens with a strong hook
2. Highlights relevant experience from the resume
3. Shows enthusiasm for the role
4. Demonstrates knowledge of the company
5. Includes a clear call to action
6. Maintains {cl_tone.lower()} tone throughout

Format it as a complete cover letter ready to send."""

                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                response = model.generate_content(cl_prompt)
                
                st.markdown("---")
                st.subheader("✉️ Your Generated Cover Letter")
                
                cover_letter = response.text
                st.markdown(cover_letter)
                
                # Download and copy options
                col1, col2 = st.columns(2)
                
                with col1:
                    st.download_button(
                        label="📥 Download Cover Letter",
                        data=cover_letter,
                        file_name=f"cover_letter_{cl_company}_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                with col2:
                    if st.button("🔄 Generate Another Version", use_container_width=True):
                        st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# TAB 4: History & Comparison
with tab4:
    st.header("📊 Analysis History & Comparison")
    
    if st.session_state.analysis_history:
        st.markdown(f"**Total Analyses:** {len(st.session_state.analysis_history)}")
        
        # Display history
        for idx, entry in enumerate(reversed(st.session_state.analysis_history)):
            with st.expander(f"📄 {entry['filename']} - Score: {entry['score']}/100 - {entry['timestamp'].strftime('%Y-%m-%d %H:%M')}"):
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Score", f"{entry['score']}/100")
                
                with col2:
                    st.metric("Words", entry['stats']['word_count'])
                
                with col3:
                    st.metric("Action Verbs", entry['stats']['action_verb_count'])
                
                st.markdown("**Analysis:**")
                st.markdown(entry['analysis'][:500] + "...")
                
                st.download_button(
                    label="Download Full Analysis",
                    data=entry['analysis'],
                    file_name=f"analysis_{idx}_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                    key=f"download_{idx}"
                )
        
        # Compare versions if multiple exist
        if len(st.session_state.analysis_history) >= 2:
            st.markdown("---")
            st.subheader("🔄 Compare Resume Versions")
            
            col1, col2 = st.columns(2)
            
            with col1:
                version1_idx = st.selectbox(
                    "Select First Version",
                    range(len(st.session_state.analysis_history)),
                    format_func=lambda x: f"{st.session_state.analysis_history[x]['filename']} ({st.session_state.analysis_history[x]['timestamp'].strftime('%Y-%m-%d')})"
                )
            
            with col2:
                version2_idx = st.selectbox(
                    "Select Second Version",
                    range(len(st.session_state.analysis_history)),
                    index=min(1, len(st.session_state.analysis_history)-1),
                    format_func=lambda x: f"{st.session_state.analysis_history[x]['filename']} ({st.session_state.analysis_history[x]['timestamp'].strftime('%Y-%m-%d')})"
                )
            
            if st.button("📊 Compare Versions", use_container_width=True):
                v1 = st.session_state.analysis_history[version1_idx]
                v2 = st.session_state.analysis_history[version2_idx]
                
                st.markdown("### Comparison Results")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    score_diff = v2['score'] - v1['score']
                    st.metric("Score Change", f"{v2['score']}/100", f"{score_diff:+d} points")
                
                with col2:
                    word_diff = v2['stats']['word_count'] - v1['stats']['word_count']
                    st.metric("Word Count", v2['stats']['word_count'], f"{word_diff:+d}")
                
                with col3:
                    verb_diff = v2['stats']['action_verb_count'] - v1['stats']['action_verb_count']
                    st.metric("Action Verbs", v2['stats']['action_verb_count'], f"{verb_diff:+d}")
                
                with col4:
                    achieve_diff = v2['stats']['quantifiable_achievements'] - v1['stats']['quantifiable_achievements']
                    st.metric("Achievements", v2['stats']['quantifiable_achievements'], f"{achieve_diff:+d}")
                
                if score_diff > 0:
                    st.success(f"🎉 Great improvement! Your score increased by {score_diff} points!")
                elif score_diff < 0:
                    st.warning(f"⚠️ Score decreased by {abs(score_diff)} points. Consider reverting some changes.")
                else:
                    st.info("Score remained the same.")
        
        # Clear history button
        if st.button("🗑️ Clear All History", type="secondary"):
            st.session_state.analysis_history = []
            st.session_state.previous_score = None
            st.rerun()
    
    else:
        st.info("📭 No analysis history yet. Upload and analyze a resume in the first tab!")

# TAB 5: Resume Tools
with tab5:
    st.header("🔧 Resume Enhancement Tools")
    
    tool_option = st.selectbox(
        "Select Tool",
        ["Action Verb Replacer", "Achievement Quantifier", "Bullet Point Improver", "Section Reorganizer", "Interview Question Generator"]
    )
    
    st.markdown("---")
    
    if tool_option == "Action Verb Replacer":
        st.subheader("💪 Action Verb Replacer")
        st.markdown("Replace weak verbs with powerful action verbs")
        
        input_text = st.text_area("Paste your resume bullet points:", height=200)
        
        if st.button("🔄 Improve Action Verbs") and input_text:
            with st.spinner("Improving verbs..."):
                prompt = f"""Analyze these resume bullet points and replace weak verbs with strong action verbs.

Input:
{input_text}

For each bullet point:
1. Identify weak verbs
2. Suggest stronger alternatives
3. Rewrite the bullet point

Format as:
**Original:** [original text]
**Issue:** [weak verb identified]
**Improved:** [rewritten with strong verb]
**Why Better:** [brief explanation]"""

                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                response = model.generate_content(prompt)
                st.markdown(response.text)
    
    elif tool_option == "Achievement Quantifier":
        st.subheader("📊 Achievement Quantifier")
        st.markdown("Add numbers and metrics to your achievements")
        
        achievement_text = st.text_area("Describe your achievements:", height=200)
        
        if st.button("📈 Quantify Achievements") and achievement_text:
            with st.spinner("Adding metrics..."):
                prompt = f"""Transform these achievements into quantified, measurable statements.

Achievements:
{achievement_text}

For each achievement:
1. Identify what can be quantified (time saved, revenue, efficiency, etc.)
2. Suggest realistic metrics or percentages
3. Rewrite in STAR format (Situation, Task, Action, Result)

Provide before/after comparisons."""

                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                response = model.generate_content(prompt)
                st.markdown(response.text)
    
    elif tool_option == "Bullet Point Improver":
        st.subheader("✨ Bullet Point Improver")
        st.markdown("Transform basic bullet points into impactful statements")
        
        bullets = st.text_area("Enter your bullet points (one per line):", height=200)
        
        if st.button("✨ Improve Bullets") and bullets:
            with st.spinner("Enhancing bullet points..."):
                prompt = f"""Improve these resume bullet points to make them more impactful and professional.

Bullet Points:
{bullets}

For each bullet:
1. Start with a strong action verb
2. Add context and specifics
3. Include results/impact
4. Keep it concise (1-2 lines)

Show before/after for each."""

                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                response = model.generate_content(prompt)
                st.markdown(response.text)
    
    elif tool_option == "Section Reorganizer":
        st.subheader("📋 Section Reorganizer")
        st.markdown("Get suggestions on optimal resume structure")
        
        resume_sections = st.text_area("List your current resume sections:", height=150, placeholder="e.g., Summary, Experience, Education, Skills")
        target_industry = st.text_input("Target Industry:", placeholder="e.g., Tech, Finance, Healthcare")
        
        if st.button("🔄 Get Structure Recommendations") and resume_sections:
            with st.spinner("Analyzing structure..."):
                prompt = f"""Analyze this resume structure and provide recommendations.

Current Sections:
{resume_sections}

Target Industry: {target_industry if target_industry else 'General'}

Provide:
1. Optimal section order for this industry
2. Sections to add/remove
3. Content suggestions for each section
4. Industry-specific best practices"""

                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                response = model.generate_content(prompt)
                st.markdown(response.text)
    
    elif tool_option == "Interview Question Generator":
        st.subheader("💬 Interview Question Generator")
        st.markdown("Prepare for interviews based on your resume")
        
        interview_resume = st.file_uploader("Upload Resume for Interview Prep", type=["pdf", "txt"], key="interview_resume")
        interview_role = st.text_input("Target Role:", placeholder="e.g., Product Manager")
        
        if st.button("🎤 Generate Interview Questions") and interview_resume:
            with st.spinner("Generating questions..."):
                resume_text = extract_text_from_file(interview_resume)
                
                prompt = f"""Based on this resume, generate likely interview questions and suggested answers.

Resume:
{resume_text}

Target Role: {interview_role if interview_role else 'General'}

Provide:
1. 10 behavioral questions based on their experience
2. 5 technical questions related to their skills
3. 3 situational questions
4. Suggested answer frameworks for each

Format each as:
**Question:** [question]
**Why They'll Ask:** [reasoning]
**How to Answer:** [framework/tips]
**Example Answer:** [brief example]"""

                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                response = model.generate_content(prompt)
                st.markdown(response.text)
                
                st.download_button(
                    label="📥 Download Interview Prep Guide",
                    data=response.text,
                    file_name=f"interview_prep_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #666;'>© 2025 AI Resume Analyzer Pro. All rights reserved.</p>",
    unsafe_allow_html=True)
