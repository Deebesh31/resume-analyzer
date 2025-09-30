import streamlit as st
import PyPDF2
import io
import os
import re
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime
import json
from streamlit_google_auth import Authenticate

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
    .score-excellent { color: #4CAF50; font-weight: bold; }
    .score-good { color: #8BC34A; font-weight: bold; }
    .score-average { color: #FFC107; font-weight: bold; }
    .score-poor { color: #FF5722; font-weight: bold; }
    .auth-container {
        max-width: 600px;
        margin: 50px auto;
        padding: 40px;
        background: white;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8501")

# User database (JSON file)
USER_DATA_FILE = "user_data.json"

def load_user_data():
    """Load user data from JSON file"""
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    """Save user data to JSON file"""
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_user_usage(user_id):
    """Get user usage data"""
    user_data = load_user_data()
    if user_id in user_data:
        return user_data[user_id]
    
    # Create new user entry
    new_user = {
        'usage_count': 0,
        'last_reset': datetime.now().strftime('%Y-%m-%d'),
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    user_data[user_id] = new_user
    save_user_data(user_data)
    return new_user

def update_user_usage(user_id):
    """Update user usage count"""
    user_data = load_user_data()
    
    if user_id not in user_data:
        user_data[user_id] = {
            'usage_count': 0,
            'last_reset': datetime.now().strftime('%Y-%m-%d'),
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    # Check if we need to reset monthly usage (30 days)
    last_reset = datetime.strptime(user_data[user_id]['last_reset'], '%Y-%m-%d')
    if (datetime.now() - last_reset).days >= 30:
        user_data[user_id]['usage_count'] = 0
        user_data[user_id]['last_reset'] = datetime.now().strftime('%Y-%m-%d')
    
    user_data[user_id]['usage_count'] += 1
    save_user_data(user_data)
    return user_data[user_id]

def check_usage_limit(user_id):
    """Check if user has exceeded usage limit"""
    usage_data = get_user_usage(user_id)
    USAGE_LIMIT = 5  # Free tier: 5 analyses per month
    return usage_data['usage_count'] < USAGE_LIMIT

# Initialize Google Auth
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    authenticator = Authenticate(
        secret_credentials_path='google_credentials.json',
        cookie_name='resume_analyzer_auth',
        cookie_key='resume_analyzer_secret_key',
        redirect_uri=REDIRECT_URI,
    )
else:
    authenticator = None

# Check authentication
if authenticator:
    # Use Google OAuth
    authenticator.check_authentification()
    
    if not st.session_state['connected']:
        # Show login page
        st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
        st.title("🔐 AI Resume Analyzer Pro")
        st.markdown("### Sign in with Google to continue")
        st.markdown("Get **5 free resume analyses** per month")
        st.markdown("---")
        
        authenticator.login()
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")
        st.info("🔒 **Secure Authentication**: Your Google account keeps your data safe and private.")
        st.stop()
    
    # User is authenticated
    user_email = st.session_state['user_info'].get('email', 'user@example.com')
    user_name = st.session_state['user_info'].get('name', 'User')
    user_id = user_email.replace('@', '_').replace('.', '_')
    
else:
    # Fallback: Simple demo mode without Google OAuth
    st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
    st.title("🔐 AI Resume Analyzer Pro")
    
    if 'demo_authenticated' not in st.session_state:
        st.session_state.demo_authenticated = False
    
    if not st.session_state.demo_authenticated:
        st.warning("⚠️ Google OAuth not configured. Using demo mode.")
        st.markdown("### Demo Login")
        st.info("""
        **To enable Google Sign-In:**
        
        1. Go to [Google Cloud Console](https://console.cloud.google.com)
        2. Create a new project or select existing
        3. Enable Google+ API
        4. Create OAuth 2.0 credentials
        5. Add to .env:
           ```
           GOOGLE_CLIENT_ID=your_client_id
           GOOGLE_CLIENT_SECRET=your_client_secret
           REDIRECT_URI=http://localhost:8501
           ```
        6. Create google_credentials.json with your OAuth credentials
        """)
        
        st.markdown("---")
        demo_email = st.text_input("Enter email for demo:", placeholder="your.email@gmail.com")
        demo_name = st.text_input("Enter name:", placeholder="Your Name")
        
        if st.button("Demo Login", use_container_width=True):
            if demo_email and demo_name:
                st.session_state.demo_authenticated = True
                st.session_state.demo_email = demo_email
                st.session_state.demo_name = demo_name
                st.rerun()
            else:
                st.error("Please enter both email and name")
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()
    
    # Demo mode authenticated
    user_email = st.session_state.demo_email
    user_name = st.session_state.demo_name
    user_id = user_email.replace('@', '_').replace('.', '_')

# Main App (after authentication)
st.title("📄 AI Resume Analyzer Pro")
st.markdown(f"**Welcome back, {user_name}!** 👋")

# Top bar with user info and logout
col1, col2, col3 = st.columns([4, 1, 1])

with col1:
    usage_data = get_user_usage(user_id)
    usage_percentage = (usage_data['usage_count'] / 5) * 100
    
    st.markdown(f"**Usage: {usage_data['usage_count']}/5 analyses this month**")
    st.progress(min(usage_percentage / 100, 1.0))

with col2:
    st.markdown(f"🆓 **FREE**")

with col3:
    if st.button("🚪 Logout"):
        if authenticator:
            authenticator.logout()
        else:
            st.session_state.demo_authenticated = False
        st.rerun()

st.markdown("---")

# Check usage limit
if not check_usage_limit(user_id):
    st.error("🚫 **Monthly Limit Reached!**")
    st.warning(f"You've used all 5 analyses for this month.")
    
    # Calculate next reset date
    last_reset = datetime.strptime(usage_data['last_reset'], '%Y-%m-%d')
    next_reset = datetime.fromtimestamp(last_reset.timestamp() + (30 * 24 * 60 * 60))
    
    st.info(f"✨ Your limit will reset on: **{next_reset.strftime('%B %d, %Y')}**")
    st.markdown("### ⏰ Come back next month for 5 more free analyses!")
    st.stop()

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
    st.header("📊 Features")
    
    enable_scoring = st.checkbox("Resume Scoring", value=True)
    enable_ats_check = st.checkbox("ATS Compatibility", value=True)
    
    st.markdown("---")
    st.info("💡 **Tip:** Use ATS Optimization mode for best results with applicant tracking systems")

# Check API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    st.error("⚠️ GEMINI_API_KEY not found! Please add it to your .env file.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

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
    
    action_verbs = [
        'achieved', 'improved', 'trained', 'managed', 'created', 'designed', 
        'developed', 'led', 'increased', 'decreased', 'launched', 'implemented',
        'coordinated', 'analyzed', 'solved', 'optimized', 'streamlined', 'built'
    ]
    
    text_lower = text.lower()
    action_verb_count = sum(text_lower.count(verb) for verb in action_verbs)
    
    numbers = re.findall(r'\b\d+[%]?\b', text)
    quantifiable_achievements = len(numbers)
    
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

def calculate_overall_score(text, stats):
    score = 0
    
    if 400 <= stats['word_count'] <= 800:
        score += 20
    elif 300 <= stats['word_count'] <= 1000:
        score += 15
    else:
        score += 10
    
    if stats['action_verb_count'] >= 15:
        score += 20
    elif stats['action_verb_count'] >= 10:
        score += 15
    elif stats['action_verb_count'] >= 5:
        score += 10
    else:
        score += 5
    
    if stats['quantifiable_achievements'] >= 10:
        score += 20
    elif stats['quantifiable_achievements'] >= 5:
        score += 15
    elif stats['quantifiable_achievements'] >= 3:
        score += 10
    else:
        score += 5
    
    if stats['has_email'] and stats['has_phone']:
        score += 20
    elif stats['has_email'] or stats['has_phone']:
        score += 10
    
    if 15 <= stats['avg_sentence_length'] <= 25:
        score += 20
    elif 10 <= stats['avg_sentence_length'] <= 30:
        score += 15
    else:
        score += 10
    
    return min(score, 100)

# Main content
st.header("📤 Upload Your Resume")

col1, col2 = st.columns([2, 1])

with col1:
    uploaded_file = st.file_uploader(
        "Choose your resume file",
        type=["pdf", "txt"],
        help="Supported formats: PDF, TXT (Max 5MB)"
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
    # Increment usage count
    update_user_usage(user_id)
    
    with st.spinner("🔍 Analyzing your resume... Please wait."):
        try:
            file_content = extract_text_from_file(uploaded_file)
            
            if not file_content.strip():
                st.error("❌ File appears empty or unreadable")
                st.stop()
            
            stats = calculate_resume_statistics(file_content)
            overall_score = calculate_overall_score(file_content, stats)
            
            if enable_scoring:
                st.markdown("---")
                st.subheader("📊 Resume Score")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if overall_score >= 80:
                        st.metric("Overall Score", f"{overall_score}/100", "Excellent ⭐")
                    elif overall_score >= 60:
                        st.metric("Overall Score", f"{overall_score}/100", "Good ✓")
                    else:
                        st.metric("Overall Score", f"{overall_score}/100", "Needs Work ⚠️")
                
                with col2:
                    word_score = "✅" if 400 <= stats['word_count'] <= 800 else "⚠️"
                    st.metric("Word Count", stats['word_count'], word_score)
                
                with col3:
                    verb_score = "✅" if stats['action_verb_count'] >= 10 else "⚠️"
                    st.metric("Action Verbs", stats['action_verb_count'], verb_score)
                
                with col4:
                    achieve_score = "✅" if stats['quantifiable_achievements'] >= 5 else "⚠️"
                    st.metric("Achievements", stats['quantifiable_achievements'], achieve_score)
                
                st.progress(overall_score / 100)
            
            # AI Analysis
            st.markdown("---")
            st.subheader("🤖 AI-Powered Analysis")
            
            focus_text = ", ".join(focus_areas) if focus_areas else "general quality"
            
            prompt = f"""Analyze this resume with focus on: {focus_text}

Resume Content:
{file_content}

Target Role: {job_role if job_role else 'General'}
Analysis Mode: {analysis_mode}

Provide detailed, actionable feedback including:
1. **Key Strengths** - What stands out positively
2. **Areas for Improvement** - Specific weaknesses to address
3. **Actionable Recommendations** - Concrete steps to improve
4. **ATS Optimization Tips** - How to pass applicant tracking systems

Be constructive, specific, and prioritize the most impactful changes."""

            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content(prompt)
            
            st.markdown(response.text)
            
            # Update usage display
            remaining = 5 - get_user_usage(user_id)['usage_count']
            if remaining > 0:
                st.success(f"✅ Analysis complete! You have **{remaining}** analyses remaining this month.")
            else:
                st.warning("⚠️ This was your last free analysis this month!")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            # Rollback usage if analysis failed
            user_data = load_user_data()
            if user_id in user_data:
                user_data[user_id]['usage_count'] = max(0, user_data[user_id]['usage_count'] - 1)
                save_user_data(user_data)

# Footer
st.markdown("---")
usage_data = get_user_usage(user_id)
st.markdown(
    f"<p style='text-align: center; color: #666;'>"
    f"Logged in as {user_email} | "
    f"Analyses: {usage_data['usage_count']}/5 | "
    f"© 2025 AI Resume Analyzer Pro"
    f"</p>",
    unsafe_allow_html=True
)