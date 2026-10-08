"""Configurable sender classification layer for academic institutions.

Implements Chapter 3 Section 3.1 & 3.2:
- Stakeholder is Faculty mailbox owner.
- Classifies incoming senders into canonical categories:
  - Student: e.g. USN-pattern local-parts (admission year + campus code + batch year + branch code + roll no), student.edu addresses
  - Admin: role-based department accounts (placement_officer@, hod_*@, coe@, dean@, registrar@, etc.)
  - Collaborator: colleague faculty or research partners (personal name/firstname.lastname@)
  - Vendor: external promotional, marketing, automated notification senders
  - Other: unclassified external senders
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.models import SenderCategory

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "institution_config.json"


class InstitutionSenderClassifier:
    """Configurable classifier using institution-specific regex patterns and role rules."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or _CONFIG_PATH
        self.config = self._load_config()

        # Compile USN regexes
        self.usn_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in self.config.get("student_usn_regexes", [
                r"^[0-9]{2}[a-zA-Z]{2}[0-9]{2}[a-zA-Z]{2,5}[0-9]{2,}$",
            ])
        ]
        self.admin_prefixes = [
            p.lower()
            for p in self.config.get("admin_role_prefixes", [
                "placement_officer", "hod_", "hod", "coe", "dean", "principal",
                "registrar", "academic", "admin", "office", "senate", "exam",
                "admissions", "accounts", "controller", "controller_of_examinations",
                "library", "hr", "academics", "faculty", "institute", "student_affairs",
            ])
        ]
        self.vendor_keywords = [
            k.lower()
            for k in self.config.get("vendor_keywords", [
                "sales", "promo", "marketing", "newsletter", "no-reply", "noreply", "kaggle", "notifications",
            ])
        ]

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def extract_email_address(self, raw_sender: str) -> str:
        """Extract clean email address from 'Name <email@domain>' or bare email."""
        match = re.search(r"<([^>]+)>", raw_sender)
        if match:
            return match.group(1).strip().lower()
        return raw_sender.strip().lower()

    def classify(
        self,
        sender: str,
        contact_map: Optional[Dict[str, Any]] = None,
    ) -> SenderCategory:
        """Classify a sender address into the canonical SenderCategory."""
        email = self.extract_email_address(sender)
        raw_lower = sender.lower()

        # 1. Contact map override (if verified in address book)
        if contact_map and email in contact_map:
            cat_val = contact_map[email].get("category")
            if cat_val:
                try:
                    return SenderCategory(cat_val)
                except ValueError:
                    pass

        # Split local part and domain
        if "@" in email:
            local_part, domain = email.split("@", 1)
        else:
            local_part, domain = email, ""

        # 2. Student USN pattern (dense alphanumeric, admission year + branch + roll)
        # e.g., 01fe23bci117@kletech.ac.in
        for pattern in self.usn_patterns:
            if pattern.match(local_part):
                return SenderCategory.STUDENT

        # Explicit student subdomains or student keywords
        if "student" in local_part or "student" in domain or ("cs" in domain and ".edu" in domain and "student" in raw_lower):
            return SenderCategory.STUDENT

        # 3. Known Administrative / Institutional Role-based accounts
        for prefix in self.admin_prefixes:
            if local_part.startswith(prefix) or f"_{prefix}" in local_part or f".{prefix}" in local_part:
                return SenderCategory.ADMIN
        if any(role in raw_lower for role in ["placement officer", "controller of examinations", "hod ", "dean ", "academic senate"]):
            return SenderCategory.ADMIN

        # 4. Vendor / Automated Notification / Promotional senders
        for vk in self.vendor_keywords:
            if vk in local_part or vk in domain or vk in raw_lower:
                return SenderCategory.VENDOR

        # 5. Colleague Faculty / Collaborator (e.g. bldesai@, firstname.lastname@)
        # In faculty mailboxes, colleague faculty mail is classified as Collaborator per spec
        if domain.endswith(".edu") or domain.endswith(".ac.in"):
            return SenderCategory.COLLABORATOR

        # Default fallback
        if "." in local_part:
            return SenderCategory.COLLABORATOR
        return SenderCategory.OTHER


# Singleton instance for easy import across modules
_CLASSIFIER = InstitutionSenderClassifier()


def classify_sender(sender: str, contact_map: Optional[Dict[str, Any]] = None) -> SenderCategory:
    """Convenience helper using the default InstitutionSenderClassifier."""
    return _CLASSIFIER.classify(sender, contact_map)
