"""Regression tests against real, public MAIS HTML."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scrape import check_coverage, main, parse_plan, parse_sheet

FIXTURES = Path(__file__).parent / 'fixtures'


def sheet(name='zap.html'):
    return parse_sheet((FIXTURES / name).read_text(encoding='utf-8'),
                       '65954478', '2026/2027', '2026-11-17T00:00:00Z')


def test_zap_control_values_and_table_alignment():
    result = sheet()
    assert result['code'] == '26000629'
    assert result['fields']['credits'] == 5
    assert result['fields']['last_changed'] == '2026-09-01'
    assert result['grades'] == {'total_students': 12286,
                                'percent': {'A': 19, 'B': 12, 'C': 13, 'D': 12, 'E': 16, 'FX': 28}}
    assert len(result['programs']) == 17
    assert result['programs'][4]['degree'] == '1. PO'
    assert result['programs'][2]['method'] == 'Kombinovaná'
    assert result['unknown_labels'] == []
    assert {'label': 'Podmieňujúce predmety', 'text': ''} in result['sections']
    assert any(
        '1. Úvod do informatiky\n2. Algoritmus' in s['text'] for s in result['sections'])


def test_unknown_label_and_bold_value_preserved():
    html = (FIXTURES / 'zap.html').read_text(encoding='utf-8')
    html = html.replace('<b>Poznámky:</b>', '<b>Nová sekcia:</b>')
    html = html.replace('26000629</td>', '<b>26000629</b></td>')
    result = parse_sheet(html, '1', '2026/2027', 'stamp')
    assert result['unknown_labels'] == ['Nová sekcia']
    assert result['code'] == '26000629'


def test_historical_prerequisite_sheet():
    result = sheet('prerequisite.html')
    assert result['code'] == '2609051'
    assert result['name'] == 'Počítačové siete'
    assert result['grades']['total_students'] == 426
    assert result['grades']['percent']['FX'] == 13
    assert result['unknown_labels'] == []


def test_empty_program_table_is_an_empty_list():
    from bs4 import BeautifulSoup
    soup = BeautifulSoup((FIXTURES / 'zap.html').read_text(encoding='utf-8'), 'html.parser')
    for row in list(soup.select('tr')):
        cells = row.find_all('td', recursive=False)
        if len(cells) == 4 and 'middleLeft' in cells[0].get('class', []) and cells[0].get_text(strip=True) != 'Odporúčaný semester':
            row.decompose()
    result = parse_sheet(str(soup), '65954478', '2026/2027', 'stamp')
    assert result['programs'] == []
    assert 'Odporúčaný semester' in result['full_text']


def test_coverage_rejects_loss_and_reordering():
    result = sheet()
    check_coverage(result['sections'], result['full_text'])
    result['sections'][0]['text'] = ''
    with pytest.raises(ValueError, match='coverage'):
        check_coverage(result['sections'], result['full_text'])


def test_plan_preserves_prerequisites_state_exams_and_rules():
    result = parse_plan((FIXTURES / 'plan.html').read_text(encoding='utf-8'), {})
    assert len(result['plan']) == 51
    zap = next(r for r in result['plan'] if r['predmet_id'] == '65954478')
    assert zap['period'] == '1. rok ZS'
    assert zap['short_name'] == 'ZAP'
    assert zap['credits'] == 5
    exam = next(r for r in result['plan'] if r['predmet_id'] == '69482574')
    assert exam['block'] == 'state_exam'
    assert exam['period'] is None and exam['hours'] is None
    assert exam['faculty'] == 'FEI'
    assert any(r['type'] == 'Prerekvizita' for r in result['plan'])
    assert len(result['rules']) == 14
    assert 'Profil absolventa' not in [r['label'] for r in result['header']]


def test_plan_rejects_wrong_program_from_session():
    with pytest.raises(ValueError, match='Wrong plan returned'):
        parse_plan((FIXTURES / 'plan.html').read_text(encoding='utf-8'),
                   {'name': 'Wrong program', 'code': 'WRONG'})


def test_parse_only_missing_cache_is_failure_without_network(tmp_path, monkeypatch):
    import requests
    def forbidden(*args, **kwargs):
        raise AssertionError('Network used in parse-only mode')
    monkeypatch.setattr(requests.Session, 'request', forbidden)
    output = tmp_path / 'out'
    assert main(['--parse-only', '--cache', str(tmp_path / 'cache'), '--out', str(output)]) == 1
    assert json.loads((output / 'manifest.json').read_text(encoding='utf-8'))['failures']


def test_retry_after_redirect_keeps_original_post(monkeypatch):
    import scrape
    client = scrape.Client()
    calls = []
    def request(method, url, **kwargs):
        calls.append((method, kwargs.get('data')))
        response = scrape.requests.Response()
        response.status_code = 302 if len(calls) in (1, 3) else 200
        response.headers['Location'] = 'report.htm'
        response._content = b'ok'
        if len(calls) == 2:
            raise scrape.requests.ConnectionError('Temporary failure after redirect')
        return response
    monkeypatch.setattr(client.session, 'request', request)
    monkeypatch.setattr(scrape.time, 'sleep', lambda _: None)
    assert client.request('POST', 'https://example.test/plan', data={'id': '1'}) == 'ok'
    assert calls == [('POST', {'id': '1'}), ('GET', None), ('POST', {'id': '1'}), ('GET', None)]


def test_parse_only_reproduces_cached_output_without_network(tmp_path, monkeypatch):
    import scrape
    cache_root = tmp_path / 'cache'
    cache = cache_root / '2026-2027-FEI'
    meta = dict(program_id='65699720', name='Aplikovaná elektrotechnika',
                code='ApE_Bc_D_KM', form='DENNA', degree='PRVY')
    plan_html = (FIXTURES / 'plan.html').read_text(encoding='utf-8')
    # Keep one genuine course row; this fixture checks cache/CLI orchestration.
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(plan_html, 'html.parser')
    for table in soup.select('table.basic_grid'):
        for row in list(table.find_all('tr')):
            if row.find('td') and '65954478' not in str(row):
                row.decompose()
    scrape.write_json(cache / 'index.json', [meta])
    for relative, html in [('plans/65699720.html', str(soup)),
                           ('sheets/65954478.html', (FIXTURES / 'zap.html').read_text(encoding='utf-8'))]:
        path = cache / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding='utf-8')
        scrape.write_json(path.with_suffix('.meta.json'), {'fetched_at': '2026-11-17T00:00:00Z'})
    def forbidden(*args, **kwargs):
        raise AssertionError('Network used in parse-only mode')
    monkeypatch.setattr(scrape.requests.Session, 'request', forbidden)
    output = tmp_path / 'out'
    args = ['--parse-only', '--cache', str(cache_root), '--out', str(output)]
    assert main(args) == 0
    first = {p.relative_to(output): p.read_bytes() for p in output.rglob('*.json') if p.name != 'manifest.json'}
    assert main(args) == 0
    assert first == {p.relative_to(output): p.read_bytes() for p in output.rglob('*.json') if p.name != 'manifest.json'}
