import pandas as pd
import requests
import time
import re
from typing import Dict, List, Tuple, Any


def _extract_sources(resp_json: Dict[str, Any]) -> List[str]:
    """
    Get a flat list of source URLs from Perplexity response.
    Prefers 'search_results'; falls back to 'citations' if present.
    """
    urls = []

    # Primary: 'search_results' at top level
    for item in resp_json.get("search_results", []) or []:
        url = item.get("url")
        if url:
            urls.append(url)

    # Fallbacks people sometimes see in the wild
    # 1) message-level 'citations': could be list[str] or list[dict]
    try:
        msg = resp_json["choices"][0]["message"]
        cits = msg.get("citations")
        if cits:
            if isinstance(cits, list):
                for c in cits:
                    if isinstance(c, str):
                        urls.append(c)
                    elif isinstance(c, dict) and "url" in c:
                        urls.append(c["url"])
    except Exception:
        pass

    # De-dup preserving order
    seen = set()
    deduped = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped


def _inline_replace_citation_numbers(text: str, urls: List[str]) -> str:
    """
    Replace every [N] in the text with [<corresponding URL>].
    Leaves tokens intact if no matching URL exists.
    Handles consecutive refs like ...[1][3].
    """

    def repl(match: re.Match) -> str:
        n = match.group(1)  # the number inside brackets
        try:
            idx = int(n) - 1
            if 0 <= idx < len(urls):
                return f"[{urls[idx]}]"
        except ValueError:
            pass
        # If not a valid mapping, return original token
        return match.group(0)

    return re.sub(r"\[(\d+)\]", repl, text)


def query_perplexity_api(prompt: str, api_key: str) -> Tuple[str, List[str]]:
    """
    Send a query to Perplexity API and return (content, source_urls).
    """
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                # Optional nudge to include bracketed refs in content we can swap out:
                "content": "When citing, use bracketed numeric citations like [1], [2], etc. Keep facts precise."
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1000,
        "temperature": 0.2,
    }

    resp = requests.post(url, json=data, headers=headers)
    resp.raise_for_status()
    resp_json = resp.json()

    content = resp_json["choices"][0]["message"]["content"]
    source_urls = _extract_sources(resp_json)
    return content, source_urls


def process_companies(input_csv: str, output_csv: str, api_key: str) -> None:
    """
    Process the CSV file and add LLM responses with inline URL citations.
    """
    df = pd.read_csv(input_csv)

    llm_responses = []
    llm_sources = []  # optional: store sources as a pipe-joined list too

    for _, row in df.iterrows():
        company_name = row["company_name"]
        web_site = row["web_site"]

        prompt= (
            f"Please provide {company_name} workplace management company funding "
            f"history and current ownership structure. Check if the company undergo a majority acquisition."
            f"Website is {web_site}. Specify who is/are the founders. "
            f"Include current investors and board of directors."
            f"Be as specific and detailed as possible. "
            f"Try to obtain a list of it's leadership, including their job titles. Use the "
            f"specific website provided for this."
            f"Try searching on a section called Leadership or in the About "
            f"section, look for 'The Team' or 'Leadership' or under a section called 'Company' or under 'About Us' or under 'Who we are' or under About-->Leadership"
            f"or use your common sense to search the website."
            f"If you still don't find any leadership information, try looking for it in other sources. "
            f"First source you should look at is LinkedIn, search for the company and get the first 10 people "
            f"with Leadership roles that appear as People with their job titles."
        )


        print(f"Processing {company_name}...")

        try:
            content, urls = query_perplexity_api(prompt, api_key)
            print(content)
            content_with_inline_urls = _inline_replace_citation_numbers(content, urls)
            llm_responses.append(content_with_inline_urls)
            llm_sources.append(" | ".join(urls))
        except Exception as e:
            err = f"Error: {e}"
            llm_responses.append(err)
            llm_sources.append("")

        time.sleep(1)  # gentle pacing

    df["llm_response"] = llm_responses
    # Optional but handy: keep the full source list in a separate column
    df["llm_sources"] = llm_sources

    df.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"Results saved to {output_csv}")


if __name__ == "__main__":
    API_KEY = ""
    INPUT_CSV = "step_1_input_companies_data.csv"
    OUTPUT_CSV = "step_1_output_companies_with_llm_generated_summaries.csv"
    process_companies(INPUT_CSV, OUTPUT_CSV, API_KEY)

