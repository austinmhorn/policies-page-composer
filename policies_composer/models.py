from dataclasses import dataclass


@dataclass(frozen=True)
class Policy:
    title: str
    number: str
    manual: str
    deep_link: str
    keywords: tuple[str, ...] = ()
    notion_page_id: str = ""
