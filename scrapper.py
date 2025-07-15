import os
import requests
import logging
import yaml
from dotenv import load_dotenv
import praw
import json
from pathlib import Path


# ----------------------- Logging Setup -----------------------
logging.basicConfig(
    filename='scraper.log',
    filemode='a',
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)

# ---------------------- Config Loader ------------------------
def load_config(path='config.yaml'):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def load_env(env_path):
    load_dotenv(dotenv_path=env_path)

# ------------------- Reddit API Scraper ----------------------
def fetch_reddit_data(username, limit=100):
    try:
        reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT")
        )
        user = reddit.redditor(username)

        posts = [post.title for post in user.submissions.new(limit=limit)]
        comments = [comment.body for comment in user.comments.new(limit=limit)]

        logging.info(f"Successfully fetched data using Reddit API for u/{username}")
        return {"posts": posts, "comments": comments}
    except Exception as e:
        logging.error(f"Reddit API failed for u/{username}: {e}")
        raise

# ------------------- Pushshift Scraper -----------------------
def fetch_pushshift_data(username, limit=100):
    try:
        post_url = f"https://api.pushshift.io/reddit/submission/search/?author={username}&size={limit}"
        comment_url = f"https://api.pushshift.io/reddit/comment/search/?author={username}&size={limit}"

        posts_resp = requests.get(post_url).json().get("data", [])
        comments_resp = requests.get(comment_url).json().get("data", [])

        posts = [p.get("title", "") for p in posts_resp if "title" in p]
        comments = [c.get("body", "") for c in comments_resp if "body" in c]

        logging.info(f"Successfully fetched data using Pushshift for u/{username}")
        return {"posts": posts, "comments": comments}
    except Exception as e:
        logging.error(f"Pushshift API failed for u/{username}: {e}")
        raise

# ------------------------ Main Logic -------------------------
def scrape_user(username):
    config = load_config("config.yaml")
    load_env(config["reddit"].get("env_file", ".env"))

    limit = config["reddit"].get("limit", 100)
    use_api = config["reddit"].get("use_api", True)
    fallback = config["reddit"].get("fallback_to_pushshift", True)

    try:
        if use_api:
            logging.info(f"Attempting Reddit API for u/{username}")
            return fetch_reddit_data(username, limit)
        else:
            raise RuntimeError("Reddit API disabled in config.")
    except Exception as api_error:
        if fallback:
            logging.warning(f"API failed, falling back to Pushshift for u/{username}")
            return fetch_pushshift_data(username, limit)
        else:
            logging.critical(f"Both Reddit API and Pushshift unavailable for u/{username}")
            raise RuntimeError("Both API and fallback failed.")

# -------------------------- Run ------------------------------
if __name__ == "__main__":
    import sys

    logging.info("\n" + "-" * 80)

    if len(sys.argv) > 1:
        uname = sys.argv[1]
    else:
        uname = input("🔍 Enter Reddit username (without u/): ").strip()

    try:
        user_data = scrape_user(uname)
        logging.info(f"✅ Finished scraping u/{uname}. {len(user_data['posts'])} posts, {len(user_data['comments'])} comments.")

        # Save to reddit/data/username.json (to match pipeline expectation)
        output_dir = Path("data/")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{uname}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=4, ensure_ascii=False)

        logging.info(f"💾 Saved data to {output_path}")
        print(f"✅ Data scraping complete. Saved to {output_path}. Check `scraper.log` for details.")
        
    except Exception as e:
        logging.critical(f"Scraping failed for u/{uname}: {e}")
        print("❌ Failed to fetch user data. Check `scraper.log` for errors.")
