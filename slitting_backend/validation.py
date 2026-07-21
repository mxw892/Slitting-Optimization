"""Structured validation results shared by input-boundary adapters."""

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    """Severity assigned to a validation issue."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One traceable problem found while adapting external input."""

    component: str
    field: str
    severity: Severity
    message: str
    row: str | None = None
    record_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("component", "field", "message"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonblank string")
        if not isinstance(self.severity, Severity):
            raise TypeError("severity must be a Severity")


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Immutable collection of validation issues."""

    issues: tuple[ValidationIssue, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.issues, tuple):
            raise TypeError("issues must be a tuple")
        if not all(isinstance(issue, ValidationIssue) for issue in self.issues):
            raise TypeError("issues must contain ValidationIssue objects")

    @property
    def is_valid(self) -> bool:
        """Return whether the report contains no errors."""

        return not any(issue.severity is Severity.ERROR for issue in self.issues)

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        """Return only error-severity issues."""

        return tuple(issue for issue in self.issues if issue.severity is Severity.ERROR)


class DataFrameValidationError(ValueError):
    """Raised when boundary input cannot be converted into valid domain objects."""

    def __init__(self, report: ValidationReport) -> None:
        if report.is_valid:
            raise ValueError("DataFrameValidationError requires at least one error")
        self.report = report
        summary = "; ".join(_format_issue(issue) for issue in report.errors)
        super().__init__(summary)


def _format_issue(issue: ValidationIssue) -> str:
    location = issue.component
    if issue.row is not None:
        location += f" row={issue.row}"
    if issue.record_id is not None:
        location += f" record_id={issue.record_id}"
    return f"{location} field={issue.field}: {issue.message}"
