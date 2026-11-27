"""Resume analysis operations shared by the web routes."""

import io
import os
import re
from datetime import datetime

import PyPDF2
from google import genai


GEMINI_MODELS = ("gemini-3.8-flash", "gemini-3.5-flash-lite")
ANALYSIS_MODES = ("Quick Scan", "Standard Analysis", "Deep Dive", "ATS Optimization")
FOCUS_AREAS = (
    "Content Quality",
    "Skills Presentation",
    "Experience Impact",
    "Formatting & Structure",
    "ATS Compatibility",
    "Keywords Optimization",
    "Achievements Quantification",
    "Action Verbs",
    "Grammar & Clarity",
)
TOOLS = (
    "Action Verb Replacer",
    "Achievement Quantifier",
    "Bullet Point Improver",
    "Section Reorganizer",
    "Interview Question Generator",
)


class GeminiConfigurationError(RuntimeError):
    pass


def generate_gemini_content(contents):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiConfigurationError("GEMINI_API_KEY is not configured on the server.")

    client = genai.Client(api_key=api_key)
    errors = []
    for model_name in GEMINI_MODELS:
        try:
            response = client.models.generate_content(model=model_name, contents=contents)
            if not response.text:
                raise RuntimeError("The model returned an empty response.")
            return response.text
        except Exception as error:
            errors.append(f"{model_name}: {error}")

    raise RuntimeError("All configured Gemini models failed. " + " | ".join(errors)) from None


def extract_text_from_file(filename, file_bytes):
    extension = os.path.splitext(filename or "")[1].lower()
    if extension == ".pdf":
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except Exception as error:
            raise ValueError(f"Error reading PDF: {error}") from error
    if extension == ".txt":
        try:
            return file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError("The text file must use UTF-8 encoding.") from error
    raise ValueError("Unsupported file format. Upload a PDF or TXT file.")


def calculate_resume_statistics(text):
    words = text.split()
    sentences = re.split(r"[.!?]+", text)
    action_verbs = [
        "achieved", "improved", "trained", "managed", "created", "designed",
        "developed", "led", "increased", "decreased", "launched", "implemented",
        "coordinated", "analyzed", "solved", "optimized", "streamlined", "built",
    ]
    text_lower = text.lower()
    action_verb_count = sum(text_lower.count(verb) for verb in action_verbs)
    numbers = re.findall(r"\b\d+[%]?\b", text)
    emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
    phones = re.findall(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", text)
    sentence_count = len([sentence for sentence in sentences if sentence.strip()])

    return {
        "word_count": len(words),
        "sentence_count": sentence_count,
        "action_verb_count": action_verb_count,
        "quantifiable_achievements": len(numbers),
        "has_email": bool(emails),
        "has_phone": bool(phones),
        "avg_sentence_length": len(words) / max(sentence_count, 1),
    }


def check_ats_compatibility(text):
    issues = []
    score = 100
    if text.count("|") > 5:
        issues.append("Tables detected - may not be ATS-friendly")
        score -= 15
    if len(re.findall(r"[^\x00-\x7F]+", text)) > 10:
        issues.append("Special characters detected - use standard ASCII")
        score -= 10
    if not re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text):
        issues.append("No email address found")
        score -= 20
    if not re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", text):
        issues.append("No phone number detected")
        score -= 10
    common_sections = ("experience", "education", "skills", "summary")
    found_sections = sum(1 for section in common_sections if section in text.lower())
    if found_sections < 3:
        issues.append("Missing common resume sections")
        score -= 15

    if score >= 80:
        status = "Excellent"
    elif score >= 60:
        status = "Good"
    elif score >= 40:
        status = "Needs Improvement"
    else:
        status = "Poor"
    return score, issues, status


def calculate_overall_score(text, stats):
    score = 0
    if 400 <= stats["word_count"] <= 800:
        score += 20
    elif 300 <= stats["word_count"] <= 1000:
        score += 15
    else:
        score += 10

    if stats["action_verb_count"] >= 15:
        score += 20
    elif stats["action_verb_count"] >= 10:
        score += 15
    elif stats["action_verb_count"] >= 5:
        score += 10
    else:
        score += 5

    if stats["quantifiable_achievements"] >= 10:
        score += 20
    elif stats["quantifiable_achievements"] >= 5:
        score += 15
    elif stats["quantifiable_achievements"] >= 3:
        score += 10
    else:
        score += 5

    if stats["has_email"] and stats["has_phone"]:
        score += 20
    elif stats["has_email"] or stats["has_phone"]:
        score += 10

    if 15 <= stats["avg_sentence_length"] <= 25:
        score += 20
    elif 10 <= stats["avg_sentence_length"] <= 30:
        score += 15
    else:
        score += 10
    return min(score, 100)


