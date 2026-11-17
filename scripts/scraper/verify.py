"""Verify the delivered default-scope JSON snapshot and offline reproducibility."""
import hashlib
import json
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

from scrape import check_coverage, main


def verify():
    started = time.monotonic()
    output = Path('data/mais/2026-27')
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    programs = json.loads((output / 'programs.json').read_text(encoding='utf-8'))
    courses = {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in (output / 'courses').glob('*.json')}
    assert manifest['failures'] == [], manifest['failures']
    rows = [r for p in programs for r in p['plan']]
    assert {r['predmet_id'] for r in rows} == set(courses)
    assert manifest['counts'] == dict(programs=len(programs), plan_rows=len(rows),
                                      sheets=len(courses), unique_course_codes=len({s['code'] for s in courses.values()}))
    for row in rows:
        assert courses[row['predmet_id']]['code'] == row['code'], row
    for course in courses.values():
        check_coverage(course['sections'], course['full_text'])
    assert not any('Ã' in p.read_text(encoding='utf-8') or 'Å' in p.read_text(encoding='utf-8') for p in output.rglob('*.json'))
    controls = {pid: {'code': courses[pid]['code'], 'fields': courses[pid]['fields'], 'grades': courses[pid]['grades']}
                for pid in ('65954478', '65953562')}
    unknown = sorted({label for c in courses.values() for label in c['unknown_labels']})
    def digests(root):
        return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.rglob('*.json') if p.name != 'manifest.json'}
    with tempfile.TemporaryDirectory(prefix='mais-verify-') as temporary:
        target = Path(temporary)
        with patch('requests.Session.request', side_effect=AssertionError('Offline verification attempted network')):
            assert main(['--parse-only', '--out', str(target)]) == 0
        assert digests(output) == digests(target), 'Offline JSON differs from downloaded snapshot'
        rebuilt = json.loads((target / 'manifest.json').read_text(encoding='utf-8'))
        assert {k: v for k, v in manifest.items() if k != 'scraped_at'} == {k: v for k, v in rebuilt.items() if k != 'scraped_at'}
    summary = dict(counts=manifest['counts'], controls=controls, unknown_labels=unknown,
                   null_convenience_values={key: sum(c[key] is None for c in courses.values())
                                            for key in ('programs', 'grades', 'teachers')},
                   output_bytes=sum(p.stat().st_size for p in output.rglob('*.json')),
                   regular_unique_ids_by_degree={d: len({r['predmet_id'] for p in programs if p['degree'] == d
                                                        for r in p['plan'] if r['block'] == 'plan'})
                                                 for d in manifest['degrees']},
                   verification_seconds=round(time.monotonic() - started, 2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    verify()
