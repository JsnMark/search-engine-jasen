"""
html_extractor.py
"""

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

IMPORTANT_TAGS = ["h1", "h2", "h3", "b", "strong", "em"]

def extract(content: str) -> dict:
    """
    Extracts the content into title, important, and body
    """
    stripped = content.lstrip()
    # not html or xml
    if not stripped.startswith("<"):
        return {"title": "", "important": "", "body": content}

    head = stripped[:1000].lower() # might have whitespace in front
    if head.startswith("<?xml") and "<html" not in head:
        soup = BeautifulSoup(content, features="xml")
    else:
        soup = BeautifulSoup(content, "lxml")

    # dont want stuff like js or css stuff
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = soup.title.get_text(" ") if soup.title else ""
    # Important is all important tags if there isnt a highler level important parent
    # Otherwise we will double count stuff like <h1><bold> Hello </bold></h1>
    important = " ".join(
        t.get_text(" ") for t in soup.find_all(IMPORTANT_TAGS) if t.find_parent(IMPORTANT_TAGS) is None
    )
    body = soup.get_text(" ")
    return {"title": title, "important": important, "body": body}