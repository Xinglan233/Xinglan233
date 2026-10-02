"""Offline tests. All numeric examples below are synthetic fixtures, not account data."""
import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('profile', ROOT / 'scripts/update_profile.py')
profile = None
if spec and Path(spec.origin).exists():
    profile = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(profile)


def repo(name='example', private=False, fork=False, archived=False, stars=2, lang='Python', size=100):
    return {'name': name, 'isPrivate': private, 'isFork': fork, 'isArchived': archived,
            'stargazerCount': stars, 'owner': {'login': 'Xinglan233'},
            'languages': {'edges': [{'size': size, 'node': {'name': lang}}],
                          'pageInfo': {'hasNextPage': False}}}


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(profile, 'The profile generator has not been implemented yet.')

    def test_rank_zero(self):
        self.assertEqual(profile.calculate_rank(0, 0, 0, 0, 0, 0), ('C', 100.0))

    def test_rank_medians(self):
        level, percentile = profile.calculate_rank(250, 50, 25, 2, 50, 10)
        self.assertEqual(level, 'B+')
        self.assertAlmostEqual(percentile, 50.0)

    def test_rank_improves(self):
        low = profile.calculate_rank(1, 1, 1, 1, 1, 1)[1]
        high = profile.calculate_rank(500, 80, 50, 10, 100, 30)[1]
        self.assertLess(high, low)

    def test_rank_rejects_negative(self):
        with self.assertRaises(ValueError):
            profile.calculate_rank(-1, 0, 0, 0, 0, 0)

    def test_public_own_nonfork_repositories_only(self):
        other = repo(); other['owner']['login'] = 'another-owner'
        summary = profile.aggregate_repositories([repo(), repo('PRIVATE_SENTINEL', private=True),
            repo('fork', fork=True), repo('Xinglan233'), other], 'Xinglan233')
        self.assertEqual(summary['stars'], 2)
        self.assertEqual(summary['languages'], {'Python': 100})
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(summary))

    def test_archived_repositories_keep_stars_not_languages(self):
        summary = profile.aggregate_repositories([repo(archived=True)], 'Xinglan233')
        self.assertEqual(summary['stars'], 2)
        self.assertEqual(summary['languages'], {})

    def test_language_pagination_does_not_silently_truncate(self):
        value = repo(); value['languages']['pageInfo']['hasNextPage'] = True
        with self.assertRaises(ValueError):
            profile.aggregate_repositories([value], 'Xinglan233')

    def test_percentages_sum_exactly_to_100(self):
        rows = profile.language_rows({'A': 1, 'B': 1, 'C': 1})
        self.assertEqual(sum(row['tenths'] for row in rows), 1000)

    def test_remainder_goes_to_other(self):
        rows = profile.language_rows({str(i): 10 - i for i in range(8)})
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[-1]['name'], 'Other')
        self.assertEqual(sum(row['bytes'] for row in rows), 52)

    def test_empty_languages(self):
        self.assertEqual(profile.language_rows({}), [])

    def test_svg_variants_are_well_formed(self):
        for dark in (False, True):
            for mobile in (False, True):
                text = profile.render_svg(None, dark=dark, mobile=mobile)
                root = ET.fromstring(text)
                self.assertTrue(root.tag.endswith('svg'))
                self.assertIn('Awaiting first sync', text)
                self.assertIn('—', text)
                self.assertNotIn('<script', text)
                self.assertNotIn('<foreignObject', text)

    def test_language_names_are_xml_escaped(self):
        stats = {'commits': 12, 'prs': 2, 'issues': 1, 'reviews': 1, 'stars': 0,
                 'followers': 1, 'languages': {'<script>&"': 50},
                 'date': '2026-09-30', 'year': 2026}
        text = profile.render_svg(stats, dark=False, mobile=False)
        ET.fromstring(text)
        self.assertNotIn('<script>', text)
        self.assertIn('&lt;script&gt;', text)

    def test_readme_markers_preserve_personal_text(self):
        original = 'Before\n<!-- PROFILE:START -->\nold\n<!-- PROFILE:END -->\nAfter'
        actual = profile.replace_details(original, 'new')
        self.assertEqual(actual, 'Before\n<!-- PROFILE:START -->\nnew\n<!-- PROFILE:END -->\nAfter')

    def test_missing_markers_fail_closed(self):
        with self.assertRaises(ValueError):
            profile.replace_details('No markers', 'new')

    def test_repository_pages_are_all_read(self):
        fake_user = {'login': 'Xinglan233', 'followers': {'totalCount': 3},
                     'contributionsCollection': {'totalCommitContributions': 9,
                         'totalPullRequestReviewContributions': 2}}
        page1 = {'user': dict(fake_user, repositories={'nodes': [repo()],
                    'pageInfo': {'hasNextPage': True, 'endCursor': 'NEXT'}}),
                 'prs': {'issueCount': 4}, 'issues': {'issueCount': 1}}
        page2 = {'user': {'repositories': {'nodes': [repo('second', lang='Java', size=50)],
                    'pageInfo': {'hasNextPage': False, 'endCursor': 'END'}}}}
        with patch.object(profile, 'graphql', side_effect=[page1, page2]) as call:
            stats = profile.fetch_stats('Xinglan233', 'test-token')
        self.assertEqual(stats['stars'], 4)
        self.assertEqual(stats['languages'], {'Python': 100, 'Java': 50})
        self.assertEqual(call.call_args_list[1].args[1]['after'], 'NEXT')

    def test_github_errors_do_not_become_zero_stats(self):
        with patch.object(profile, 'graphql', side_effect=RuntimeError('API unavailable')):
            with self.assertRaises(RuntimeError):
                profile.fetch_stats('Xinglan233', 'test-token')

    def test_preview_does_not_need_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            profile.write_assets(Path(directory), None)
            self.assertEqual(len(list(Path(directory).glob('*.svg'))), 4)


class PublicationTests(unittest.TestCase):
    def test_mobile_language_names_are_clipped_to_their_column(self):
        sample = {'commits': 1, 'prs': 1, 'issues': 1, 'reviews': 1, 'stars': 1,
                  'followers': 1, 'languages': {'An exceptionally long language name': 1},
                  'date': '2026-09-30', 'year': 2026}
        self.assertIn('language-label-0', profile.render_svg(sample, dark=False, mobile=True))

    def test_missing_token_keeps_previous_files(self):
        import os
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            readme = Path(tmp) / 'README.md'
            readme.write_text('do not overwrite', encoding='utf-8')
            env = dict(os.environ)
            env.pop('GITHUB_TOKEN', None)
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/update_profile.py'),
                '--readme', str(readme), '--output', str(Path(tmp) / 'assets')],
                env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(readme.read_text(), 'do not overwrite')
            self.assertFalse((Path(tmp) / 'assets').exists())

    def test_duplicate_markers_are_rejected(self):
        with self.assertRaises(ValueError):
            profile.replace_details(profile.START + profile.START + profile.END, 'new')

    def test_reverse_markers_are_rejected(self):
        with self.assertRaises(ValueError):
            profile.replace_details(profile.END + profile.START, 'new')

    def test_all_readme_images_exist(self):
        import re
        references = re.findall(r'(?:src|srcset)="[^"]*/(activity-[^"]+\.svg)"',
                                (ROOT / 'README.md').read_text(encoding='utf-8'))
        self.assertEqual(len(references), 4)
        self.assertEqual(set(references), set(profile.asset_texts(None)))
        for name in references:
            self.assertTrue((ROOT / 'assets' / name).is_file())


if __name__ == '__main__':
    unittest.main()
