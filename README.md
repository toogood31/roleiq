# WorkAlign Project

An AI-driven platform for resume-JD matching, analyzing seniority, competencies, and business context.

## Setup Instructions
1. Navigate to the project folder: cd /path/to/workalign (e.g., cd ~/Desktop/workalign)
2. Activate the virtual environment: source workalign_env/bin/activate
3. Install dependencies (if needed): pip install -r requirements.txt
4. Run the app: streamlit run app.py

## Project Structure
- **app.py**: Main Streamlit user interface for uploading resumes and JDs.
- **api.py**: Optional Flask backend for API endpoints (if expanded).
- **utils/**: Helper scripts for processing.
  - parser.py: Document parsing functions.
  - extractor.py: Feature extraction (skills, seniority).
  - matcher.py: Matching and scoring logic.
  - optimizer.py: Optimization suggestions.
- **data/**: Data storage.
  - ontologies/: Skill graphs and hierarchies (e.g., ESCO CSV).
  - samples/: Test resumes and JDs.
- **requirements.txt**: List of Python dependencies.
- **workalign_env/**: Virtual environment (ignore in Git).

## Next Steps
- Download data for Step 3.
- Add code to the utils files.