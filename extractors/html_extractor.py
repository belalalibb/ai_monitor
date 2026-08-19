import re
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup
from data_mining.core.security import clean_scraped_text


class HtmlContentExtractor:
    """
    Parses HTML documents, strips boilerplate/navigation/scripts,
    and extracts clean article text and metadata.
    """

    def extract(self, html_content: str, source_url: str = "") -> Dict[str, str]:
        if not html_content:
            return {"title": "", "description": "", "text": "", "headings": ""}

        soup = BeautifulSoup(html_content, "html.parser")

        # Extract title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("meta", property="og:title"):
            title = soup.find("meta", property="og:title").get("content", "").strip()

        # Extract description
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
        if meta_desc:
            description = meta_desc.get("content", "").strip()

        # Remove unneeded elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "svg", "noscript"]):
            tag.decompose()

        # Extract headings
        headings = []
        for h in soup.find_all(["h1", "h2", "h3"]):
            text = h.get_text(strip=True)
            if text:
                headings.append(text)

        # Main content targeting (prefer article, main, or body)
        main_content = soup.find("article") or soup.find("main") or soup.body or soup
        raw_text = main_content.get_text(separator="\n", strip=True)
        clean_text = clean_scraped_text(raw_text)

        return {
            "title": title,
            "description": description,
            "headings": " | ".join(headings[:10]),
            "text": clean_text,
        }
