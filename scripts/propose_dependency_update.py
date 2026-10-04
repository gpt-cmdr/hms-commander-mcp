"""Compare stable PyPI metadata; prepare compatible dependency PR changes.

No package install, merge or publication. Used only by maintenance CI or an
explicit maintainer command, never during an MCP query.
"""
from pathlib import Path
import argparse
import json
import re
from urllib.request import Request, urlopen
from packaging.specifiers import SpecifierSet
from packaging.version import Version

PACKAGES = {"mcp": ">=2.3.0,<3", "hms-commander": ">=0.3.1,<0.4"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Update lower bounds within declared target ranges")
    args = parser.parse_args()
    path = Path("pyproject.toml")
    text = path.read_text()
    report = []
    for package in PACKAGES:
        match = re.search(r'"' + re.escape(package) + r'(>=([^",]+),<[^" ]+)"', text)
        if not match:
            raise ValueError(f"Missing dependency contract for {package}")
        declared, minimum = match.group(1), Version(match.group(2))
        request = Request(f"https://pypi.org/pypi/{package}/json", headers={"User-Agent": "hms-commander-mcp-dependency-review"})
        with urlopen(request, timeout=15) as response:
            payload = response.read(2 * 1024 * 1024 + 1)
        if len(payload) > 2 * 1024 * 1024:
            raise ValueError(f"PyPI metadata for {package} exceeded the 2 MiB maintenance budget")
        document = json.loads(payload)
        candidates = []
        for raw, files in document["releases"].items():
            version = Version(raw)
            if not version.is_prerelease and not version.is_devrelease and any(not f.get("yanked", False) for f in files):
                candidates.append(version)
        latest = max(candidates)
        compatible = max(v for v in candidates if v in SpecifierSet(declared))
        report.append({"package": package, "declared": declared, "latest_stable": str(latest),
                       "latest_compatible": str(compatible), "outside_range_review": latest not in SpecifierSet(declared)})
        if args.apply and compatible > minimum:
            # Keep the upper bound. This candidate must pass checks and review
            # before merge; a resolver range is never itself evidence.
            proposed = re.sub(r'^>=([^,]+)', '>=' + str(compatible), declared)
            text = text.replace('"' + package + declared + '"', '"' + package + proposed + '"')
    if args.apply:
        path.write_text(text)
    Path("dependency-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
