"""Run from project root: python phase7_10_optional_validation/validate_project.py myproject.zip"""
from pathlib import Path
import argparse
import json
from project_validation import inspect_zip_bytes, markdown_report


def main():
    p = argparse.ArgumentParser(description='Static report for a generated project ZIP; never executes its contents.')
    p.add_argument('archive', type=Path)
    p.add_argument('--output-dir', type=Path, default=None)
    args = p.parse_args()
    report = inspect_zip_bytes(args.archive.read_bytes())
    out = args.output_dir or args.archive.parent
    out.mkdir(parents=True, exist_ok=True)
    stem = args.archive.stem
    json_path = out / (stem + '.validation.json')
    md_path = out / (stem + '.validation.md')
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    md_path.write_text(markdown_report(report), encoding='utf-8')
    print(f"Validated {report['files_analyzed']} files: {report['summary']}")
    print(f'Reports: {json_path} and {md_path}')

if __name__ == '__main__': main()
