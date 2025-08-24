import pandas as pd
import requests
import time
import json


def build_schema():
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "founder_owned": {"type": "string", "enum": ["Yes", "No", "Unsure"]},
            "explanation_founder_owned": {"type": "string"},
            "founder_on_mgmt_team": {"type": "string", "enum": ["Yes", "No", "Unsure"]},
            "explanation_founder_on_mgmt_team": {"type": "string"},
            "founder_on_board": {"type": "string", "enum": ["Yes", "No", "Unsure"]},
            "explanation_founder_on_board": {"type": "string"},
            "majority_acquired": {"type": "string", "enum": ["Yes", "No", "Unsure"]},
            "explanation_majority_acquired": {"type": "string"},
            "current_investors": {"type": "array", "items": {"type": "string"}},
            "explanation_current_investors": {"type": "string"},
            "board_of_directors": {"type": "array", "items": {"type": "string"}},
            "explanation_board_of_directors": {"type": "string"},
            "board_size": {"type": "integer", "minimum": 0},
            "explanation_board_size": {"type": "string"},
            "investors_represented_on_board": {"type": "integer", "minimum": 0},
            "explanation_investors_represented_on_board": {"type": "string"}
        },
        "required": [
            "founder_owned",
            "explanation_founder_owned",
            "founder_on_mgmt_team",
            "explanation_founder_on_mgmt_team",
            "founder_on_board",
            "explanation_founder_on_board",
            "majority_acquired",
            "explanation_majority_acquired",
            "current_investors",
            "explanation_current_investors",
            "board_of_directors",
            "explanation_board_of_directors",
            "board_size",
            "explanation_board_size",
            "investors_represented_on_board",
            "explanation_investors_represented_on_board"
        ]
    }


# 1) Load your CSV (must contain: company_name, web_site)
INPUT_PATH = "step_1_output_companies_with_llm_generated_summaries.csv"
OUTPUT_PATH = "final_output_complete_proptech_companies_analysis.csv"

# Read CSV and handle NaN values immediately
df = pd.read_csv(INPUT_PATH)
df = df.fillna('')  # Replace all NaN with empty strings

# Filter out rows with empty or invalid company names
print(f"📊 Initial rows loaded: {len(df)}")
df_filtered = df[
    (df['company_name'].notna()) &
    (df['company_name'].str.strip() != '') &
    (df['company_name'].str.lower() != 'nan')
    ].copy()

print(f"📊 Valid companies found: {len(df_filtered)}")

# Stop execution if no valid companies found
if len(df_filtered) == 0:
    print("❌ No valid companies found in the CSV file. Stopping execution.")
    exit()

# Reset index for the filtered dataframe
df_filtered.reset_index(drop=True, inplace=True)

# 2) Function to query the Perplexity AI Completion API
API_URL = "https://api.perplexity.ai/chat/completions"

API_KEY = ""

MODEL = "sonar-pro"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = (
    "You are an expert Private Equity analyst with access to real-time web data. "
    "Your objective is to evaluate companies as potential acquisition opportunities. "
    "Using the company information provided, specifically the column llm_response with full detail of the company funding history "
    "extract the following information and return it in valid JSON format:\n"
    "{\n"
    '  "founder_owned": "Yes, No, or Unsure - based on ownership information found",\n'
    '  "explanation_founder_owned": "max 20 words explaining how this conclusion was reached. Which sources were searched",\n'
    '  "founder_on_mgmt_team": "Yes or No - based on management team information",\n'
    '  "explanation_founder_on_mgmt_team": "max 20 words explaining how this conclusion was reached. Which sources were searched",\n'
    '  "founder_on_board": "Yes, No, or Unsure - based on board information found",\n'
    '  "explanation_founder_on_board": "max 20 words explaining how this conclusion was reached. Which sources were searched",\n'
    '  "majority_acquired": "Yes, No, or Unsure - based on acquisition/investment history",\n'
    '  "explanation_majority_acquired": "max 20 words explaining how this conclusion was reached. Which sources were searched",\n'
    '  "current_investors": "list of current institutional investors (exclude those who have exited)",\n'
    '  "explanation_current_investors": "max 20 words explaining how this conclusion was reached. Which sources were searched",\n'
    '  "board_of_directors": "list of current board members",\n'
    '  "explanation_board_of_directors": "max 20 words explaining how this conclusion was reached. Which sources were searched",\n'
    '  "board_size": "count of individuals in Board of Directors as integer",\n'
    '  "explanation_board_size": "max 20 words explaining how this conclusion was reached. Which sources were searched",\n'
    '  "investors_represented_on_board": "count of board members representing institutional investors as integer"\n'
    '  "explanation_investors_represented_on_board": "max 20 words explaining how this conclusion was reached. Which sources were searched",\n'
    "}\n"
    "Focus on finding explicit information about ownership structure, governance, and investor relationships. "
    "If specific data is not available, use 'Unsure' for yes/no fields, empty arrays for lists, "
    "0 for counts, and 'Information not found' for explanation fields."
)


