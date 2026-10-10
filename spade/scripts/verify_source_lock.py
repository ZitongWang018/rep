"""Read-only SHA256 receipt for a separately transferred, unadapted source snapshot."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(project_root, lock):
    root = Path(project_root).resolve(strict=True)
    problems = []
    for relative, expected in lock['files_sha256'].items():
        parts = Path(relative)
        if parts.is_absolute() or '..' in parts.parts:
            raise ValueError('Invalid manifest path')
        candidate = root / parts
        if not candidate.is_file():
            problems.append({'file': relative, 'reason': 'missing'})
            continue
        if not candidate.resolve().is_relative_to(root):
            problems.append({'file': relative, 'reason': 'outside project'})
            continue
        actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if actual != expected:
            problems.append({'file': relative, 'reason': 'sha256 mismatch'})
    return {'passed': not problems, 'expected_files': len(lock['files_sha256']),
            'problems': problems,
            'scope': 'unadapted source identity only; no runtime, GPU or model validation'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--lock', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'configs/source-lock.json')
    args = parser.parse_args()
    report = verify(args.project_root, json.loads(args.lock.read_text(encoding='utf-8')))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
