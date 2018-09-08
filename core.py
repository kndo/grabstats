import os

import requests
import yaml
from lxml import html
from dateutil import parser

import numpy as np
import pandas as pd


with open('teams.yaml', 'r') as f:
    team_name_abbrev = yaml.load(f)

def get_monthly_schedule(year, month):
    """
    year: a string, e.g. 2018
    month: a string, e.g. january
    """
    url = f'https://www.basketball-reference.com/leagues/NBA_{year}_games-{month}.html'
    page = requests.get(url)
    tree = html.fromstring(page.content)

    game_date = tree.xpath('//*[@data-stat="date_game"]/a/text()')

    road_team = tree.xpath('//*[@data-stat="visitor_team_name"]/a/text()')
    road_pts = tree.xpath('//*[@data-stat="visitor_pts"]/text()')
    road_pts.pop(0)  # Remove col name

    home_team = tree.xpath('//*[@data-stat="home_team_name"]/a/text()')
    home_pts = tree.xpath('//*[@data-stat="home_pts"]/text()')
    home_pts.pop(0)  # Remove col name

    box_score_url = tree.xpath('//*[@data-stat="box_score_text"]/a/@href')

    sched = {
        'DATE':           game_date,
        'ROAD_TEAM':      road_team,
        'ROAD_PTS':       road_pts,
        'HOME_TEAM':      home_team,
        'HOME_PTS':       home_pts,
        'BOX_SCORE_URL':  box_score_url,
    }

    sched = pd.DataFrame(sched)
    sched['ROAD_TM'] = sched['ROAD_TEAM'].map(team_name_abbrev)
    sched['HOME_TM'] = sched['HOME_TEAM'].map(team_name_abbrev)
    sched = sched[['DATE', 'ROAD_TEAM', 'ROAD_TM', 'ROAD_PTS',
                           'HOME_TEAM', 'HOME_TM', 'HOME_PTS', 'BOX_SCORE_URL']]

    BBALLREF = 'https://www.basketball-reference.com'
    sched['BOX_SCORE_URL'] = sched['BOX_SCORE_URL'].apply(lambda x: BBALLREF + x)

    def format_date(date):
        date = parser.parse(date)
        return date.strftime('%Y-%m-%d')

    sched['DATE'] = sched['DATE'].apply(format_date)

    return sched


def get_daily_schedule(date):
    """
    date: a string with format 'YYYY-MM-DD'
    """

    # Get month and year from date
    parsed_date = parser.parse(date)
    month = parsed_date.strftime('%B').lower()  # Long name, e.g. january
    year = parsed_date.strftime('%Y')           # E.g. 2018

    if month in ['october, november, december']:
        year = str(int(year) + 1)  # Increment year

    sched = get_monthly_schedule(year, month)

    return sched.query('DATE == @date').reset_index(drop=True)


class BoxScore:
    def __init__(self, tree):
        self.tree = tree

    def _get_col(self, col_name):
        subtree = self.tree.xpath(self.table + f'//td[@data-stat="{col_name}"]')
        return [el.text for el in subtree]

    def _get_players(self):
        inactive_players = []
        rows = self.tree.xpath(self.table + '/tbody/tr')
        for row in rows:
            player = row.xpath('th/a/text()')
            stats = row.xpath('td/text()')
            if len(stats) == 1:
                inactive_players.append(player[0])

        active_players = self.tree.xpath(self.table + '//th[@data-stat="player"]/a/text()')
        for player in inactive_players:
            active_players.remove(player)
        active_players.append('Team Totals')

        return active_players, inactive_players


    def _format_time(MP):
        if len(MP.split(':')) > 1:
            (m, s) = MP.split(':')
            return int(m) + int(s) / 60
        else:
            return int(MP)


class BasicBoxScore(BoxScore):
    def get(self, team_name):
        self.table = f'//*[@id="box_{team_name}_basic"]'

        box_score = {}
        active_players, inactive_players = self._get_players()
        box_score['PLAYER_NAME'] = active_players

        col_names = self.tree.xpath(self.table + '/thead/tr[2]/th/text()')
        col_names.pop(0)   # Remove player name col

        data_stats = self.tree.xpath(self.table + '/thead/tr[2]/th/@data-stat')
        data_stats.pop(0)  # Remove player name data attribute

        for col, stat in zip(col_names, data_stats):
            box_score[col] = self._get_col(stat)

        box_score = pd.DataFrame(box_score)
        box_score.fillna(value=np.nan, inplace=True)

        box_score['MP'] = box_score['MP'].apply(BasicBoxScore._format_time)

        return box_score


class AdvancedBoxScore(BoxScore):
    def get(self, team_name):
        self.table = f'//*[@id="box_{team_name}_advanced"]'

        box_score = {}
        active_players, inactive_players = self._get_players()
        box_score['PLAYER_NAME'] = active_players

        col_names = self.tree.xpath(self.table + '/thead/tr[2]/th/text()')
        col_names.pop(0)   # Remove player name col

        data_stats = self.tree.xpath(self.table + '/thead/tr[2]/th/@data-stat')
        data_stats.pop(0)  # Remove player name data attribute

        for col, stat in zip(col_names, data_stats):
            box_score[col] = self._get_col(stat)

        box_score = pd.DataFrame(box_score)
        box_score.fillna(value=np.nan, inplace=True)

        box_score['MP'] = box_score['MP'].apply(BoxScore._format_time)

        return box_score


def get_box_scores(date, team_name, url):
    page = requests.get(url)
    tree = html.fromstring(page.content)

    basic = BasicBoxScore(tree).get(team_name.lower())
    adv = AdvancedBoxScore(tree).get(team_name.lower())

    basic['USG%'] = adv['USG%']

    return basic, adv


def get_daily_box_scores(schedule, basic_box_score_outfile, adv_box_score_outfile):
    for index, row in schedule.iterrows():
        game_date = row['DATE']
        road_team = row['ROAD_TM']
        home_team = row['HOME_TM']
        box_score_url = row['BOX_SCORE_URL']

        road_basic, road_adv = get_box_scores(game_date, road_team, box_score_url)
        home_basic, home_adv = get_box_scores(game_date, home_team, box_score_url)

        # Road team
        road_basic['DATE'] = game_date
        road_basic['OWN_TEAM'] = road_team
        road_basic['OPP_TEAM'] = home_team
        road_basic['VENUE'] = 'R'

        # Home team
        home_basic['DATE'] = game_date
        home_basic['OWN_TEAM'] = home_team
        home_basic['OPP_TEAM'] = road_team
        home_basic['VENUE'] = 'H'

        basic = pd.concat([road_basic, home_basic])

        reordered_cols = ['DATE', 'PLAYER_NAME', 'OWN_TEAM', 'OPP_TEAM', 'VENUE', 'MP',
                          'FG', 'FGA', 'FG%', '3P', '3PA', '3P%', 'FT', 'FTA', 'FT%',
                          'ORB', 'DRB', 'TRB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS', '+/-', 'USG%']
        basic = basic[reordered_cols]

        if os.path.isfile(basic_box_score_outfile):
            header = False
        else:
            header = True

        with open(basic_box_score_outfile, 'a') as f:
            basic.to_csv(f, header=header, index=False)

        print(f'Grabbed {road_team} vs {home_team} box score!')
    print('All done!')


def grabstats(date, basic_box_score_outfile, adv_box_score_outfile):
    schedule = get_daily_schedule(date)
    get_daily_box_scores(
        schedule,
        basic_box_score_outfile,
        adv_box_score_outfile
    )