def call_llm_json_only(row_data, max_tokens=1500, retry=1):
    messages = [
        {"role": "system", "content": (
                SYSTEM_PROMPT +
                "\nOutput ONLY a JSON object that validates against the provided schema."
        )},
        {"role": "user", "content": (
                "Company information:\n" +
                json.dumps(row_data, ensure_ascii=False) +
                "\nReturn ONLY a JSON object that matches the schema."
        )}
    ]

    payload = {
        "model": MODEL,  # e.g. "sonar-pro"
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "pe_company_analysis",
                "schema": build_schema()
            }
        }
    }

    r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=120)
    if r.status_code >= 400:
        print("Status:", r.status_code)
        print("Body:", r.text)
    r.raise_for_status()
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    finish_reason = data["choices"][0].get("finish_reason")

    # First parse attempt
    try:
        return json.loads(content), finish_reason
    except json.JSONDecodeError:
        if retry > 0:
            # Retry: ask to reprint JSON only
            payload["messages"].append({
                "role": "user",
                "content": "Your previous output did not parse. Reprint ONLY the full JSON object."
            })
            payload["max_tokens"] = max_tokens + 500
            r2 = requests.post(API_URL, json=payload, headers=HEADERS, timeout=120)
            if r2.status_code >= 400:
                print("Status:", r2.status_code)
                print("Body:", r2.text)
            r2.raise_for_status()
            content2 = r2.json()["choices"][0]["message"]["content"]
            try:
                return json.loads(content2), r2.json()["choices"][0].get("finish_reason")
            except json.JSONDecodeError:
                # last-ditch: slice braces
                start = content2.find("{")
                end = content2.rfind("}")
                if start != -1 and end != -1 and end > start:
                    return json.loads(content2[start:end + 1]), "repaired"
        # Give up—let caller fall back to empty structure
        raise


def extract_company_data(row) -> dict:
    row_data = {k: ('' if (pd.isna(v) or str(v).lower() == 'nan') else v) for k, v in row.to_dict().items()}
    try:
        extracted, finish_reason = call_llm_json_only(row_data)
        # Optional: log finish_reason to see if you’re hitting "length"
        if finish_reason == "length":
            print("⚠️ finish_reason=length (hit token cap). Consider increasing max_tokens.")
        return extracted
    except Exception as e:
        company_name = row_data.get('company_name', 'Unknown')
        print(f"❌ Error processing {company_name}: {e}")
        return get_empty_data_structure()


def get_empty_data_structure():
    return {
        "founder_owned": "Unsure",
        "explanation_founder_owned": "Extraction failed",
        "founder_on_mgmt_team": "Unsure",
        "explanation_founder_on_mgmt_team": "Extraction failed",
        "founder_on_board": "Unsure",
        "explanation_founder_on_board": "Extraction failed",
        "majority_acquired": "Unsure",
        "explanation_majority_acquired": "Extraction failed",
        "current_investors": [],
        "explanation_current_investors": "Extraction failed",
        "board_of_directors": [],
        "explanation_board_of_directors": "Extraction failed",
        "board_size": 0,
        "explanation_board_size": "Extraction failed",
        "investors_represented_on_board": 0,
        "explanation_investors_represented_on_board": "Extraction failed"
    }


# 3) Process each valid company
extracted_data_list = []
opportunity_scores = []
opportunity_levels = []
total_companies = len(df_filtered)

