# career/application_engine/questions.py — Semantic Question Classification & Sensitive Guard
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from career.models import ApplicationQuestion, CareerProfile

logger = logging.getLogger("JARVIS.QuestionEngine")

SENSITIVE_KEYWORDS = {
    "work_authorization": ["authorized to work", "legal right to work", "work permit", "eligible to work"],
    "sponsorship": ["visa sponsorship", "require sponsorship", "require visa", "sponsorship in future", "h1b", "h-1b", "opt", "cpt"],
    "salary": ["salary expectation", "desired salary", "compensation expectations", "target compensation", "current salary"],
    "relocation": ["willing to relocate", "relocation assistance", "open to relocate"],
    "eeo": ["gender", "race", "ethnicity", "veteran", "disability", "equal opportunity", "demographic"],
    "legal": ["criminal record", "background check", "felony", "misdemeanor", "drug test"],
}


class QuestionEngine:
    """
    Semantic question mapping and sensitive field protection engine.
    - Accurately maps form fields to verified CareerProfile attributes.
    - Flags sensitive questions requiring mandatory human confirmation.
    - Zero-guessing rule: Never fabricates or guesses unverified personal answers.
    """

    @classmethod
    def map_questions(cls, profile: CareerProfile, questions: List[ApplicationQuestion]) -> List[ApplicationQuestion]:
        """Fill suggested answers from verified CareerProfile and flag sensitive requirements."""
        for q in questions:
            q_text_low = q.question_text.lower().strip()

            # 1. Sensitive Field Detection
            for category, kws in SENSITIVE_KEYWORDS.items():
                if any(kw in q_text_low for kw in kws):
                    q.requires_confirmation = True
                    q.sensitive_category = category
                    break

            # 2. Semantic Mapping to CareerProfile
            if any(w in q_text_low for w in ("first name", "given name")):
                q.suggested_answer = profile.contact.full_name.split()[0] if profile.contact.full_name else ""
                q.confidence = 1.0

            elif any(w in q_text_low for w in ("last name", "family name", "surname")):
                parts = profile.contact.full_name.split()
                q.suggested_answer = " ".join(parts[1:]) if len(parts) > 1 else ""
                q.confidence = 1.0

            elif any(w in q_text_low for w in ("full name", "your name")):
                q.suggested_answer = profile.contact.full_name
                q.confidence = 1.0

            elif "email" in q_text_low:
                q.suggested_answer = profile.contact.email
                q.confidence = 1.0

            elif "phone" in q_text_low or "mobile" in q_text_low:
                q.suggested_answer = profile.contact.phone
                q.confidence = 1.0

            elif "linkedin" in q_text_low:
                q.suggested_answer = profile.contact.linkedin_url
                q.confidence = 1.0

            elif "github" in q_text_low:
                q.suggested_answer = profile.contact.github_url
                q.confidence = 1.0

            elif "portfolio" in q_text_low or "website" in q_text_low:
                q.suggested_answer = profile.contact.portfolio_url
                q.confidence = 1.0

            elif "location" in q_text_low or "city" in q_text_low or "address" in q_text_low:
                q.suggested_answer = profile.contact.location
                q.confidence = 0.95

            elif q.sensitive_category == "work_authorization":
                q.suggested_answer = "Yes" if "without sponsorship" in profile.preferences.work_authorization.lower() or "authorized" in profile.preferences.work_authorization.lower() else "No"
                q.confidence = 0.9

            elif q.sensitive_category == "sponsorship":
                q.suggested_answer = "Yes" if profile.preferences.requires_sponsorship else "No"
                q.confidence = 0.9

            elif q.sensitive_category == "salary":
                if profile.salary.target_annual_salary > 0:
                    q.suggested_answer = f"{int(profile.salary.target_annual_salary)} {profile.salary.currency}"
                else:
                    q.suggested_answer = profile.salary.salary_notes
                q.confidence = 0.85

            elif q.sensitive_category == "relocation":
                q.suggested_answer = "Open to discussing remote or relocation options."
                q.confidence = 0.8

            elif "notice period" in q_text_low or "availability" in q_text_low or "start date" in q_text_low:
                q.suggested_answer = profile.preferences.availability
                q.confidence = 0.9

            elif not q.suggested_answer:
                q.confidence = 0.0

        return questions
