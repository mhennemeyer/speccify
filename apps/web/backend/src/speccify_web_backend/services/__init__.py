"""Service layer for the web backend.

Routes stay thin (pydantic in, dict out); the actual call into
`speccify-core` lives here so it can be reused from cross-consistency tests.
"""
