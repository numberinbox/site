"""Regression checks for approved visible brand copy."""

import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_brand


def copy_site_tree(temporary):
    site = Path(temporary) / "site"
    shutil.copytree(
        check_brand.SITE_ROOT,
        site,
        ignore=shutil.ignore_patterns(".git", "docs", "__pycache__"),
    )
    return site


def copy_guide(temporary):
    guide_source = (
        check_brand.SITE_ROOT.parent / "platform" / "docs" / "16-branding.md"
    )
    platform = Path(temporary) / "platform"
    (platform / "docs").mkdir(parents=True)
    shutil.copy(guide_source, platform / "docs" / "16-branding.md")
    return platform


def run_checker(site, extra_args=()):
    output = io.StringIO()
    with patch.object(check_brand, "SITE_ROOT", site), \
         patch("sys.argv", ["check_brand.py", *extra_args]), \
         contextlib.redirect_stdout(output):
        status = check_brand.main()
    return status, output.getvalue()


MOBILE_ROOT = check_brand.SITE_ROOT.parent / "mobile-app"


class MessageGuardTests(unittest.TestCase):
    def test_approved_guide_and_footers_pass(self):
        with tempfile.TemporaryDirectory(prefix="numberinbox-messages-") as temporary:
            site = copy_site_tree(temporary)
            platform = copy_guide(temporary)
            status, _ = run_checker(
                site,
                [
                    "--platform-root", str(platform),
                    "--mobile-root", str(MOBILE_ROOT),
                    "--require-sources",
                ],
            )
            self.assertEqual(status, 0)

    def test_misspelled_footer_tagline_fails(self):
        with tempfile.TemporaryDirectory(prefix="numberinbox-messages-") as temporary:
            site = copy_site_tree(temporary)
            page = site / "index.html"
            text = page.read_text(encoding="utf-8")
            self.assertIn("Email, reimagined with your number.", text)
            page.write_text(
                text.replace(
                    "Email, reimagined with your number.",
                    "Email, reimagined with youre number.",
                ),
                encoding="utf-8",
            )
            status, output = run_checker(site)
            self.assertEqual(status, 1)
            self.assertIn("primary_tagline", output)

    def test_comment_only_tagline_does_not_satisfy_footer(self):
        with tempfile.TemporaryDirectory(prefix="numberinbox-messages-") as temporary:
            site = copy_site_tree(temporary)
            page = site / "delete-account.html"
            text = page.read_text(encoding="utf-8")
            self.assertIn("<p>Email, reimagined with your number.</p>", text)
            page.write_text(
                text.replace(
                    "<p>Email, reimagined with your number.</p>",
                    "<!-- Email, reimagined with your number. -->",
                ),
                encoding="utf-8",
            )
            status, output = run_checker(site)
            self.assertEqual(status, 1)
            self.assertIn("primary_tagline", output)

    def test_missing_and_duplicate_guide_keys_fail(self):
        with tempfile.TemporaryDirectory(prefix="numberinbox-messages-") as temporary:
            site = copy_site_tree(temporary)
            platform = copy_guide(temporary)
            guide = platform / "docs" / "16-branding.md"
            text = guide.read_text(encoding="utf-8")
            row = "| `secondary_tagline` | `Your number. Your inbox.` | Compact slogan for login/onboarding or space-limited brand placement |"
            self.assertIn(row, text)
            guide.write_text(text.replace(row + "\n", ""), encoding="utf-8")
            status, output = run_checker(
                site,
                [
                    "--platform-root", str(platform),
                    "--mobile-root", str(MOBILE_ROOT),
                    "--require-sources",
                ],
            )
            self.assertEqual(status, 1)
            self.assertIn("secondary_tagline", output)

            guide.write_text(text, encoding="utf-8")
            primary = "| `primary_tagline` | `Email, reimagined with your number.` | Default brand tagline; website footer, app welcome/about, logo-with-tagline asset |"
            self.assertIn(primary, text)
            guide.write_text(
                text.replace(primary, primary + "\n" + primary), encoding="utf-8"
            )
            status, output = run_checker(
                site,
                [
                    "--platform-root", str(platform),
                    "--mobile-root", str(MOBILE_ROOT),
                    "--require-sources",
                ],
            )
            self.assertEqual(status, 1)
            self.assertIn("primary_tagline", output)

    def test_explanatory_message_in_primary_placement_fails(self):
        with tempfile.TemporaryDirectory(prefix="numberinbox-messages-") as temporary:
            site = copy_site_tree(temporary)
            page = site / "index.html"
            text = page.read_text(encoding="utf-8")
            self.assertIn("<p>Email, reimagined with your number.</p>", text)
            page.write_text(
                text.replace(
                    "<p>Email, reimagined with your number.</p>",
                    "<p>Your number is your inbox.</p>",
                ),
                encoding="utf-8",
            )
            status, output = run_checker(site)
            self.assertEqual(status, 1)
            self.assertIn("primary_tagline", output)


if __name__ == "__main__":
    unittest.main()
