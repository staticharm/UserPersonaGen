import json
import os
import subprocess
import requests

# ==== CONFIG ====
GROQ_API_KEY = ""
GROQ_MODEL = "llama3-70b-8192"
SCRAPER_SCRIPT = "scrapper.py"  # Assumes you can call this as `python scraper.py <username>`
DATA_DIR = "data/"
OUTPUT_DIR = "output"

# ==== ASK FOR USERNAME ====
username = input("Enter Reddit username: ").strip()
json_path = os.path.join(DATA_DIR, f"{username}.json")
output_path = os.path.join(OUTPUT_DIR, f"{username}.txt")

# ==== STEP 1: RUN SCRAPER ====
print(f"[•] Running scraper for u/{username}...")
try:
    subprocess.run(["python", SCRAPER_SCRIPT, username], check=True)
except subprocess.CalledProcessError as e:
    print(f"❌ Scraper failed: {e}")
    exit(1)

# ==== STEP 2: LOAD SCRAPED JSON ====
if not os.path.exists(json_path):
    print(f"❌ Expected JSON file not found: {json_path}")
    exit(1)

with open(json_path, "r", encoding="utf-8") as f:
    user_data = json.load(f)

MAX_POSTS = 20
MAX_COMMENTS = 30
user_data["posts"] = user_data.get("posts", [])[:MAX_POSTS]
user_data["comments"] = user_data.get("comments", [])[:MAX_COMMENTS]

# Now prepare joined text for the prompt
posts = "\n".join(user_data["posts"])
comments = "\n".join(user_data["comments"])

posts = "\n".join(user_data.get("posts", []))
comments = "\n".join(user_data.get("comments", []))

# ==== STEP 3: FORMAT PROMPT ====
prompt = f"""
You are an expert Reddit persona analyst.

Below is the Reddit activity of a user:
Posts:
{posts}

Comments:
{comments}

Using the data, generate a comprehensive markdown-based user persona report using the following structure.

IMPORTANT:
- DO NOT include any explanations or extra text.
- Return your response **only** in the format below.
- Where information is missing or unclear, write "N/A" or a helpful placeholder message.
- Use direct quotes or paraphrases from the Reddit content when possible to support insights.

Return the persona as markdown text in this exact structure:

## {username}

---

### 🧾 Summary
<short summary of the user>

---

### 👤 Basic Info
- **Age:** <value>
- **Occupation:** <value>
- **Status:** <value>
- **Location:** <value>
- **Tier:** <value>
- **Archetype:** <value>

---

### 🧠 Personality (MBTI Style)
| Trait        | Value     |
|--------------|-----------|
| Introvert–Extrovert | <value> |
| Intuition–Sensing  | <value> |
| Feeling–Thinking   | <value> |
| Perceiving–Judging | <value> |

---

### ⚡ Motivations
| Factor           | Strength |
|------------------|----------|
| Convenience      | <value> |
| Wellness         | <value> |
| Speed            | <value> |
| Preferences      | <value> |
| Comfort          | <value> |
| Dietary Needs    | <value> |

---

### 🔁 Behaviour & Habits
<summary of user behavior and lifestyle>

**Citations (Behaviour):**
- <citation 1>
- <citation 2>

---

### 😤 Frustrations
<summary of user's main frustrations>

**Citations (Frustrations):**
- <citation 1>
- <citation 2>

---

### 🎯 Goals & Needs
<summary of user's goals and needs>

**Citations (Goals):**
- <citation 1>
- <citation 2>

---

### 🗳️ Political
<summary or placeholder about user's political inclinations>

**Citations (Political):**
- <citation if available>
"""

# ==== STEP 4: CALL LLM ====
print("[•] Calling Groq LLaMA model...")
response = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    },
)

try:
    result = response.json()["choices"][0]["message"]["content"]
except Exception as e:
    print("❌ Failed to parse model output:", e)
    print("Full response:", response.text)
    exit(1)

# ==== STEP 5: SAVE OUTPUT ====
os.makedirs(OUTPUT_DIR, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    f.write(result)

print(f"[✓] Persona for u/{username} saved to {output_path}")