def analyze_keywords(resume_text, job_description):
    resume_words = set(re.findall(r"\b[a-z]{3,}\b", resume_text.lower()))
    jd_words = set(re.findall(r"\b[a-z]{3,}\b", job_description.lower()))
    stop_words = {"the", "and", "for", "with", "this", "that", "from", "will", "are", "have", "has", "been", "were", "was"}
    resume_words -= stop_words
    jd_words -= stop_words
    matching_keywords = resume_words & jd_words
    missing_keywords = jd_words - resume_words
    match_percentage = (len(matching_keywords) / len(jd_words) * 100) if jd_words else 0
    return {
        "match_percentage": match_percentage,
        "matching_keywords": sorted(matching_keywords)[:20],
        "missing_keywords": sorted(missing_keywords)[:20],
        "total_jd_keywords": len(jd_words),
        "total_resume_keywords": len(resume_words),
    }


def suggest_action_verbs(text):
    weak_verbs = ("responsible for", "worked on", "helped", "assisted", "did", "made", "handled")
    strong_verbs = {
        "responsible for": ["managed", "oversaw", "directed", "coordinated"],
        "worked on": ["developed", "created", "built", "designed"],
        "helped": ["supported", "facilitated", "enabled", "contributed to"],
        "assisted": ["collaborated", "partnered", "coordinated with"],
        "did": ["executed", "performed", "completed", "delivered"],
        "made": ["created", "produced", "generated", "developed"],
        "handled": ["managed", "processed", "coordinated", "executed"],
    }
    text_lower = text.lower()
    return [
        {"weak": weak, "strong": strong_verbs[weak], "count": text_lower.count(weak)}
        for weak in weak_verbs if weak in text_lower
    ]


def build_resume_prompt(text, stats, score, analysis_mode, focus_areas, job_role):
    mode_instructions = {
        "Quick Scan": "Provide a brief overview with 3-5 key points only.",
        "Standard Analysis": "Provide detailed analysis with specific examples and recommendations.",
        "Deep Dive": "Provide comprehensive analysis with examples, industry comparisons, and step-by-step improvements.",
        "ATS Optimization": "Focus specifically on ATS compatibility, keyword optimization, and formatting for applicant tracking systems.",
    }
    if analysis_mode not in mode_instructions:
        analysis_mode = "Standard Analysis"
    return f"""You are an expert resume reviewer with 15+ years of experience in HR and recruitment.

**Analysis Mode:** {analysis_mode}
{mode_instructions[analysis_mode]}

**Focus Areas:** {', '.join(focus_areas)}

**Target Role:** {job_role if job_role else 'General applications'}

**Resume Statistics:**
- Word Count: {stats['word_count']}
- Action Verbs: {stats['action_verb_count']}
- Quantifiable Achievements: {stats['quantifiable_achievements']}
- Overall Score: {score}/100

**Resume Content:**
{text}

Please provide structured feedback in this format:

## Executive Summary
[Brief overall assessment]

## Key Strengths
[3-5 specific strengths with examples]

## Areas for Improvement
[Specific issues with examples from resume]

## Actionable Recommendations
[Concrete, prioritized suggestions]

## Next Steps
[Immediate actions to take]

Be specific, constructive, and actionable. Use plain Markdown headings without emojis or decorative symbols."""


def build_match_prompt(resume_text, job_description):
    return f"""Analyze how well this resume matches the job description.

**Job Description:**
{job_description}

**Resume:**
{resume_text}

Provide analysis in this format:

## Overall Match Assessment
[Percentage estimate and summary]

## Strong Matches
[Skills/experience that align well]

## Gaps Identified
[Missing qualifications or skills]

## Recommendations
[How to improve the match]

## Application Strategy
[Tips for applying to this role]

Use plain Markdown headings without emojis or decorative symbols."""


def build_cover_letter_prompt(resume_text, job_description, company, role, tone):
    return f"""Generate a professional cover letter based on this information:

**Candidate's Resume:**
{resume_text}

**Job Description:**
{job_description}

**Company:** {company if company else '[Company Name]'}
**Role:** {role if role else '[Job Title]'}
**Tone:** {tone}

Create a compelling cover letter that:
1. Opens with a strong hook
2. Highlights relevant experience from the resume
3. Shows enthusiasm for the role
4. Demonstrates knowledge of the company
5. Includes a clear call to action
6. Maintains {tone.lower()} tone throughout

Format it as a complete cover letter ready to send. Do not include emojis or decorative symbols."""