for idx, row in df_filtered.iterrows():
    company_name = row['company_name']
    current_position = idx + 1

    print(f"🔍 Processing ({current_position}/{total_companies}): {company_name}")

    extracted_data = extract_company_data(row)
    # --- Compute opportunity score & level ---
    founder_owned = extracted_data.get("founder_owned", "Unsure")
    founder_mgmt = extracted_data.get("founder_on_mgmt_team", "Unsure")
    majority_acq = extracted_data.get("majority_acquired", "Unsure")

    opportunity_score = 0
    if founder_owned == "Yes": opportunity_score += 3
    if founder_mgmt == "Yes": opportunity_score += 2
    if founder_on_board == "Yes": opportunity_score += 1
    if majority_acq == "No": opportunity_score += 1

    opportunity_level = (
        "High" if opportunity_score >= 5 else
        "Medium" if opportunity_score >= 3 else
        "Low"
    )

    extracted_data_list.append(extracted_data)
    opportunity_scores.append(opportunity_score)
    opportunity_levels.append(opportunity_level)

    time.sleep(1.5)  # Rate limiting

    # Optional: Add a checkpoint every 10 companies
    if current_position % 10 == 0:
        print(f"📈 Checkpoint: Processed {current_position}/{total_companies} companies")

print(f"🎉 All {total_companies} companies processed successfully!")

# 4) Add new columns to the filtered dataframe
df_filtered["founder_owned"] = [data["founder_owned"] for data in extracted_data_list]
df_filtered["explanation_founder_owned"] = [data["explanation_founder_owned"] for data in extracted_data_list]

df_filtered["founder_on_mgmt_team"] = [data["founder_on_mgmt_team"] for data in extracted_data_list]
df_filtered["explanation_founder_on_mgmt_team"] = [data["explanation_founder_on_mgmt_team"] for data in
                                                   extracted_data_list]

df_filtered["founder_on_board"] = [data["founder_on_board"] for data in extracted_data_list]
df_filtered["explanation_founder_on_board"] = [data["explanation_founder_on_board"] for data in extracted_data_list]

df_filtered["majority_acquired"] = [data["majority_acquired"] for data in extracted_data_list]
df_filtered["explanation_majority_acquired"] = [data["explanation_majority_acquired"] for data in extracted_data_list]

df_filtered["current_investors"] = [data["current_investors"] for data in extracted_data_list]

df_filtered["board_of_directors"] = [data["board_of_directors"] for data in extracted_data_list]

df_filtered["board_size"] = [data["board_size"] for data in extracted_data_list]

df_filtered["investors_represented_on_board"] = [data["investors_represented_on_board"] for data in extracted_data_list]
# --- Add the new columns ---
df_filtered["opportunity_score"] = opportunity_scores
df_filtered["opportunity_level"] = opportunity_levels

# 5) Save to disk
df_filtered.to_csv(OUTPUT_PATH, index=False)
print(f"✅ Finished. File written to {OUTPUT_PATH}")

# 6) Display Private Equity relevant summary statistics
print(f"\n📊 Private Equity Analysis Summary:")
print(f"Total companies processed: {len(df_filtered)}")
print(f"Founder-owned companies: {(df_filtered['founder_owned'] == 'Yes').sum()}")
print(f"Companies with founder on management team: {(df_filtered['founder_on_mgmt_team'] == 'Yes').sum()}")
print(f"Companies with founder on board: {(df_filtered['founder_on_board'] == 'Yes').sum()}")
print(f"Companies with majority acquisition: {(df_filtered['majority_acquired'] == 'Yes').sum()}")
print(f"Average board size: {df_filtered['board_size'].mean():.1f}")

print(f"\n🔍 Sample Explanations:")
for idx in range(min(2, len(df_filtered))):
    company = df_filtered.iloc[idx]['company_name']
    print(f"\n{company}:")
    print(f"  Founder ownership source: {df_filtered.iloc[idx]['explanation_founder_owned']}")
    print(f"  Management team source: {df_filtered.iloc[idx]['explanation_founder_on_mgmt_team']}")
    print(f"  Board information source: {df_filtered.iloc[idx]['explanation_founder_on_board']}")
