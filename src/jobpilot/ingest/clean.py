import html

from bs4 import BeautifulSoup


def html_to_text(raw: str) -> str:
    text = BeautifulSoup(html.unescape(raw), "html.parser").get_text(" ")
    return " ".join(text.split())
