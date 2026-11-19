from enum import StrEnum


class UserRole(StrEnum):
    CANDIDATE = "CANDIDATE"
    RECRUITER = "RECRUITER"


class TechDomain(StrEnum):
    PYTHON = "PYTHON"
    DOTNET = "DOTNET"
    JAVA = "JAVA"
    GAMEDEV = "GAMEDEV"
    PROJECT_MANAGEMENT = "PROJECT_MANAGEMENT"
    QA = "QA"
    EMBEDDED = "EMBEDDED"


class CompanyType(StrEnum):
    PRODUCT = "PRODUCT"
    OUTSOURCE = "OUTSOURCE"
    OUTSTAFF = "OUTSTAFF"
    STARTUP = "STARTUP"


class WorkFormat(StrEnum):
    REMOTE = "REMOTE"
    OFFICE = "OFFICE"
    HYBRID = "HYBRID"


class EnglishLevel(StrEnum):
    NO_ENGLISH = "NO_ENGLISH"
    BEGINNER = "BEGINNER"
    PRE_INTERMEDIATE = "PRE_INTERMEDIATE"
    INTERMEDIATE = "INTERMEDIATE"
    UPPER_INTERMEDIATE = "UPPER_INTERMEDIATE"
    ADVANCED = "ADVANCED"
    PROFICIENT = "PROFICIENT"


class VacancyStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ApplicationStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    HIRED = "HIRED"
