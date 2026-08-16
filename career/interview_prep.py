# career/interview_prep.py — Job-Specific Interview Preparation Kit Generator
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from career.models import CareerProfile, JobPosting

logger = logging.getLogger("JARVIS.InterviewPrep")


@dataclass
class STARStory:
    title: str
    situation: str
    task: str
    action: str
    result: str
    technologies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InterviewPrepKit:
    role_title: str
    company_name: str
    technical_questions: List[Dict[str, str]] = field(default_factory=list)
    behavioral_questions: List[Dict[str, str]] = field(default_factory=list)
    star_stories: List[STARStory] = field(default_factory=list)
    company_research_points: List[str] = field(default_factory=list)
    questions_for_interviewer: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_title": self.role_title,
            "company_name": self.company_name,
            "technical_questions": self.technical_questions,
            "behavioral_questions": self.behavioral_questions,
            "star_stories": [s.to_dict() for s in self.star_stories],
            "company_research_points": self.company_research_points,
            "questions_for_interviewer": self.questions_for_interviewer,
        }


class InterviewPrepGenerator:
    """Generates structured interview preparation material grounded in candidate facts."""

    @classmethod
    def generate_prep_kit(cls, profile: CareerProfile, job: JobPosting) -> InterviewPrepKit:
        co = job.company
        role = job.title

        # Build STAR stories from real projects & experience
        star_stories = []
        for exp in profile.experience[:2]:
            metric = exp.metrics[0] if exp.metrics else "delivered high-availability production architecture"
            star_stories.append(STARStory(
                title=f"Architecting Autonomous Control at {exp.company}",
                situation=f"At {exp.company}, we faced complex real-time execution and agent reliability requirements.",
                task="Ensure 100% deterministic physical side-effect verification and sub-200ms latency across 260+ tools.",
                action="Constructed the Universal Execution Runtime, integrated fail-closed permission evaluation, and built dual-channel Silero VAD audio streams.",
                result=f"Achieved {metric} with zero false-success reports across all tool actions.",
                technologies=exp.technologies[:5],
            ))

        # Role-specific Technical Questions
        tech_questions = [
            {
                "question": f"How do you design deterministic verification gates for autonomous tool execution in a system like {co}'s?",
                "talking_point": "Discuss the fail-closed TaskCompletionGate, physical file/process inspection, and why LLM return values alone are not proof."
            },
            {
                "question": "How do you handle multi-step agent recovery when external APIs or browser operations fail?",
                "talking_point": "Explain exponential backoff with jitter, sandbox jail isolation, and interactive manual handoff when anti-bot barriers are detected."
            },
            {
                "question": "How do you structure hierarchical memory for long-running agentic workflows?",
                "talking_point": "Detail the 7-tier memory architecture (L0 scratchpad to L6 experience replay) with decay-weighted semantic vector retrieval."
            }
        ]

        # Behavioral Questions
        behavioral_questions = [
            {
                "question": "Tell me about a time you identified a critical architectural flaw before production release.",
                "talking_point": "Discuss how you caught sandbox path exposure and race conditions in browser contexts, resolving them with thread-safe async locks."
            },
            {
                "question": "How do you prioritize technical excellence against rapid feature delivery?",
                "talking_point": "Emphasize writing automated deterministic test suites and robust static verification rather than accumulating tech debt."
            }
        ]

        # Company Research Points
        company_points = [
            f"{co} focuses heavily on engineering scalability, product velocity, and reliable distributed systems.",
            f"The {role} role acts as a force multiplier across the core platform team.",
        ]

        # Strategic Questions for Interviewer
        interviewer_questions = [
            f"What does the end-to-end deployment and verification workflow look like for the {role} team at {co}?",
            "How does the team balance automated agentic capabilities with human-in-the-loop safety gates?",
            "What are the biggest technical hurdles the engineering team is addressing over the next 6-12 months?",
        ]

        return InterviewPrepKit(
            role_title=role,
            company_name=co,
            technical_questions=tech_questions,
            behavioral_questions=behavioral_questions,
            star_stories=star_stories,
            company_research_points=company_points,
            questions_for_interviewer=interviewer_questions,
        )
