#!/usr/bin/env python3

import click

from core import grabstats


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
    grabstats(date, basic, adv)


if __name__ == '__main__':
    main()
