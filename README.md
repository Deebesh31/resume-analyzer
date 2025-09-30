# AI Resume Analyzer Pro

A sophisticated AI-powered resume analysis tool built with Streamlit and Google's Gemini AI. Get professional feedback on your resume, match it against job descriptions, generate cover letters, and access powerful resume enhancement tools.

## Features

### Core Features
- **AI-Powered Resume Analysis**: Get detailed feedback from Google's Gemini AI on resume quality, structure, and content
- **Resume Scoring System**: Receive a comprehensive score (0-100) based on industry standards
- **ATS Compatibility Check**: Ensure your resume passes Applicant Tracking Systems
- **Keyword Analysis**: Match your resume against job descriptions to identify gaps
- **Action Verb Analysis**: Detect weak phrases and get suggestions for stronger alternatives

### Advanced Tools
- **Job Matcher**: Compare your resume against job descriptions with keyword matching
- **Cover Letter Generator**: Create tailored cover letters in multiple tones
- **Analysis History**: Track improvements across multiple resume versions
- **Resume Enhancement Tools**:
  - Action Verb Replacer
  - Achievement Quantifier
  - Bullet Point Improver
  - Section Reorganizer
  - Interview Question Generator

### Analysis Modes
- **Quick Scan**: Brief overview with key points
- **Standard Analysis**: Detailed analysis with examples
- **Deep Dive**: Comprehensive analysis with industry comparisons
- **ATS Optimization**: Focus on applicant tracking system compatibility

## Prerequisites

- Python 3.11 or higher
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/Deebesh31/resume-analyzer.git
cd resume-analyzer
```

### 2. Create a virtual environment
```bash
# Using venv
python -m venv .venv

# Activate on Windows
.venv\Scripts\activate

# Activate on Mac/Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install streamlit PyPDF2 google-generativeai python-dotenv matplotlib
```

Or if using `uv` (faster):
```bash
uv pip install -r requirements.txt
```

### 4. Set up environment variables
Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

**Important**: Never commit your `.env` file to version control. It's already included in `.gitignore`.

## Usage

### Run the application
```bash
streamlit run main.py
```

The app will open in your default browser at `http://localhost:8501`

### Basic Workflow
1. **Upload Resume**: Upload your resume in PDF or TXT format
2. **Select Analysis Mode**: Choose from Quick Scan, Standard, Deep Dive, or ATS Optimization
3. **Configure Settings**: Select focus areas and enable/disable features in the sidebar
4. **Analyze**: Click "Analyze Resume" to get AI-powered feedback
5. **Download Results**: Export your analysis report

### Additional Features
- **Job Matcher**: Upload resume + paste job description to see match percentage
- **Cover Letter Generator**: Generate tailored cover letters based on your resume
- **History**: Track and compare multiple resume versions
- **Tools**: Use enhancement tools to improve specific aspects of your resume

## Project Structure

```
resume-analyzer/
├── main.py                 # Main Streamlit application
├── .env                    # Environment variables (not committed)
├── .gitignore             # Git ignore file
├── pyproject.toml         # Project configuration
├── uv.lock                # Dependency lock file
├── README.md              # This file
└── .python-version        # Python version specification
```

## Configuration

### Sidebar Settings
- **Analysis Mode**: Choose depth of analysis
- **Focus Areas**: Select specific aspects to analyze
- **Feature Toggles**: Enable/disable scoring, statistics, ATS checks, etc.

### Supported File Formats
- PDF (`.pdf`)
- Plain Text (`.txt`)

## API Usage and Costs

This application uses Google's Gemini API. Be aware of potential costs:

- **Gemini 2.0 Flash**: Approximately $0.01-0.05 per resume analysis
- Free tier available with rate limits
- Consider implementing usage limits for public deployments

### Cost Management Options
1. Add session-based rate limiting
2. Require users to provide their own API keys
3. Implement user authentication with quotas

## Deployment

### Streamlit Community Cloud (Free)
1. Push your code to GitHub (already done!)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Select this repository
5. Add your `GEMINI_API_KEY` in "Advanced settings" > "Secrets"
6. Deploy

### Adding Secrets on Streamlit Cloud
In the Streamlit Cloud dashboard, add:
```toml
GEMINI_API_KEY = "your_api_key_here"
```

### Other Deployment Options
- **Railway**: Connect GitHub repo, add environment variables
- **Render**: Connect GitHub, configure as web service
- **Heroku**: Use Heroku CLI to deploy
- **Docker**: Build and deploy as container

## Security Notes

- Never commit `.env` files to version control
- Keep your API keys secret
- Rotate API keys regularly
- Consider implementing authentication for production use
- Add rate limiting to prevent API abuse

## Troubleshooting

### Common Issues

**"GEMINI_API_KEY not found"**
- Ensure `.env` file exists in project root
- Verify the key is correctly formatted
- Check that `python-dotenv` is installed

**"Error reading PDF"**
- Ensure PDF is not password-protected
- Try converting to a different PDF format
- Check file size (keep under 10MB)

**"Module not found"**
- Activate virtual environment
- Run `pip install -r requirements.txt`

**Rate limit errors**
- You've exceeded API quota
- Wait or upgrade your API plan
- Implement usage limits

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [Google Gemini AI](https://deepmind.google/technologies/gemini/)
- PDF parsing with [PyPDF2](https://pypdf2.readthedocs.io/)

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact: [Your contact info]

## Roadmap

- [ ] Add support for DOCX files
- [ ] Implement user authentication
- [ ] Add multiple language support
- [ ] Create resume templates library
- [ ] Add LinkedIn profile analyzer
- [ ] Implement resume builder from scratch
- [ ] Add industry-specific analysis modes

## Changelog

### Version 1.0.0 (2025-01-XX)
- Initial release
- Core resume analysis features
- Job matcher and cover letter generator
- Resume enhancement tools
- Analysis history and comparison

---

Made with Streamlit and Gemini AI | © 2025
