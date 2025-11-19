import os
import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from datetime import datetime, timezone
from textwrap import dedent

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
}


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
    return response_json["result"]["results"]


def format_article_message_content(article):
    return dedent(f"""\
    ## {article['category']}: {article['title']}
    -# {article['description']}
    -# Author: {article['author']}, Posted: {article['posted_at']}
    <{article['url']}>
    """).strip("\n")


def convert_feed_to_articles(articles_from_feed):
    result = []
    for article in articles_from_feed:
        article_url = article["url"]
        article_id = article_url.rsplit("/", 1)[-1]
        article_post_datetime = datetime.fromtimestamp(article["time"], tz=timezone.utc)
        res_article = {
            "id": article_id,
            "category": article["type"],
            "url": article_url,
            "title": article["title"],
            "description": article["description"],
            "author": article["author"],
            "posted_at": article_post_datetime.strftime("%d.%m.%Y %H:%M:%S UTC")
        }
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


def get_last_posted_article_id(file_name):
    if os.path.exists(file_name):
        with open(file_name, mode="r", encoding="utf-8") as file:
            content = file.read().strip()
            return content or None
    else:
        return None


def main():
    feed_url = os.environ.get("MINECRAFT_FEED_URL")
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    print("Opening http session...")
    http_session = create_http_session()

    print("Getting last posted article id...")
    last_article_file_name = "last_posted_article_id.txt"
    last_posted_article_id = get_last_posted_article_id(last_article_file_name)

    print("Fetching news articles...")
    all_articles = convert_feed_to_articles(fetch_articles(http_session, feed_url))
    if last_posted_article_id is not None:
        index = next((i for i, item in enumerate(all_articles) if item["id"] == last_posted_article_id), None)
        if index is not None:
            all_articles = all_articles[:index]

    if not all_articles:
        print("No new news articles found")
        return

    print("Posting new news articles to discord...")
    for article in reversed(all_articles):
        content = format_article_message_content(article)
        post_message_to_discord(http_session, webhook_url, content)

    print("Updating last posted article id...")
    last_article_id = all_articles[0]["id"]
    with open(last_article_file_name, mode="w", encoding="utf-8") as file:
        file.write(last_article_id)


if __name__ == "__main__":
    main()
