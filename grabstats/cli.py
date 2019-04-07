#!/usr/bin/env python3

import sys

import click

from core import grabstats


def is_valid_date(date):
    if len(date.split('-')) == 3 or len(date.split('-')) == 2:
        return True
    return False

@click.command()
@click.option(
    '--basic',
    '-b',
    default='basic_box_score.csv',
    help='CSV file to write basic box score',
)
@click.option(
    '--adv',
    '-a',
    default='adv_box_score.csv',
    help='CSV file to write advanced box score',
)
@click.argument('date')
def main(date, basic, adv):
    if not is_valid_date(date):
        print('Error: Invalid date argument; must be YYYY-MM-DD or YYYY-MM')
        print('Exiting ...')
        sys.exit(1)
    grabstats(date, basic, adv)


if __name__ == '__main__':
    main()
