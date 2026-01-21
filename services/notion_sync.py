import json
from typing import Optional

import requests

NOTION_API_VERSION = "2022-06-28"
NOTION_API_BASE = "https://api.notion.com/v1"


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


def _query_page_by_job_url(database_id: str, api_key: str, job_url: str) -> Optional[str]:
    payload = {
        "filter": {
            "property": "Job URL",
            "url": {"equals": job_url},
        }
    }
    response = requests.post(
        f"{NOTION_API_BASE}/databases/{database_id}/query",
        headers=_headers(api_key),
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if results:
        return results[0].get("id")
    return None


def _build_properties(entry: dict) -> dict:
    company = str(entry.get("company", "")).strip()
    role = str(entry.get("title", "")).strip()
    status = str(entry.get("status", "")).strip()
    source = str(entry.get("source", "")).strip()
    job_url = entry.get("url")
    drive_link = entry.get("drive_link")
    date_str = entry.get("date")

    title = " - ".join(x for x in [company, role] if x) or role or company or "Job"

    props = {
        "Job": {"title": [{"text": {"content": title}}]},
    }
    if company:
        props["Company"] = {"rich_text": [{"text": {"content": company}}]}
    if role:
        props["Role"] = {"rich_text": [{"text": {"content": role}}]}
    if date_str:
        props["Date"] = {"date": {"start": date_str}}
    if status:
        props["Status"] = {"select": {"name": status}}
    if source:
        props["Source"] = {"select": {"name": source}}
    if job_url:
        props["Job URL"] = {"url": job_url}
    if drive_link:
        props["Drive Link"] = {"url": drive_link}

    return props


def _create_page(database_id: str, api_key: str, entry: dict) -> None:
    payload = {
        "parent": {"database_id": database_id},
        "properties": _build_properties(entry),
    }
    response = requests.post(
        f"{NOTION_API_BASE}/pages",
        headers=_headers(api_key),
        json=payload,
        timeout=15,
    )
    response.raise_for_status()


def _update_page(page_id: str, api_key: str, entry: dict) -> None:
    payload = {
        "properties": _build_properties(entry),
    }
    response = requests.patch(
        f"{NOTION_API_BASE}/pages/{page_id}",
        headers=_headers(api_key),
        json=payload,
        timeout=15,
    )
    response.raise_for_status()


def sync_history_to_notion(
    history_path: str,
    database_id: str,
    api_key: str,
) -> dict:
    with open(history_path, "r", encoding="utf-8") as f:
        history = json.load(f)

    synced = 0
    skipped = 0
    for entry in history:
        job_url = entry.get("url")
        if not job_url:
            skipped += 1
            continue
        try:
            page_id = _query_page_by_job_url(database_id, api_key, job_url)
            if page_id:
                _update_page(page_id, api_key, entry)
            else:
                _create_page(database_id, api_key, entry)
            synced += 1
        except requests.RequestException:
            skipped += 1

    return {"synced": synced, "skipped": skipped}