def build_tool_prompt(tool_name, text, target_industry="", target_role=""):
    prompts = {
        "Action Verb Replacer": f"""Analyze these resume bullet points and replace weak verbs with strong action verbs.

Input:
{text}

For each bullet point:
1. Identify weak verbs
2. Suggest stronger alternatives
3. Rewrite the bullet point

Format as:
**Original:** [original text]
**Issue:** [weak verb identified]
**Improved:** [rewritten with strong verb]
**Why Better:** [brief explanation]""",
        "Achievement Quantifier": f"""Transform these achievements into quantified, measurable statements.

Achievements:
{text}

For each achievement:
1. Identify what can be quantified (time saved, revenue, efficiency, etc.)
2. Suggest realistic metrics or percentages
3. Rewrite in STAR format (Situation, Task, Action, Result)

Provide before/after comparisons.""",
        "Bullet Point Improver": f"""Improve these resume bullet points to make them more impactful and professional.

Bullet Points:
{text}

For each bullet:
1. Start with a strong action verb
2. Add context and specifics
3. Include results/impact
4. Keep it concise (1-2 lines)

Show before/after for each.""",
        "Section Reorganizer": f"""Analyze this resume structure and provide recommendations.

Current Sections:
{text}

Target Industry: {target_industry if target_industry else 'General'}

Provide:
1. Optimal section order for this industry
2. Sections to add/remove
3. Content suggestions for each section
4. Industry-specific best practices""",
        "Interview Question Generator": f"""Based on this resume, generate likely interview questions and suggested answers.

Resume:
{text}

Target Role: {target_role if target_role else 'General'}

Provide:
1. 10 behavioral questions based on their experience
2. 5 technical questions related to their skills
3. 3 situational questions
4. Suggested answer frameworks for each

Format each as:
**Question:** [question]
**Why They'll Ask:** [reasoning]
**How to Answer:** [framework/tips]
**Example Answer:** [brief example]""",
    }
    if tool_name not in prompts:
        raise ValueError("Choose one of the available resume tools.")
    return f"{prompts[tool_name]}\n\nDo not include emojis or decorative symbols in your response."


def analyze_resume(file_name, file_bytes, analysis_mode="Standard Analysis", focus_areas=None,
                   job_role="", enable_scoring=True, enable_statistics=True,
                   enable_ats_check=True, enable_action_verbs=False):
    text = extract_text_from_file(file_name, file_bytes)
    if not text.strip():
        raise ValueError("The file appears empty or does not contain readable text.")

    stats = calculate_resume_statistics(text)
    score = calculate_overall_score(text, stats)
    prompt = build_resume_prompt(text, stats, score, analysis_mode, focus_areas or [], job_role)
    analysis = generate_gemini_content(prompt)
    ats = None
    if enable_ats_check:
        ats_score, ats_issues, ats_status = check_ats_compatibility(text)
        ats = {"score": ats_score, "issues": ats_issues, "status": ats_status}
    return {
        "filename": file_name,
        "stats": stats if enable_statistics or enable_scoring else None,
        "score": score if enable_scoring else None,
        "ats": ats,
        "action_verbs": suggest_action_verbs(text) if enable_action_verbs else None,
        "analysis": analysis,
        "full_report": generate_text_report(analysis, stats, score),
    }


def analyze_job_match(file_name, file_bytes, job_description, include_keywords=False):
    resume_text = extract_text_from_file(file_name, file_bytes)
    if not resume_text.strip():
        raise ValueError("The uploaded resume does not contain readable text.")
    if not job_description.strip():
        raise ValueError("Paste a job description to continue.")
    keyword_analysis = analyze_keywords(resume_text, job_description) if include_keywords else None
    analysis = generate_gemini_content(build_match_prompt(resume_text, job_description))
    return {"keywords": keyword_analysis, "analysis": analysis}


def generate_cover_letter(file_name, file_bytes, job_description, company="", role="", tone="Professional"):
    resume_text = extract_text_from_file(file_name, file_bytes)
    if not resume_text.strip():
        raise ValueError("The uploaded resume does not contain readable text.")
    if not job_description.strip():
        raise ValueError("Add the job description so the draft has role context.")
    return generate_gemini_content(build_cover_letter_prompt(resume_text, job_description, company, role, tone))


def generate_tool_output(tool_name, text, file_name=None, file_bytes=None,
                         target_industry="", target_role=""):
    if tool_name not in TOOLS:
        raise ValueError("Choose a valid resume tool.")
    if tool_name == "Interview Question Generator":
        if not file_name or not file_bytes:
            raise ValueError("Upload a PDF or TXT resume for interview preparation.")
        text = extract_text_from_file(file_name, file_bytes)
        if not text.strip():
            raise ValueError("The uploaded resume does not contain readable text.")
    elif not text.strip():
        raise ValueError("Enter resume content before running this tool.")
    return generate_gemini_content(build_tool_prompt(tool_name, text, target_industry, target_role))


def generate_text_report(analysis_text, stats, score):
    return f"""
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
Copyright 2025 AI Resume Analyzer Pro. All rights reserved.
"""
