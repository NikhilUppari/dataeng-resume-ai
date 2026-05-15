from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ClientInfo:
    name: str
    pattern: str
    domain: str


KNOWN_CLIENTS = [
    ClientInfo("CVS Health", r"\bcvs\s+health\b", "Healthcare"),
    ClientInfo("Oak Street Health", r"\boak\s+street\s+health\b", "Healthcare"),
    ClientInfo("HCA Healthcare", r"\bhca\s+healthcare\b", "Healthcare"),
    ClientInfo(
        "Northern Trust",
        r"\bnorthern\s+trust\b",
        "Financial Services / Banking / Wealth Management / Asset Servicing",
    ),
    ClientInfo("eBay", r"\bebay\b", "Retail / E-commerce"),
    ClientInfo("United Airlines", r"\bunited\s+airlines\b", "Aviation"),
    ClientInfo("MakeMyTrip", r"\bmake\s*my\s*trip\b", "Travel / Online Travel Platform"),
]


def find_known_client(text: str) -> ClientInfo | None:
    for client in KNOWN_CLIENTS:
        if re.search(client.pattern, text or "", flags=re.IGNORECASE):
            return client
    return None


def known_client_domain(client_name: str) -> str:
    client = find_known_client(client_name)
    return client.domain if client else ""


def known_client_names() -> list[str]:
    return [client.name for client in KNOWN_CLIENTS]


def present_known_clients(lines: Iterable[str]) -> list[ClientInfo]:
    found: list[ClientInfo] = []
    seen = set()
    for line in lines:
        client = find_known_client(line)
        if client and client.name.lower() not in seen:
            found.append(client)
            seen.add(client.name.lower())
    return found
