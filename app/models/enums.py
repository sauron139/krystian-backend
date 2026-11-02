from enum import StrEnum


class ContentStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class Availability(StrEnum):
    OPEN_TO_WORK = "open_to_work"
    OPEN_TO_FREELANCE = "open_to_freelance"
    OPEN_TO_BOTH = "open_to_both"
    UNAVAILABLE = "unavailable"


class ProjectCategory(StrEnum):
    SOFTWARE = "software"
    PHYSICS = "physics"
    FREELANCE = "freelance"
    RESEARCH = "research"


class ExperienceType(StrEnum):
    WORK = "work"
    EDUCATION = "education"
    RESEARCH = "research"
    VOLUNTEER = "volunteer"


class SkillCategory(StrEnum):
    LANGUAGE = "language"
    FRAMEWORK = "framework"
    DATA = "data"
    PHYSICS = "physics"
    MATH = "math"
    TOOL = "tool"
    CLOUD = "cloud"


class ContactIntent(StrEnum):
    JOB = "job"
    FREELANCE = "freelance"
    OTHER = "other"


class MessageStatus(StrEnum):
    NEW = "new"
    REPLIED = "replied"
    ARCHIVED = "archived"
