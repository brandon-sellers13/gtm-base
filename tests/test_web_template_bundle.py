"""The web app's copy of the company template matches the template itself.

A base created in the browser starts from `web/src/lib/base-template.generated.json`,
which `web/scripts/bundle-template.mjs` copies by hand from
`plugins/gtm-base/templates/company-base/`. Nothing rebuilt it when the template
changed, so the browser went on giving new bases a map that listed nine context
files after the template listed ten. This test fails whenever the bundle and
either copy of the template on the same commit disagree, and says which file.
The fix is to run `npm run bundle-template` in `web/`.
"""

import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE = os.path.join(ROOT, "web", "src", "lib", "base-template.generated.json")
TEMPLATES = (
    os.path.join(ROOT, "plugins", "gtm-base", "templates", "company-base"),
    os.path.join(ROOT, "templates", "company-base"),
)
# What the bundle script leaves out on purpose, matched the same way it matches.
LEFT_OUT = (".claude/settings.json",)
LEFT_OUT_ENDINGS = (".DS_Store",)


def template_files(folder):
    found = {}
    for dirpath, _dirs, names in os.walk(folder):
        for name in names:
            full = os.path.join(dirpath, name)
            relative = os.path.relpath(full, folder).replace(os.sep, "/")
            if relative in LEFT_OUT or relative.endswith(LEFT_OUT_ENDINGS):
                continue
            with open(full, encoding="utf-8", newline="") as handle:
                found[relative] = handle.read()
    return found


def bundled_files():
    with open(BUNDLE, encoding="utf-8") as handle:
        bundle = json.load(handle)
    return dict((one["path"], one["content"]) for one in bundle["files"])


class TheBundleIsTheTemplate(unittest.TestCase):
    def test_the_bundle_holds_exactly_the_templates_files(self):
        bundled = bundled_files()
        for folder in TEMPLATES:
            with self.subTest(folder=os.path.relpath(folder, ROOT)):
                self.assertEqual(sorted(template_files(folder)), sorted(bundled))

    def test_each_bundled_file_reads_as_the_template_does(self):
        bundled = bundled_files()
        for folder in TEMPLATES:
            for path, text in sorted(template_files(folder).items()):
                with self.subTest(folder=os.path.relpath(folder, ROOT), path=path):
                    self.assertEqual(text, bundled.get(path))

    def test_the_bundle_is_taken_from_the_template_folder(self):
        with open(BUNDLE, encoding="utf-8") as handle:
            source = json.load(handle)["source"]
        self.assertEqual("plugins/gtm-base/templates/company-base/", source["folder"])


if __name__ == "__main__":
    unittest.main()
