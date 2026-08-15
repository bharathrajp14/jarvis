# tests/unit/test_backend_diagnostics.py — Unit Tests for FailureType Classification and Structured Diagnostics
from __future__ import annotations

import unittest
from router.diagnostics import (
    FailureType,
    BackendAttempt,
    TaskExecutionDiagnostic,
    classify_exception,
    sanitize_diagnostic_text,
    TRANSIENT_FAILURE_TYPES,
)


class TestBackendDiagnostics(unittest.TestCase):

    def test_credential_sanitization(self):
        raw_error = "OpenAI request failed: Authorization: Bearer sk-testmockkey1234567890123456 with key=mock-secret-token-abcdef123456"
        sanitized = sanitize_diagnostic_text(raw_error)
        self.assertNotIn("sk-testmockkey", sanitized)
        self.assertNotIn("mock-secret-token", sanitized)
        self.assertIn("[REDACTED_SECRET]", sanitized)


    def test_failure_type_classification_matrix(self):
        # 1. TIMEOUT
        f_type, _ = classify_exception(TimeoutError("ReadTimeout: Request timed out after 10.0s"))
        self.assertEqual(f_type, FailureType.TIMEOUT)

        # 2. RATE_LIMIT
        f_type, _ = classify_exception(Exception("429 Too Many Requests: Rate limit exceeded"), http_status=429)
        self.assertEqual(f_type, FailureType.RATE_LIMIT)

        # 3. QUOTA_EXCEEDED
        f_type, _ = classify_exception(Exception("RESOURCE_EXHAUSTED: You have exhausted your monthly API quota"))
        self.assertEqual(f_type, FailureType.QUOTA_EXCEEDED)

        # 4. AUTH_FAILURE
        f_type, _ = classify_exception(Exception("401 Unauthorized: Invalid API key provided"), http_status=401)
        self.assertEqual(f_type, FailureType.AUTH_FAILURE)

        # 5. CONTEXT_TOO_LARGE
        f_type, _ = classify_exception(Exception("Prompt is too long: 135000 tokens exceeds context window limit of 128000"))
        self.assertEqual(f_type, FailureType.CONTEXT_TOO_LARGE)

        # 6. NETWORK_ERROR
        f_type, _ = classify_exception(ConnectionRefusedError("Connection refused: [Errno 111] Failed to establish a new connection"))
        self.assertEqual(f_type, FailureType.NETWORK_ERROR)

        # 7. MODEL_UNAVAILABLE
        f_type, _ = classify_exception(Exception("404 Not Found: Model gemini-invalid does not exist"), http_status=404)
        self.assertEqual(f_type, FailureType.MODEL_UNAVAILABLE)

        # 8. INVALID_TOOL_SCHEMA
        f_type, _ = classify_exception(Exception("Invalid tool schema: property 'aspect' missing required type"))
        self.assertEqual(f_type, FailureType.INVALID_TOOL_SCHEMA)

        # 9. PARSER_ERROR
        f_type, _ = classify_exception(Exception("JSONDecodeError: Expecting value at line 1 column 1"))
        self.assertEqual(f_type, FailureType.PARSER_ERROR)

        # 10. UNSUPPORTED_MODALITY
        f_type, _ = classify_exception(Exception("Unsupported modality: image input not supported on text-only model"))
        self.assertEqual(f_type, FailureType.UNSUPPORTED_MODALITY)

        # 11. INVALID_REQUEST
        f_type, _ = classify_exception(Exception("400 Bad Request: Invalid argument supplied"), http_status=400)
        self.assertEqual(f_type, FailureType.INVALID_REQUEST)

        # 12. PROVIDER_ERROR
        f_type, _ = classify_exception(Exception("500 Internal Server Error"), http_status=500)
        self.assertEqual(f_type, FailureType.PROVIDER_ERROR)

    def test_structured_diagnostic_trace_formatting(self):
        diag = TaskExecutionDiagnostic(
            trace_id="tr_abc123",
            task_id="task_456",
            goal="Analyze multi-modal system diagnostics",
        )
        diag.add_attempt(BackendAttempt(
            provider="Gemini",
            model="gemini-3.5-flash",
            status="FAILED",
            stage="provider_request",
            error_type=FailureType.TIMEOUT,
            error="Read timed out with Authorization: Bearer sk-abc1234567890def",
            latency_ms=5000,
            http_status=408,
        ))
        diag.add_attempt(BackendAttempt(
            provider="GPT",
            model="gemini-3.6-flash-high",
            status="FAILED",
            stage="provider_request",
            error_type=FailureType.RATE_LIMIT,
            error="429 Too Many Requests",
            latency_ms=1200,
            http_status=429,
        ))

        dev_trace = diag.format_developer_trace()
        self.assertIn("=== TASK_EXECUTION_FAILED ===", dev_trace)
        self.assertIn("trace_id: tr_abc123", dev_trace)
        self.assertIn("provider:   Gemini", dev_trace)
        self.assertIn("error_type: TIMEOUT", dev_trace)
        self.assertIn("error_type: RATE_LIMIT", dev_trace)
        self.assertNotIn("sk-abc1234567890def", dev_trace)
        self.assertIn("[REDACTED_SECRET]", dev_trace)

        user_summary = diag.format_user_facing_summary()
        self.assertIn("Gemini (Timeout)", user_summary)
        self.assertIn("GPT (Rate Limit)", user_summary)

    def test_transient_failure_classification(self):
        self.assertTrue(FailureType.TIMEOUT in TRANSIENT_FAILURE_TYPES)
        self.assertTrue(FailureType.RATE_LIMIT in TRANSIENT_FAILURE_TYPES)
        self.assertTrue(FailureType.NETWORK_ERROR in TRANSIENT_FAILURE_TYPES)
        self.assertFalse(FailureType.AUTH_FAILURE in TRANSIENT_FAILURE_TYPES)
        self.assertFalse(FailureType.INVALID_REQUEST in TRANSIENT_FAILURE_TYPES)
        self.assertFalse(FailureType.INVALID_TOOL_SCHEMA in TRANSIENT_FAILURE_TYPES)


if __name__ == "__main__":
    unittest.main()
