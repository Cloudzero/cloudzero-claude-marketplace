"""Allocate exact, non-negative USD amounts from a CSV stream by team."""
import argparse
import csv
from decimal import Decimal, InvalidOperation, localcontext
import json
from pathlib import Path
import sys


def allocate(stream):
    reader = csv.DictReader(stream, strict=True)
    if reader.fieldnames is None or len(reader.fieldnames) != 2 or set(reader.fieldnames) != {'team', 'amount_usd'}:
        raise ValueError('Expected exactly the columns team,amount_usd')
    totals = {}
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f'Row {reader.line_num}: expected exactly two fields')
        team = row['team'].strip(); amount_text = row['amount_usd'].strip()
        if not team or not amount_text:
            raise ValueError(f'Row {reader.line_num}: team and amount_usd must be nonblank')
        try:
            amount = Decimal(amount_text)
        except InvalidOperation as error:
            raise ValueError(f'Row {reader.line_num}: invalid amount_usd') from error
        if not amount.is_finite() or amount < 0:
            raise ValueError(f'Row {reader.line_num}: amount must be finite and non-negative')
        # USD cents are exact; reject sub-cent values rather than silently round.
        if amount.as_tuple().exponent < -2:
            raise ValueError(f'Row {reader.line_num}: amount must have at most two decimal places')
        if amount.adjusted() > 15:
            raise ValueError(f'Row {reader.line_num}: amount exceeds supported USD range')
        with localcontext() as context:
            context.prec = 50
            totals[team] = totals.get(team, Decimal(0)) + amount
    with localcontext() as context:
        context.prec = 50
        overall = sum(totals.values(), Decimal(0))
    return {'teams': {key: f'{totals[key]:.2f}' for key in sorted(totals)}, 'total_usd': f'{overall:.2f}'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_file', help='CSV file, or - for stdin')
    args = parser.parse_args()
    try:
        if args.csv_file == '-':
            result = allocate(sys.stdin)
        else:
            with Path(args.csv_file).open(newline='', encoding='utf-8-sig') as stream:
                result = allocate(stream)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, csv.Error, OSError) as error:
        print(f'Allocation error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
