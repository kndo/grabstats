"""
"""

import arrow
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import requests
import yaml


class MonthSchedule:
    def __init__(self, year, month):
        """
        :param str year:
        :param str month:
        """

        date = '-'.join([year, month])
        month = arrow.get(date).datetime.strftime('%B').lower()  # e.g. 'january'

        # BBallRef takes the season year as the calendar year when the Playoffs
        # are played; hence, the 2017-2018 season is the 2018 season
        if month in ['october', 'november', 'december']:
            year = str(int(year) + 1)  # Increment year

        url = f'https://www.basketball-reference.com/leagues/NBA_{year}_games-{month}.html'
        page = requests.get(url).text  # TODO: Handle request error
        self.soup = BeautifulSoup(page, 'lxml')
        self._get_schedule()


    def _get_schedule(self):
        col_game_date = self._get_col('th', 'date_game', has_title=True)
        col_road_team = self._get_col('td', 'visitor_team_name')
        col_road_team_pts = self._get_col('td', 'visitor_pts')
        col_home_team = self._get_col('td', 'home_team_name')
        col_home_team_pts = self._get_col('td', 'home_pts')
        col_box_score_url = self._get_col_box_score_url()

        schedule = {
            'DATE':          col_game_date,
            'ROAD_TEAM':     col_road_team,
            'ROAD_TEAM_PTS': col_road_team_pts,
            'HOME_TEAM':     col_home_team,
            'HOME_TEAM_PTS': col_home_team_pts,
            'BOX_SCORE_URL': col_box_score_url,
        }

        self.schedule = pd.DataFrame(schedule)
        self.schedule = self.schedule.replace('', np.nan)
        self.schedule = self.schedule.dropna(how='any')

        self._abbrev_team_names()
        self._reorder_cols()
        self._complete_box_score_url()
        self._format_date()


    def _get_col(self, tag, data_stat, has_title=False):
        """
        :param str tag: e.g. 'td'
        :param str data_stat: e.g. 'home_team_name'
        :param bool has_title: indicates whether the column has a title row
                               for its first row, which will be removed
        """

        result = self.soup.find_all(tag, {'data-stat': data_stat})
        if has_title:
            result.pop(0)
        return [row.a.text if row.a else row.text for row in result]


    def _get_col_box_score_url(self):
        result = self.soup.find_all('td', {'data-stat': 'box_score_text'})
        return [row.a.get('href') if row.a else '' for row in result]


    def _abbrev_team_names(self):
        with open('./grabstats/teams.yaml', 'r') as f:
            team_name_abbrev = yaml.safe_load(f)

        self.schedule['ROAD_TEAM_ABBR'] = \
                self.schedule['ROAD_TEAM'].map(team_name_abbrev)
        self.schedule['HOME_TEAM_ABBR'] = \
                self.schedule['HOME_TEAM'].map(team_name_abbrev)


    def _reorder_cols(self):
        reordered_cols = ['DATE',
            'ROAD_TEAM', 'ROAD_TEAM_ABBR', 'ROAD_TEAM_PTS',
            'HOME_TEAM', 'HOME_TEAM_ABBR', 'HOME_TEAM_PTS',
            'BOX_SCORE_URL'
        ]
        self.schedule = self.schedule[reordered_cols]


    def _complete_box_score_url(self):
        BBALLREF = 'https://www.basketball-reference.com'
        self.schedule['BOX_SCORE_URL'] = \
                self.schedule['BOX_SCORE_URL'].apply(lambda x: BBALLREF + x)


    def _format_date(self):
        def format_date(date):
            return arrow.get(date, 'ddd, MMM D, YYYY').datetime.strftime('%Y-%m-%d')
        self.schedule['DATE'] = self.schedule['DATE'].apply(format_date)


class DaySchedule(MonthSchedule):
    def __init__(self, year, month, day):
        super().__init__(year, month)
        date = '-'.join([year, month, day])
        self.schedule = self.schedule.query('DATE == @date').reset_index(drop=True)


def get_schedule(year, month, day=None):
    """
    :param str year:
    :param str month:
    :param str day:

    :return pd.DataFrame schedule: contains game info for games played on date,
                                   either a day or a month
    """

    if day:
        schedule = DaySchedule(year, month, day)
    else:
        schedule = MonthSchedule(year, month)

    return schedule.schedule