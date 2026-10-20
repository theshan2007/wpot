"""
WordPress Auto-Posting Bot
==========================
WordPress REST API use කරලා posts automatically publish කරන bot.

Requirements:
    pip install requests python-dotenv

Setup:
    1. .env file එකේ credentials දාන්න
    2. python wp_bot.py run
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Configuration ───────────────────────────────────────────────────────────

WP_URL      = os.getenv("WP_URL", "https://yoursite.com")       # WordPress site URL
WP_USER     = os.getenv("WP_USER", "your_username")             # WordPress username
WP_PASSWORD = os.getenv("WP_PASSWORD", "your_app_password")     # Application Password

# ─── WordPress API Client ─────────────────────────────────────────────────────

class WordPressBot:
    def __init__(self, url: str, username: str, password: str):
        self.base_url = url.rstrip("/")
        self.api_url  = f"{self.base_url}/wp-json/wp/v2"
        self.auth     = (username, password)

    def _request(self, method: str, endpoint: str, **kwargs):
        """Generic API request helper."""
        url = f"{self.api_url}/{endpoint}"
        response = requests.request(method, url, auth=self.auth, **kwargs)
        if not response.ok:
            print(f"[ERROR] {response.status_code}: {response.text}")
            response.raise_for_status()
        return response.json()

    def test_connection(self):
        """WordPress connection test කරන්න."""
        try:
            data = self._request("GET", "users/me")
            print(f"[OK] Connected as: {data['name']} ({data['email']})")
            return True
        except Exception as e:
            print(f"[FAIL] Connection failed: {e}")
            return False

    def create_post(
        self,
        title: str,
        content: str,
        status: str = "publish",
        categories: list[int] = None,
        tags: list[int] = None,
        excerpt: str = "",
        featured_media: int = None,
    ) -> dict:
        """
        New post එකක් create කරන්න.

        Args:
            title:          Post title
            content:        Post body (HTML supported)
            status:         'publish', 'draft', 'pending', 'private'
            categories:     List of category IDs
            tags:           List of tag IDs
            excerpt:        Short description
            featured_media: Attachment ID for featured image
        """
        payload = {
            "title":   title,
            "content": content,
            "status":  status,
            "excerpt": excerpt,
        }
        if categories:
            payload["categories"] = categories
        if tags:
            payload["tags"] = tags
        if featured_media:
            payload["featured_media"] = featured_media

        result = self._request("POST", "posts", json=payload)
        print(f"[POST] '{result['title']['rendered']}' → {result['link']}")
        return result

    def update_post(self, post_id: int, **fields) -> dict:
        """Existing post එකක් update කරන්න."""
        result = self._request("POST", f"posts/{post_id}", json=fields)
        print(f"[UPDATE] Post {post_id} updated → {result['link']}")
        return result

    def delete_post(self, post_id: int, force: bool = False):
        """Post එකක් delete කරන්න (force=True = trash bypass)."""
        result = self._request("DELETE", f"posts/{post_id}", params={"force": force})
        print(f"[DELETE] Post {post_id} deleted.")
        return result

    def list_posts(self, per_page: int = 10, status: str = "any") -> list[dict]:
        """Recent posts list කරන්න."""
        data = self._request("GET", "posts", params={"per_page": per_page, "status": status})
        for p in data:
            print(f"  [{p['id']}] {p['status']:10s} {p['title']['rendered']}")
        return data

    def get_categories(self) -> list[dict]:
        """Available categories list කරන්න."""
        data = self._request("GET", "categories", params={"per_page": 100})
        for c in data:
            print(f"  [{c['id']}] {c['name']}")
        return data

    def bulk_post_from_json(self, json_file: str):
        """
        JSON file එකෙන් bulk posts publish කරන්න.
        JSON format: [ { "title": "...", "content": "...", "status": "publish" }, ... ]
        """
        path = Path(json_file)
        if not path.exists():
            print(f"[ERROR] File not found: {json_file}")
            return

        with open(path, encoding="utf-8") as f:
            posts = json.load(f)

        print(f"[BULK] Publishing {len(posts)} posts from {json_file}...")
        results = []
        for i, post in enumerate(posts, 1):
            try:
                result = self.create_post(**post)
                results.append({"id": result["id"], "link": result["link"], "status": "ok"})
                print(f"  ({i}/{len(posts)}) Done")
            except Exception as e:
                results.append({"error": str(e), "status": "fail"})
                print(f"  ({i}/{len(posts)}) FAILED: {e}")

        # Save results log
        log_file = f"bulk_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"[BULK] Log saved to {log_file}")


# ─── CLI Interface ────────────────────────────────────────────────────────────

def print_usage():
    print("""
Usage: python wp_bot.py <command> [args]

Commands:
  test                         - Connection test කරන්න
  post <title> <content>       - Single post publish කරන්න
  draft <title> <content>      - Draft post save කරන්න
  list [count]                 - Recent posts list කරන්න (default: 10)
  categories                   - Categories list කරන්න
  bulk <posts.json>            - JSON file එකෙන් bulk posts publish කරන්න
  delete <post_id>             - Post delete කරන්න

Examples:
  python wp_bot.py test
  python wp_bot.py post "My Title" "My content here"
  python wp_bot.py list 5
  python wp_bot.py bulk posts.json
  python wp_bot.py delete 42
""")


def main():
    bot = WordPressBot(WP_URL, WP_USER, WP_PASSWORD)

    if len(sys.argv) < 2:
        print_usage()
        return

    cmd = sys.argv[1].lower()

    if cmd == "test":
        bot.test_connection()

    elif cmd == "post" and len(sys.argv) >= 4:
        bot.create_post(title=sys.argv[2], content=sys.argv[3], status="publish")

    elif cmd == "draft" and len(sys.argv) >= 4:
        bot.create_post(title=sys.argv[2], content=sys.argv[3], status="draft")

    elif cmd == "list":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        bot.list_posts(per_page=count)

    elif cmd == "categories":
        bot.get_categories()

    elif cmd == "bulk" and len(sys.argv) >= 3:
        bot.bulk_post_from_json(sys.argv[2])

    elif cmd == "delete" and len(sys.argv) >= 3:
        bot.delete_post(int(sys.argv[2]))

    else:
        print("[ERROR] Invalid command or missing arguments.")
        print_usage()


if __name__ == "__main__":
    main()
