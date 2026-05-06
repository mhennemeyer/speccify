"""speccify-core — shared spec loader, schema validator, resolver, codegen pipeline."""

from speccify_core.loader import SpecLoader, SpecLoaderError
from speccify_core.validator import (
    DEFAULT_SCHEMA_PATH,
    SchemaValidator,
    ValidationIssue,
)

__version__ = "0.0.0"

__all__ = [
    "DEFAULT_SCHEMA_PATH",
    "SchemaValidator",
    "SpecLoader",
    "SpecLoaderError",
    "ValidationIssue",
    "__version__",
]
