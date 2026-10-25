"""Require explicit values in Verenia block-form country-flag assignments.

This checks production syntax, not the flag defaults of the Python world model.
Native overrides are checked only for HSM-owned flag assignments.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "verenia_flags_parser", Path(__file__).with_name("Test-Verenia.py")
)
BASE = importlib.util.module_from_spec(SPEC)
# Dataclass annotation resolution needs the module registered before execution.
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)

NATIVE_OVERRIDES = (
    BASE.MOD / "common/national_focus/AVI.txt",
    BASE.MOD / "common/decisions/ERI_decisions.txt",
    BASE.MOD / "events/Avian Events.txt",
)


def missing_values(nodes, *, hsm_only=False):
    missing = []
    for node in BASE.walk(nodes):
        if node.key != "set_country_flag" or not isinstance(node.value, list):
            continue
        flag = node.get("flag", "<missing flag>")
        if hsm_only and not str(flag).startswith("HSM_"):
            continue
        if not node.all("value"):
            missing.append(flag)
    return missing


class VereniaFlags(unittest.TestCase):
    def test_production_block_flags_have_explicit_values(self):
        paths = sorted(set(BASE.package_files()) | set(NATIVE_OVERRIDES))
        self.assertTrue(paths)
        failures = []
        for path in paths:
            for flag in missing_values(
                BASE.read(path), hsm_only=path in NATIVE_OVERRIDES
            ):
                failures.append(f"{path.relative_to(BASE.ROOT)}: {flag}")
        self.assertEqual([], failures, "Missing explicit value:\n" + "\n".join(failures))

    def test_rejects_timed_and_untimed_block_omissions(self):
        source = """
        effect = {
            set_country_flag = { flag = HSM_VER_timed days = 45 }
            set_country_flag = { flag = HSM_VER_untimed }
        }
        """
        self.assertEqual(
            ["HSM_VER_timed", "HSM_VER_untimed"], missing_values(BASE.parse(source))
        )

    def test_accepts_explicit_values_and_scalar_flags(self):
        source = """
        set_country_flag = HSM_VER_permanent
        set_country_flag = { flag = HSM_VER_timed value = 1 days = 45 }
        set_country_flag = { flag = HSM_VER_zero value = 0 }
        """
        self.assertEqual([], missing_values(BASE.parse(source)))

    def test_native_filter_checks_only_hsm_assignments(self):
        source = """
        set_country_flag = { flag = native_flag days = 90 }
        set_country_flag = { flag = HSM_VER_pending days = 30 }
        """
        self.assertEqual(
            ["HSM_VER_pending"], missing_values(BASE.parse(source), hsm_only=True)
        )

    def test_comments_and_sibling_values_do_not_mask_omissions(self):
        source = """
        effect = {
            value = 1
            set_country_flag = { flag = HSM_VER_pending # value = 1
                days = 30
            }
        }
        """
        self.assertEqual(["HSM_VER_pending"], missing_values(BASE.parse(source)))


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0], *BASE.REST])
