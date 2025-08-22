# pe-opportunities
# PropTech Company Analysis – Usage Documentation

This project provides a two-step workflow for analyzing PropTech companies as potential Private Equity opportunities using the Perplexity API.

---

## 1. Getting a Perplexity API Key
1. Go to [https://perplexity.ai](https://perplexity.ai).
2. Log in (or create an account if you don’t have one).
3. Navigate to **Settings → API Keys**.
4. Click **Generate New Key**.
5. Copy the generated key and store it safely.
   - ⚠️ Treat this key like a password — do not share it publicly.

---

## 2. Running the Code in PyCharm
1. Open **PyCharm** on your computer.
2. Create a new project or open the folder where the scripts (`step_1_company_information_enrichment.py` and `step_2_structured_private_equity_analysis.py`) are stored.
3. Place your company CSV file in the same folder (e.g., `step_1_input_companies_data.csv`).
4. Open the script you want to run.
5. At the top menu, select **Run → Run 'script_name'**.
6. Results will be written to a new CSV file in the same folder (e.g., `step_1_output_companies_with_llm_generated_summaries.csv`, `final_output_complete_protech_companies_analysis.csv`).

---

## 3. Required Python Libraries
Before running the scripts, install the following libraries:

```bash
pip install pandas requests
```

- **pandas** → for reading/writing CSV files and managing data tables.
- **requests** → for making calls to the Perplexity API.

*(The `time`, `json`, `re`, and `typing` modules are built into Python, so no installation is required.)*

---

## 4. Setting the API Key in the Code
1. Open the script in PyCharm.
2. Find the line that looks like this (in both scripts):

```python
API_KEY = ""
```

3. Replace the empty string with your Perplexity API key:

```python
API_KEY = "your_actual_api_key_here"
```

4. Save the file.
5. Now when you run the script, it will authenticate using your key.

---

## 5. Workflow Overview
- **step_1_company_information_enrichment.py**: Enriches company information with funding history, ownership structure, and governance details.
- **step_2_structured_private_equity_analysis.py**: Structures the responses, extracts PE-relevant signals, and scores opportunities (High/Medium/Low).

---

## 6. Output
- **step_1_output_companies_with_llm_generated_summaries.csv** → AI-generated narratives with inline sources.
- **final_output_complete_protech_companies_analysis.csv** → Structured dataset with founder ownership, governance details, investor info, and opportunity scoring.

---

✅ You are ready to run the full workflow and analyze PropTech companies as investment opportunities.
