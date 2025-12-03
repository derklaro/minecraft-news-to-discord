import os
import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
}


def to_minecraft_url(path):
    return f"https://www.minecraft.net{path}"


def create_http_session():
    retry = Retry(total=10, backoff_factor=2, backoff_max=10, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET", "POST"], respect_retry_after_header=False)
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    return session


def fetch_articles(http_session, feed_url):
    response = http_session.get(feed_url, timeout=30, headers=BROWSER_HEADERS)
    response.raise_for_status()
    response_json = response.json()
    return response_json["article_grid"]


def format_article_message_content(article):
    return f"## {article['category']}: {article['title']}\n-# {article['sub_header']}\n\n<{article['url']}>"


def convert_feed_to_articles(articles_from_feed):
    result = []
    for article in articles_from_feed:
        res_article = {
            "id": article["article_url"],
            "category": article["primary_category"],
            "url": to_minecraft_url(article["article_url"]),
            "title": article["default_tile"]["title"],
            "sub_header": article["default_tile"]["sub_header"],
        }

        image_data = article["default_tile"]["image"]
        if image_data and image_data.get("content_type") == "image":
            res_article["image"] = to_minecraft_url(image_data["imageURL"])

        result.append(res_article)

    return result


def post_message_to_discord(http_session, webhook_url, content):
    payload = {
        "content": content,
        "username": "Minecraft News",
        "allowed_mentions": {"parse": []},
    }
    response = http_session.post(webhook_url, params={"wait": "true"}, json=payload, timeout=30)
    response.raise_for_status()


def get_posted_article_ids(file_name):
    if os.path.exists(file_name):
        with open(file_name, mode="r", encoding="utf-8") as file:
            lines = file.readlines()
            non_empty_lines = [line.strip() for line in lines if line.strip()]
            return non_empty_lines
    else:
        return []


def main():
    feed_url = os.environ.get("MINECRAFT_FEED_URL")
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    print("Opening http session...")
    http_session = create_http_session()

    print("Getting last posted article id...")
    last_article_file_name = "last_posted_article_id.txt"
    posted_article_ids = get_posted_article_ids(last_article_file_name)

    print("Fetching news articles...")
    all_articles = convert_feed_to_articles(fetch_articles(http_session, feed_url))
    relevant_articles = [article for article in all_articles if article["id"] not in posted_article_ids]
    if not relevant_articles:
        print("No new news articles found")
        return

    print("Posting new news articles to discord...")
    for article in reversed(relevant_articles):
        content = format_article_message_content(article)
        post_message_to_discord(http_session, webhook_url, content)

    print("Updating last posted article id...")
    all_article_ids = [article["id"] for article in all_articles]
    relevant_article_ids = all_article_ids[:100]
    with open(last_article_file_name, mode="w", encoding="utf-8") as file:
        file.write("\n".join(relevant_article_ids))


if __name__ == "__main__":
    main()
