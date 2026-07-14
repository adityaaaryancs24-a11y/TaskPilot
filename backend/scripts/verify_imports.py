#!/usr/bin/env python3
"""Verify that all key modules import cleanly."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

modules = [
    "core.config",
    "core.state",
    "core.tracer",
    "core.llm_client",
    "core.embedding_model",
    "core.cache",
    "core.auth",
    "core.rate_limiter",
    "core.structured_logging",
    "core.prometheus_metrics",
    "core.input_sanitizer",
    "core.database",
    "core.memory",
    "core.websocket_manager",
    "core.observability",
    "core.connector_registry",
    "core.agent",
    "core.sync_engine",
    "core.dependency_analyzer",
    "core.calendar_planner",
    "core.weekly_summary",
    "core.qa",
    "core.grounding",
    "core.normalizer",
    "core.scoring_engine",
    "core.deduplicator",
    "core.extractor",
    "models.task",
    "api.routes",
]

failed = 0
for module in modules:
    try:
        __import__(module)
        print(f"  ✓ {module}")
    except Exception as e:
        print(f"  ✗ {module}: {e}")
        failed += 1

print(f"\n{'=' * 40}")
print(f"  {len(modules) - failed}/{len(modules)} modules imported successfully")
if failed:
    print(f"  {failed} module(s) failed")
    sys.exit(1)
else:
    print("  All imports OK!")
