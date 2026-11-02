"""Placeholder content so the site renders fully before Krystian adds real content.

Everything here is flagged `is_placeholder=True`: the frontend styles it as placeholder and
the admin dashboard's content checklist lists it as still to do. Seeding is idempotent: it
only fills tables that are empty and singletons that don't exist yet.
"""

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Experience, Profile, Project, ServiceOffering, SiteSettings, Skill
from app.models.enums import (
    Availability,
    ContentStatus,
    ExperienceType,
    ProjectCategory,
    SkillCategory,
)

PUB = ContentStatus.PUBLISHED

PROFILE = {
    "full_name": "Krystian",
    "headline": "Software engineer & physics student",
    "short_bio": "I build web products and backends, and I turn physics into code that runs.",
    "long_bio": "This is placeholder text. The full bio will cover building software, studying "
    "physics, and what connects the two.",
    "availability": Availability.OPEN_TO_BOTH,
}

SITE_SETTINGS = {
    "seo_title": "Krystian · Software engineer & physics student",
    "seo_description": "Portfolio of Krystian: web products, backend systems and "
    "physics-driven software. Available for full-time roles and freelance projects.",
    "show_blog": False,
    "show_cv_button": False,
}

PROJECTS: list[dict[str, Any]] = [
    {
        "slug": f"uncharted-object-{i}",
        "title": "Uncharted object",
        "summary": "A new project is being catalogued. Check back soon.",
        "category": cat,
        "sort_order": i,
    }
    for i, cat in enumerate(
        (ProjectCategory.SOFTWARE, ProjectCategory.PHYSICS, ProjectCategory.FREELANCE), start=1
    )
]

SERVICES: list[dict[str, Any]] = [
    {
        "title": "Web applications",
        "summary": "From idea to deployed product: dashboards, booking systems, internal "
        "tools, SaaS MVPs.",
        "deliverables": ["Frontend in React or Astro", "Auth, payments, admin panels",
                         "Deployed and monitored"],
    },
    {
        "title": "APIs & backends",
        "summary": "Fast, well-tested APIs and the data layer underneath them.",
        "deliverables": ["Python / FastAPI, PostgreSQL", "Background jobs, caching",
                         "Docker-based deployments"],
    },
    {
        "title": "Scientific software",
        "summary": "Turn models and equations into tools people use: simulations, data "
        "pipelines, interactive visualizations.",
        "deliverables": ["NumPy / SciPy, numerical methods", "Interactive browser visualizations",
                         "Clear write-ups of the physics"],
    },
]  # fmt: skip

EXPERIENCE: list[dict[str, Any]] = [
    {"type": ExperienceType.WORK, "organization": "Company name", "role": "Software Engineer",
     "start_date": date(2025, 1, 1), "bullets": ["Role and key results go here."]},
    {"type": ExperienceType.EDUCATION, "organization": "University name",
     "role": "BSc Physics (in progress)", "start_date": date(2024, 9, 1),
     "bullets": ["Focus areas, courses and research go here."]},
    {"type": ExperienceType.WORK, "organization": "Self-employed", "role": "Freelance developer",
     "start_date": date(2023, 1, 1), "bullets": ["Selected clients and outcomes go here."]},
]  # fmt: skip

SKILLS: list[tuple[str, SkillCategory, float, int]] = [
    ("Python", SkillCategory.LANGUAGE, 7, 5),
    ("TypeScript", SkillCategory.LANGUAGE, 5, 4),
    ("FastAPI", SkillCategory.FRAMEWORK, 4, 4),
    ("React", SkillCategory.FRAMEWORK, 5, 4),
    ("Astro", SkillCategory.FRAMEWORK, 1.5, 3),
    ("PostgreSQL", SkillCategory.DATA, 6, 4),
    ("Redis", SkillCategory.DATA, 3, 3),
    ("Docker", SkillCategory.TOOL, 4.5, 4),
    ("NumPy / SciPy", SkillCategory.PHYSICS, 3.5, 4),
    ("Classical mechanics", SkillCategory.PHYSICS, 2, 4),
    ("Numerical methods", SkillCategory.MATH, 2.5, 3),
]


async def _empty(session: AsyncSession, model: type[Any]) -> bool:
    return (await session.scalar(select(func.count()).select_from(model)) or 0) == 0


async def seed(session: AsyncSession) -> list[str]:
    """Insert placeholder content where missing. Returns what was seeded."""
    done: list[str] = []
    if await session.get(Profile, 1) is None:
        session.add(Profile(id=1, is_placeholder=True, **PROFILE))
        done.append("profile")
    if await session.get(SiteSettings, 1) is None:
        session.add(SiteSettings(id=1, is_placeholder=True, **SITE_SETTINGS))
        done.append("site_settings")
    if await _empty(session, Project):
        session.add_all(Project(status=PUB, is_placeholder=True, **p) for p in PROJECTS)
        done.append("projects")
    if await _empty(session, ServiceOffering):
        session.add_all(
            ServiceOffering(status=PUB, is_placeholder=True, sort_order=i, **s)
            for i, s in enumerate(SERVICES)
        )
        done.append("services")
    if await _empty(session, Experience):
        session.add_all(Experience(status=PUB, is_placeholder=True, **e) for e in EXPERIENCE)
        done.append("experience")
    if await _empty(session, Skill):
        session.add_all(
            Skill(name=n, category=c, years=y, proficiency=p, status=PUB, is_placeholder=True)
            for n, c, y, p in SKILLS
        )
        done.append("skills")
    await session.commit()
    return done
