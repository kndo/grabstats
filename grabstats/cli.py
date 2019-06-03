#!/usr/bin/env python3

import click

from grabstats.schedule import get_schedule
from grabstats.box_score import box_scores_get_many, to_csv


@click.command()
@click.option(
    '-b',
    '--basic',
    'basic_box_score_file',
    type=click.Path(),
    default='basic_box_score.csv',
    help='CSV file to write basic box score',
)
@click.option(
    '-a',
    '--adv',
   'adv_box_score_file',
    type=click.Path(),
    default='adv_box_score.csv',
    help='CSV file to write advanced box score',
)
@click.option(
    '-dk',
    '--draftkings',
    'calc_dk',
    is_flag=True,
    help='Calculate DraftKings fantasy points'
)
@click.option(
    '-fd',
    '--fanduel',
    'calc_fd',
    is_flag=True,
    help='Calculate FanDuel fantasy points'
)
@click.argument(
    'date',
    type=click.DateTime(formats=['%Y-%m-%d', '%Y-%m'])
)
def main(date, basic_box_score_file, adv_box_score_file, calc_dk, calc_fd):
    print(date)
    year = '2019'
    month = '05'
    day = '03'
    schedule = get_schedule(year, month, day)
    basic_box_scores, adv_box_scores = box_scores_get_many(schedule)

    for box_score in basic_box_scores:
        to_csv(box_score, basic_box_score_file)

    for box_score in adv_box_scores:
        to_csv(box_score, adv_box_score_file)


if __name__ == '__main__':
    main()