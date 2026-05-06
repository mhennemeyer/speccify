"""speccify-core — shared spec loader, schema validator, resolver, codegen pipeline."""

from speccify_core.loader import SpecLoader, SpecLoaderError
from speccify_core.manifest import (
    DEFAULT_MANIFEST_SCHEMA_PATH,
    DEFAULT_REGISTRY_PATH,
    ManifestError,
    ProjectManifest,
)
from speccify_core.registry import (
    LocalRegistry,
    RegistryError,
    Spec,
    Version,
)
from speccify_core.resolver import (
    Range,
    RangeConflictError,
    Resolution,
    ResolvedGraph,
    Resolver,
    ResolverError,
    VersionNotFoundError,
)
from speccify_core.validator import (
    DEFAULT_SCHEMA_PATH,
    SchemaValidator,
    ValidationIssue,
)

__version__ = "0.0.0"

__all__ = [
    "DEFAULT_MANIFEST_SCHEMA_PATH",
    "DEFAULT_REGISTRY_PATH",
    "DEFAULT_SCHEMA_PATH",
    "LocalRegistry",
    "ManifestError",
    "ProjectManifest",
    "Range",
    "RangeConflictError",
    "RegistryError",
    "Resolution",
    "ResolvedGraph",
    "Resolver",
    "ResolverError",
    "SchemaValidator",
    "Spec",
    "SpecLoader",
    "SpecLoaderError",
    "ValidationIssue",
    "Version",
    "VersionNotFoundError",
    "__version__",
]
