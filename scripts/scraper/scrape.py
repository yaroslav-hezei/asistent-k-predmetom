"""Public MAIS crawler and loss-checked HTML parsers (T-001)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time

from bs4 import BeautifulSoup, NavigableString, Tag
import requests

BASE = 'https://maisportal.tuke.sk/portal/'
DEGREES = ['PRVY', 'PRVY_PROFES_ORIENTOVANY', 'DRUHY']
KNOWN_LABELS = set('''Vysoká škola|Fakulta|Pracovisko|Kód predmetu|Názov predmetu|Druh, rozsah a metóda vzdelávacích činností|Forma výučby|Odporúčaný rozsah výučby (v hodinách)|Denná forma štúdia (hodiny za týždeň)|Externá forma štúdia (hodiny za semester)|Metóda štúdia|Počet kreditov|Odporúčaný semester štúdia|Stupeň štúdia|Podmieňujúce predmety|Podmienky na absolvovanie predmetu|Spôsob hodnotenia a skončenia štúdia predmetu|Priebežné hodnotenie (PH)|Záverečné hodnotenie (ZH)|Celkové hodnotenie|Výsledky vzdelávania|Stručná osnova predmetu|Odporúčaná literatúra|Odporúčané voliteľné súčasti programu|Jazyk, ktorého znalosť je potrebná na absolvovanie predmetu|Poznámky|Hodnotenie predmetov|Zabezpečuje|Dátum poslednej zmeny|Schválil'''.split('|'))


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def normalize(value):
    return '\n'.join(re.sub(r'\s+', ' ', line).strip() for line in value.split('\n')).strip()


def events(node):
    """Render DOM order; only explicit breaks and block boundaries add newlines."""
    if isinstance(node, NavigableString):
        yield re.sub(r'\s+', ' ', str(node))
    elif isinstance(node, Tag) and node.name not in ('script', 'style'):
        if node.name == 'br':
            yield '\n'
        else:
            for child in node.children:
                yield from events(child)
            if node.name in ('td', 'th', 'tr', 'p', 'div', 'li', 'h2', 'h3', 'h5'):
                yield '\n'


def text(node):
    return normalize(''.join(events(node)))


def flat(node):
    return re.sub(r'\s+', ' ', text(node)).strip()


def number(value):
    try:
        n = float(value.strip().removesuffix('%').replace(',', '.'))
        return int(n) if n.is_integer() else n
    except (ValueError, AttributeError):
        return None


def check_coverage(sections, full_text):
    words = lambda s: re.findall(r'\w+', s, flags=re.UNICODE)
    actual = words(' '.join(s['label'] + ' ' + s['text'] for s in sections))
    expected = words(full_text)
    if actual != expected:
        raise ValueError('Section coverage mismatch: missing, added or reordered words')


def parse_sheet(html, predmet_id, academic_year, fetched_at):
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.select('table.Page_1')
    if len(tables) != 1:
        raise ValueError(f'Expected one course sheet table, found {len(tables)}')
    root = tables[0]
    title = root.find('td', class_='nadpis')
    if title and flat(title) == 'INFORMAČNÝ LIST PREDMETU':
        title.clear()
    full_text = text(root)
    labels = [b for b in root.find_all('b') if flat(b).endswith(':')]
    sections, buffer = [], []
    label_ids = {id(b): flat(b)[:-1].strip() for b in labels}

    def walk(node):
        if id(node) in label_ids:
            if sections:
                sections[-1]['text'] = normalize(''.join(buffer))
            elif normalize(''.join(buffer)):
                raise ValueError('Unlabelled text before first section')
            buffer.clear()
            sections.append({'label': label_ids[id(node)], 'text': ''})
        elif isinstance(node, NavigableString):
            buffer.append(re.sub(r'\s+', ' ', str(node)))
        elif isinstance(node, Tag) and node.name not in ('script', 'style'):
            if node.name == 'br':
                buffer.append('\n')
            else:
                for child in node.children:
                    walk(child)
                if node.name in ('td', 'th', 'tr', 'p', 'div', 'li', 'h2', 'h3', 'h5'):
                    buffer.append('\n')
    walk(root)
    if not sections:
        raise ValueError('No sheet labels')
    sections[-1]['text'] = normalize(''.join(buffer))
    check_coverage(sections, full_text)
    values = {s['label']: s['text'] for s in sections}
    get = lambda label: values.get(label) or None
    programs = []
    program_table_present = any(flat(td) == 'Odporúčaný semester' for td in root.select('td.middleLeft'))
    for row in root.select('tr'):
        cells = row.find_all('td', recursive=False)
        if len(cells) == 4 and 'middleLeft' in cells[0].get('class', []) and flat(cells[0]) != 'Odporúčaný semester':
            columns = [text(c).split('\n') for c in cells]
            count = len(columns[1])
            if any(len(c) not in (1, count) for c in columns):
                raise ValueError('Unaligned recommended semester table')
            for i in range(count):
                programs.append(dict(zip(('semester', 'program', 'degree', 'method'),
                                         [c[i] if len(c) > 1 else c[0] for c in columns])))
    grade_text = get('Hodnotenie predmetov') or ''
    total = re.search(r'Celkový počet hodnotených študentov:\s*(\d+)', grade_text)
    percentages = re.findall(r'(\d+(?:[.,]\d+)?)\s*%', grade_text)
    grades = {'total_students': int(total[1]) if total else None,
              'percent': dict(zip(('A', 'B', 'C', 'D', 'E', 'FX'), map(number, percentages)))} if len(percentages) == 6 else None
    date = get('Dátum poslednej zmeny')
    try:
        date = datetime.strptime(date, '%d.%m.%Y').date().isoformat()
    except (TypeError, ValueError):
        date = None
    if not get('Kód predmetu') or not get('Názov predmetu'):
        raise ValueError('Missing code/name')
    return dict(predmet_id=predmet_id, code=get('Kód predmetu'), name=get('Názov predmetu'),
                academic_year=academic_year, source_url=BASE + 'tlacPredmetuOSP.mais?predmetId=' + predmet_id,
                fetched_at=fetched_at, sections=sections,
                fields=dict(department=get('Pracovisko'), credits=number(get('Počet kreditov')),
                            recommended_semester=(get('Odporúčaný semester štúdia') or '').split('\n')[0] or None,
                            completion=get('Spôsob hodnotenia a skončenia štúdia predmetu'),
                            last_changed=date, approved_by=get('Schválil')),
                programs=programs if program_table_present else None, grades=grades,
                teachers=get('Zabezpečuje').split('\n') if get('Zabezpečuje') else None,
                full_text=full_text, unknown_labels=[s['label'] for s in sections if s['label'] not in KNOWN_LABELS])


def parse_plan(html, metadata):
    soup = BeautifulSoup(html, 'html.parser')
    heading = soup.find('h2')
    if heading is None:
        raise ValueError('Missing program heading')
    if metadata.get('name') and metadata.get('code'):
        expected = metadata['name'] + ' (' + metadata['code'] + ')'
        if flat(heading) != expected:
            raise ValueError(f'Wrong plan returned: expected {expected}, got {flat(heading)}')
    container = soup.new_tag('div')
    for sibling in list(heading.next_siblings):
        container.append(sibling.extract())
    container.insert(0, heading.extract())
    header_table = container.find('table')
    header, profile = [], ''
    for row in header_table.find_all('tr'):
        cells = row.find_all('td', recursive=False)
        if len(cells) == 2:
            label, value = map(text, cells)
            if label == 'Profil absolventa':
                profile = value
            else:
                header.append(dict(label=label, text=value))
    plan = []
    for table in container.select('table.basic_grid'):
        columns = [flat(c) for c in table.select('tr:first-child th')]
        state_exam = 'Fakulta' in columns
        preceding = table.find_previous(['h3', 'h2'])
        period = flat(preceding) if preceding else None
        block = 'state_exam' if state_exam else 'plan'
        for row in table.find_all('tr'):
            cells = row.find_all('td', recursive=False)
            if not cells:
                continue
            if len(cells) == 7 and cells[5].get('colspan') == '3':
                empty = soup.new_tag('td')
                cells = cells[:6] + [empty, empty] + cells[6:]
            if len(cells) != 9:
                raise ValueError(f'Unexpected plan columns: {len(cells)}')
            match = re.search(r'predmetId\.value\s*=\s*[\x27\"]?(\d+)', str(cells[-1]))
            if not match:
                raise ValueError('Missing predmetId in plan row')
            v = [flat(c) for c in cells]
            name_match = re.fullmatch(r'(.*)\s+\(([^()]*)\)', v[2])
            plan.append(dict(period=None if state_exam else period, code=v[1],
                             name=name_match[1].strip() if name_match else v[2],
                             short_name=name_match[2] if name_match else None,
                             completion=v[3], credits=number(v[4]), type=v[5], profile_course=v[6],
                             hours=None if state_exam else v[7], faculty=v[7] if state_exam else None,
                             predmet_id=match[1], block=block))
    if not plan:
        raise ValueError('No plan rows')
    rules = [normalize(s) for s in container.stripped_strings if s.startswith('V období od')]
    return dict(**metadata, header=header, profile=profile, plan=plan, rules=rules, full_text=text(container))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


class Client:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'FEI-course-information-scraper/1.0'
        self.last = 0

    def request(self, method, url, **kwargs):
        # Handle redirects explicitly so the one-second delay also applies to them.
        for attempt in range(4):
            try:
                current_method, current_url = method, url
                current_kwargs = kwargs.copy()
                for _ in range(10):
                    time.sleep(max(0, 1.05 - (time.monotonic() - self.last)))
                    self.last = time.monotonic()
                    response = self.session.request(current_method, current_url, timeout=60,
                                                    allow_redirects=False, **current_kwargs)
                    response.raise_for_status()
                    if not response.is_redirect:
                        return response.content.decode('utf-8')
                    current_url = requests.compat.urljoin(current_url, response.headers['Location'])
                    if response.status_code in (301, 302, 303):
                        current_method, current_kwargs = 'GET', {}
                raise ValueError('Too many redirects')
            except (requests.RequestException, UnicodeError):
                if attempt == 3:
                    raise
                time.sleep(2 ** (attempt + 1))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', default='2026/2027')
    parser.add_argument('--faculty', default='FEI')
    parser.add_argument('--degree', nargs='+', default=DEGREES)
    parser.add_argument('--form', nargs='+', default=['DENNA'])
    parser.add_argument('--out', type=Path)
    parser.add_argument('--cache', type=Path, default=Path('.cache/mais'))
    parser.add_argument('--parse-only', action='store_true')
    args = parser.parse_args(argv)
    if not re.fullmatch(r'\d{4}/\d{4}', args.year):
        parser.error('--year must be YYYY/YYYY')
    output = args.out or Path('data/mais') / (args.year[:4] + '-' + args.year[-2:])
    cache = args.cache / (args.year.replace('/', '-') + '-' + args.faculty)
    cache.mkdir(parents=True, exist_ok=True)
    index_path = cache / 'index.json'
    failures, programs = [], []
    client = None

    def cached(path, method, url, **kwargs):
        nonlocal client
        sidecar = path.with_suffix('.meta.json')
        if path.exists() and sidecar.exists():
            return path.read_text(encoding='utf-8'), json.loads(sidecar.read_text(encoding='utf-8'))['fetched_at']
        if args.parse_only:
            raise ValueError(f'Missing cache: {path}')
        if client is None:
            client = Client()
        html = client.request(method, url, **kwargs)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding='utf-8')
        stamp = now()
        write_json(sidecar, {'fetched_at': stamp})
        return html, stamp

    try:
        if args.parse_only:
            index = json.loads(index_path.read_text(encoding='utf-8'))
        else:
            client = Client()
            initial = client.request('GET', BASE + 'studijneProgramy.mais')
            soup = BeautifulSoup(initial, 'html.parser')
            def option(name, wanted):
                for o in soup.select(f'select[name="{name}"] option'):
                    if wanted == o.get('value') or wanted == flat(o) or f'({wanted})' in flat(o):
                        return o['value']
                raise ValueError(f'Unknown {name}: {wanted}')
            faculty = option('zvolenaFakultaId', args.faculty)
            year = option('zvolenyARKSId', args.year)
            index = []
            for form in args.form:
                for degree in args.degree:
                    data = dict(zvolenaFakultaId=faculty, zvolenyARKSId=year,
                                zvolenaFormaStudia=form, zvolenyStupenStudia=degree,
                                zvolenyStudijnyProgramStudiaId='', akcia='stupen_studia')
                    listing, _ = cached(cache / f'list-{form}-{degree}.html', 'POST', BASE + 'studijneProgramy.mais', data=data)
                    options = BeautifulSoup(listing, 'html.parser').select('select[name=zvolenyStudijnyProgramStudiaId] option')
                    for o in options:
                        if o.get('value'):
                            match = re.fullmatch(r'(.*)\s+\(([^()]*)\)', flat(o))
                            if not match:
                                raise ValueError('Unrecognized program name/code')
                            index.append(dict(program_id=o['value'], name=match[1].strip(), code=match[2], form=form, degree=degree))
            write_json(index_path, index)
        selected = [p for p in index if p['form'] in args.form and p['degree'] in args.degree]
        if not selected:
            raise ValueError('No programs for requested scope')
        for meta in selected:
            try:
                data = dict(zvolenaFakultaId=faculty, zvolenyARKSId=year,
                            zvolenaFormaStudia=meta['form'], zvolenyStupenStudia=meta['degree'],
                            zvolenyStudijnyProgramStudiaId=meta['program_id'], akcia='zobraz_studijny_program') if not args.parse_only else {}
                html, _ = cached(cache / 'plans' / (meta['program_id'] + '.html'), 'POST', BASE + 'studijneProgramy.mais', data=data)
                program = parse_plan(html, meta)
                if not any(h['label'] == 'Akademický rok' and h['text'] == args.year for h in program['header']):
                    raise ValueError('Plan academic year does not match requested year')
                programs.append(program)
                print('Plan', meta['program_id'], flush=True)
            except (ValueError, OSError, requests.RequestException) as error:
                failures.append({'predmet_id': None, 'error': f"Program {meta['program_id']}: {error}"})
                print(f"Program {meta['program_id']} failed: {error}", file=sys.stderr, flush=True)
        programs.sort(key=lambda p: (p['form'], p['degree'], p['code']))
        write_json(output / 'programs.json', programs)
        ids = sorted({r['predmet_id'] for p in programs for r in p['plan']})
        sheets = []
        courses = output / 'courses'
        courses.mkdir(parents=True, exist_ok=True)
        for i, pid in enumerate(ids, 1):
            try:
                html, stamp = cached(cache / 'sheets' / (pid + '.html'), 'GET', BASE + 'tlacPredmetuOSP.mais?predmetId=' + pid)
                sheet = parse_sheet(html, pid, args.year, stamp)
                write_json(courses / (pid + '.json'), sheet)
                sheets.append(sheet)
            except (ValueError, OSError, requests.RequestException) as error:
                failures.append({'predmet_id': pid, 'error': str(error)})
                print(f'Sheet {pid} failed: {error}', file=sys.stderr, flush=True)
            print(f'Sheet {i}/{len(ids)} {pid}', flush=True)
        # Remove only generated numeric course files inside the selected output directory.
        successful = {s['predmet_id'] for s in sheets}
        for path in courses.glob('*.json'):
            if path.stem.isdigit() and path.stem not in successful:
                path.unlink()
    except (ValueError, OSError, requests.RequestException) as error:
        failures.append({'predmet_id': None, 'error': str(error)})
        sheets = []
    manifest = dict(source=BASE, scraped_at=now(), academic_year=args.year, faculty=args.faculty,
                    degrees=args.degree, forms=args.form,
                    counts=dict(programs=len(programs), plan_rows=sum(len(p['plan']) for p in programs),
                                sheets=len(sheets), unique_course_codes=len({s['code'] for s in sheets})), failures=failures)
    write_json(output / 'manifest.json', manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return int(bool(failures))


if __name__ == '__main__':
    sys.exit(main())
