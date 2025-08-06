import os
import scrapy
from newspaper import Article
from slugify import slugify
from urllib.parse import urlparse, urljoin
from scrapy.crawler import CrawlerProcess
import requests


class NewsArticleSpider(scrapy.Spider):
    name = "bbc_news_spider"
    visited_urls = set()

    def __init__(self, domain=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not domain:
            raise ValueError("Domain must be provided as an argument")
        self.domain = domain
        self.start_urls = [f"https://{domain}"]
        self.allowed_domains = [domain.replace("https://", "").replace("http://", "")]
        self.output_dir = domain.split(".")[0] + "_articles"
        os.makedirs(self.output_dir, exist_ok=True)

    def parse(self, response):
        for href in response.css("a::attr(href)").getall():
            url = urljoin(response.url, href)
            if url in self.visited_urls or not self.is_article_url(url):
                continue
            self.visited_urls.add(url)
            yield scrapy.Request(url, callback=self.parse_article)

    def parse_article(self, response):
        try:
            article = Article(response.url)
            article.download(input_html=response.text)
            article.parse()
        except Exception as e:
            self.logger.warning(f"Failed to parse article at {response.url}: {e}")
            return

        if not article.text or not article.title:
            return

        slug_title = slugify(article.title)
        txt_path = os.path.join(self.output_dir, f"{slug_title}.txt")
        image_path = os.path.join(self.output_dir, f"{slug_title}.jpg")

        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"{article.title}\n\n{article.text}")
        except Exception as e:
            self.logger.warning(f"Failed to write article text: {e}")

        if article.top_image:
            try:
                img_data = requests.get(article.top_image, timeout=10).content
                with open(image_path, "wb") as img_file:
                    img_file.write(img_data)
            except Exception as e:
                self.logger.warning(
                    f"Failed to download image for {article.title}: {e}"
                )

    def is_article_url(self, url):
        parsed = urlparse(url)
        return self.allowed_domains[0] in parsed.netloc and "/news/" in parsed.path


if __name__ == "__main__":
    domain_to_crawl = "bbc.com"  # 🔧 you can change this to any other domain
    process = CrawlerProcess(
        settings={
            "USER_AGENT": "Mozilla/5.0",
            "LOG_LEVEL": "INFO",
            # You can add more settings here as needed
        }
    )
    process.crawl(NewsArticleSpider, domain=domain_to_crawl)
    process.start()
