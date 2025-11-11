import os
import requests


def to_minecraft_url(path):
    return f"https://www.minecraft.net{path}"


def fetch_articles(feed_url):
    response = requests.get(feed_url, timeout=30)
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


def post_message_to_discord(webhook_url, content):
    payload = {
        "content": content,
        "username": "Minecraft News",
        "allowed_mentions": {"parse": []},
    }
    response = requests.post(webhook_url, params={"wait": "true"}, json=payload, timeout=30)
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

    print("Getting last posted article id...")
    last_article_file_name = "last_posted_article_id.txt"
    last_posted_article_id = get_last_posted_article_id(last_article_file_name)

    print("Fetching news articles...")
    all_articles = convert_feed_to_articles(fetch_articles(feed_url))
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
        post_message_to_discord(webhook_url, content)

    print("Updating last posted article id...")
    last_article_id = all_articles[0]["id"]
    with open(last_article_file_name, mode="w", encoding="utf-8") as file:
        file.write(last_article_id)


if __name__ == "__main__":
    main()
