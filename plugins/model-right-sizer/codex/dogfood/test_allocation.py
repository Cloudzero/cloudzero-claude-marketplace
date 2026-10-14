import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from allocation import allocate

CLI = str(Path(__file__).with_name('allocation.py'))


class AllocationTests(unittest.TestCase):
    def test_repeated_teams_exact_cents(self):
        result = allocate(io.StringIO('team,amount_usd\na,0.10\nb,1.23\na,0.20\n'))
        self.assertEqual(result, {'teams': {'a': '0.30', 'b': '1.23'}, 'total_usd': '1.53'})

    def test_quoted_team_and_swapped_columns(self):
        self.assertEqual(allocate(io.StringIO('amount_usd,team\n2.50,"A, B"\n'))['teams'], {'A, B': '2.50'})

    def test_empty_dataset(self):
        self.assertEqual(allocate(io.StringIO('team,amount_usd\n'))['total_usd'], '0.00')

    def test_invalid_amounts(self):
        for value in ['NaN', 'Infinity', '-1', 'broken', '0.001', '1e999999', '']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                allocate(io.StringIO(f'team,amount_usd\na,{value}\n'))

    def test_invalid_rows_and_headers(self):
        for text in ['', 'team,value\na,1\n', 'team,amount_usd,team\na,1,b\n',
                     'team,amount_usd\na\n', 'team,amount_usd\na,1,extra\n', 'team,amount_usd\n ,1\n']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                allocate(io.StringIO(text))

    def test_cli_success(self):
        process = subprocess.run([sys.executable, CLI, '-'], input='team,amount_usd\na,1.20\n', text=True, capture_output=True)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(json.loads(process.stdout)['total_usd'], '1.20')

    def test_cli_error_exit(self):
        process = subprocess.run([sys.executable, CLI, '-'], input='team,amount_usd\na,NaN\n', text=True, capture_output=True)
        self.assertEqual(process.returncode, 1)
        self.assertIn('finite', process.stderr)
        self.assertFalse(process.stdout)


if __name__ == '__main__':
    unittest.main()
