# src/brjarvis/tools/validator.py — Deterministic Tool Schema Validator
"""
Deterministic Schema Validator for BR JARVIS Tool Invocations.
Enforces strict JSON schema validation, required properties, enums, type checking, bounds, and string constraints before tool execution.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("JARVIS.Tools.Validator")


class SchemaValidator:
    """Strict JSON schema validator for tool input parameters."""

    @classmethod
    def validate(cls, schema: Dict[str, Any], args: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate input arguments against a tool's JSON parameter schema.
        Returns (is_valid, error_message).
        """
        if not schema:
            return True, None

        if not isinstance(args, dict):
            return False, f"Expected argument dictionary, got {type(args).__name__}"

        schema_type = schema.get("type", "object")
        if schema_type != "object":
            return True, None

        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])

        # 1. Check Required Fields
        for req in required_fields:
            if req not in args or args[req] is None:
                return False, f"Missing required parameter '{req}'"
            if (
                isinstance(args[req], str)
                and not args[req].strip()
                and req in ("query", "path", "url", "command", "recipient", "content", "title", "prompt", "code")
            ):
                return False, f"Required parameter '{req}' cannot be empty string"

        # 2. Check Individual Property Constraints
        for key, value in args.items():
            if key not in properties:
                # Disallow unknown keys if additionalProperties is explicitly False
                if schema.get("additionalProperties") is False:
                    return False, f"Unexpected unknown parameter '{key}'"
                continue

            prop_schema = properties[key]
            prop_type = prop_schema.get("type")

            # Type Validation
            if value is not None and prop_type:
                type_valid, type_err = cls._check_type(key, value, prop_type)
                if not type_valid:
                    return False, type_err

            # Enum Validation
            if "enum" in prop_schema and value is not None:
                allowed = prop_schema["enum"]
                # Case-insensitive enum check
                val_str = str(value).lower()
                allowed_lower = [str(e).lower() for e in allowed]
                if val_str not in allowed_lower and str(value) not in allowed:
                    return False, f"Invalid value '{value}' for parameter '{key}'. Allowed options: {allowed}"

            # Numeric Range Validation
            if isinstance(value, (int, float)):
                if "minimum" in prop_schema and value < prop_schema["minimum"]:
                    return False, f"Parameter '{key}' value {value} is below minimum allowed {prop_schema['minimum']}"
                if "maximum" in prop_schema and value > prop_schema["maximum"]:
                    return False, f"Parameter '{key}' value {value} exceeds maximum allowed {prop_schema['maximum']}"

            # String Length Validation
            if isinstance(value, str):
                if "minLength" in prop_schema and len(value) < prop_schema["minLength"]:
                    return False, f"Parameter '{key}' is shorter than minimum length {prop_schema['minLength']}"
                if "maxLength" in prop_schema and len(value) > prop_schema["maxLength"]:
                    return False, f"Parameter '{key}' exceeds maximum length {prop_schema['maxLength']}"

        return True, None

    @classmethod
    def _check_type(cls, key: str, value: Any, expected_type: str) -> Tuple[bool, Optional[str]]:
        if expected_type == "string":
            if not isinstance(value, str):
                return False, f"Parameter '{key}' must be a string, got {type(value).__name__}"
        elif expected_type in ("integer", "int"):
            if not isinstance(value, int) or isinstance(value, bool):
                return False, f"Parameter '{key}' must be an integer, got {type(value).__name__}"
        elif expected_type in ("number", "float"):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return False, f"Parameter '{key}' must be a number, got {type(value).__name__}"
        elif expected_type == "boolean":
            if not isinstance(value, bool):
                return False, f"Parameter '{key}' must be a boolean, got {type(value).__name__}"
        elif expected_type == "array":
            if not isinstance(value, (list, tuple)):
                return False, f"Parameter '{key}' must be an array/list, got {type(value).__name__}"
        elif expected_type == "object":
            if not isinstance(value, dict):
                return False, f"Parameter '{key}' must be a dictionary/object, got {type(value).__name__}"
        return True, None
