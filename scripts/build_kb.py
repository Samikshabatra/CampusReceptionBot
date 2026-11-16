"""Rebuild knowledge/courses.json from the raw CSV and print the build report."""

import argparse
from pathlib import Path

import yaml

from reception.kb.courses_build import clean_courses, write_courses


def main() -> None:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=Path("data/raw/CHRIST_Central_Campus_Courses.csv"))
    ap.add_argument("--knowledge", type=Path, default=Path("knowledge"))
    args = ap.parse_args()
    text = (args.knowledge / "departments.yaml").read_text(encoding="utf-8")
    departments = yaml.safe_load(text)
    courses, report = clean_courses(args.csv, departments)
    write_courses(courses, args.knowledge / "courses.json")
    print(f"Wrote {len(courses)} courses to {args.knowledge / 'courses.json'}")
    for line in report:
        print(" -", line)


if __name__ == "__main__":
    main()
