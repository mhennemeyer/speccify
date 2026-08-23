"""speccify-core — skills, sources, resolver and lockfile.

A skill is a directory with a `SKILL.md`, in the Agent Skills format, so it
works wherever agents already look for skills. What this package adds is
everything the specification leaves open: where a skill came from, whether it
is still true, which version you have, and what it builds on.
"""

from speccify_core.check import (
    Finding,
    check_links,
)
from speccify_core.git_registry import (
    DEFAULT_GIT_CACHE_DIR,
    BundleListing,
    GitLibrary,
    GitLibraryError,
    GitRef,
    GitRegistry,
    GitRegistryError,
    GitRepoCache,
    is_git_ref,
    parse_git_ref,
)
from speccify_core.lockfile import (
    CURRENT_LOCKFILE_SCHEMA_VERSION,
    DEFAULT_LOCKFILE_SCHEMA_PATH,
    LockEntry,
    Lockfile,
    LockfileError,
    build_lockfile,
)
from speccify_core.manifest import (
    CURRENT_MANIFEST_SCHEMA_VERSION,
    DEFAULT_LIBRARY_PATH,
    DEFAULT_MANIFEST_SCHEMA_PATH,
    MANIFEST_FILENAME,
    ManifestError,
    ProjectManifest,
)
from speccify_core.registry import (
    Bundle,
    Library,
    LibraryError,
    MultiLibrary,
    MultiRegistry,
    Registry,
    RegistryError,
    Version,
    bundle_sha256,
    split_id,
)
from speccify_core.resolver import (
    Range,
    RangeConflictError,
    Resolution,
    ResolvedGraph,
    Resolver,
    ResolverError,
    VersionNotFoundError,
    parse_uses_entry,
)
from speccify_core.spec_index import (
    INDEX_ENTRY_DIR,
    INDEX_ENTRY_SCHEMA_PATH,
    IndexEntry,
    SpecIndexError,
    load_index,
    load_indexes,
    parse_index_entry,
    search_index,
)

__version__ = "0.0.0"

__all__ = [
    "Bundle",
    "CURRENT_LOCKFILE_SCHEMA_VERSION",
    "CURRENT_MANIFEST_SCHEMA_VERSION",
    "DEFAULT_GIT_CACHE_DIR",
    "Finding",
    "check_links",
    "DEFAULT_LIBRARY_PATH",
    "DEFAULT_LOCKFILE_SCHEMA_PATH",
    "DEFAULT_MANIFEST_SCHEMA_PATH",
    "BundleListing",
    "GitLibrary",
    "GitLibraryError",
    "GitRef",
    "GitRegistry",
    "GitRegistryError",
    "GitRepoCache",
    "INDEX_ENTRY_DIR",
    "INDEX_ENTRY_SCHEMA_PATH",
    "IndexEntry",
    "Library",
    "LibraryError",
    "LockEntry",
    "Lockfile",
    "LockfileError",
    "MANIFEST_FILENAME",
    "ManifestError",
    "MultiLibrary",
    "MultiRegistry",
    "ProjectManifest",
    "Range",
    "RangeConflictError",
    "Registry",
    "RegistryError",
    "Resolution",
    "ResolvedGraph",
    "Resolver",
    "ResolverError",
    "SpecIndexError",
    "Version",
    "VersionNotFoundError",
    "__version__",
    "build_lockfile",
    "bundle_sha256",
    "is_git_ref",
    "load_index",
    "load_indexes",
    "parse_git_ref",
    "parse_index_entry",
    "parse_uses_entry",
    "search_index",
    "split_id",
]
