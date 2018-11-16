import os

import arrow
import requests
import yaml
from lxml import html

import numpy as np
import pandas as pd


with open('teams.yaml', 'r') as f:
    team_name_abbrev = yaml.load(f)

def get_monthly_schedule(year, month):
    """
    :param year: a string, e.g. 2018
    :param month: a string, e.g. january

    :return schedule: a pd.DataFrame containing game info for the month
    """

    url = f'https://www.basketball-reference.com/leagues/NBA_{year}_games-{month}.html'
    page = requests.get(url)
    tree = html.fromstring(page.content)

    game_date = tree.xpath('//*[@data-stat="date_game"]/a/text()')

    road_team = tree.xpath('//*[@data-stat="visitor_team_name"]/a/text()')
    road_pts = tree.xpath('//*[@data-stat="visitor_pts"]/text()')
    road_pts.pop(0)  # Remove column name

    home_team = tree.xpath('//*[@data-stat="home_team_name"]/a/text()')
    home_pts = tree.xpath('//*[@data-stat="home_pts"]/text()')
    home_pts.pop(0)  # Remove column name

    box_score_url = tree.xpath('//*[@data-stat="box_score_text"]/a/@href')

    schedule = {
        'DATE':           game_date,
        'ROAD_TEAM':      road_team,
        'ROAD_PTS':       road_pts,
        'HOME_TEAM':      home_team,
        'HOME_PTS':       home_pts,
        'BOX_SCORE_URL':  box_score_url,
    }

    # Create a dictionary with different length columns (Series) that is
    # suitable for a DataFrame
    schedule = dict([ (k, pd.Series(v)) for k, v in schedule.items() ])
    schedule = pd.DataFrame(schedule)
    schedule.dropna(how='any', inplace=True)
    schedule['ROAD_TM'] = schedule['ROAD_TEAM'].map(team_name_abbrev)
    schedule['HOME_TM'] = schedule['HOME_TEAM'].map(team_name_abbrev)
    schedule = schedule[['DATE', 'ROAD_TEAM', 'ROAD_TM', 'ROAD_PTS',
                         'HOME_TEAM', 'HOME_TM', 'HOME_PTS', 'BOX_SCORE_URL']]

    BBALLREF = 'https://www.basketball-reference.com'
    schedule['BOX_SCORE_URL'] = \
            schedule['BOX_SCORE_URL'].apply(lambda x: BBALLREF + x)

    def format_date(date):
        return arrow.get(date, 'ddd, MMM D, YYYY').datetime.strftime('%Y-%m-%d')

    schedule['DATE'] = schedule['DATE'].apply(format_date)

    return schedule


def get_schedule(date):
    """
    :param date: a string with format 'YYYY-MM-DD' or 'YYYY-MM'

    :return schedule: a pd.DataFrame containing game info for the date,
                      either a day or month
    """

    # Get year and month from date
    year = arrow.get(date).datetime.strftime('%Y')           # e.g. 2018
    month = arrow.get(date).datetime.strftime('%B').lower()  # e.g. january

    # BBallRef takes the season year as the calendar year when the Playoffs
    # are played; therefore, the 2017-2018 season is the 2018 season
    if month in ['october', 'november', 'december']:
        year = str(int(year) + 1)  # Increment year

    schedule = get_monthly_schedule(year, month)

    # If year year, month, and day given in date, return daily schedule
    if len(date.split('-')) == 3:
        return schedule.query('DATE == @date').reset_index(drop=True)
    return schedule  # monthly schedule


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
            # Indicates an inactive player, e.g. 'Did Not Play'
            if len(stats) == 1:
                if all(x.isalpha() or x.isspace() for x in stats[0]):
                    inactive_players.append(player[0])

        active_players = \
                self.tree.xpath(self.table + '//th[@data-stat="player"]/a/text()')
        for player in inactive_players:
            active_players.remove(player)
        # Each box score has a row for team totals, which we take as an active
        # player for now, and can remove/separate in post-processing
        active_players.append('Team Totals')

        return active_players, inactive_players

    def _format_time(MP):
        """ Convert minutes played from str to int/float """
        if len(MP.split(':')) > 1:
            (m, s) = MP.split(':')
            return int(m) + int(s) / 60
        else:
            return int(MP)

    def _get_pace(self):
        for comment in self.tree.xpath('//comment()'):
            c = str(comment)
            if '"pace"' in c:
                c = c.lstrip('<!--')
                c = c.rstrip('-->')
                c = c.strip()
                subtree = html.fromstring(c)
                pace = subtree.xpath('//td[@data-stat="pace"]')[0].text
        return pace


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

        box_score['MP'] = box_score['MP'].apply(BoxScore._format_time)
        box_score['PACE'] = BoxScore._get_pace(self)

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


def get_daily_box_scores(schedule, basic_box_score_file, adv_box_score_file):
    for index, row in schedule.iterrows():
        game_date = row['DATE']
        road_team = row['ROAD_TM']
        home_team = row['HOME_TM']
        box_score_url = row['BOX_SCORE_URL']

        road_basic, road_adv = get_box_scores(game_date, road_team, box_score_url)
        home_basic, home_adv = get_box_scores(game_date, home_team, box_score_url)

        # BASIC BOX SCORE
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

        reordered_cols = \
                ['DATE', 'PLAYER_NAME', 'OWN_TEAM', 'OPP_TEAM', 'VENUE', 'MP',
                 'FG', 'FGA', 'FG%', '3P', '3PA', '3P%', 'FT', 'FTA', 'FT%',
                 'ORB', 'DRB', 'TRB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS',
                 '+/-', 'USG%', 'PACE']
        basic = basic[reordered_cols]

        if os.path.isfile(basic_box_score_file):
            header = False
        else:
            header = True

        with open(basic_box_score_file, 'a') as f:
            basic.to_csv(f, header=header, index=False)

        # ADVANCED BOX SCORE
        # Road team
        road_adv['DATE'] = game_date
        road_adv['OWN_TEAM'] = road_team
        road_adv['OPP_TEAM'] = home_team
        road_adv['VENUE'] = 'R'

        # Home team
        home_adv['DATE'] = game_date
        home_adv['OWN_TEAM'] = home_team
        home_adv['OPP_TEAM'] = road_team
        home_adv['VENUE'] = 'H'

        adv = pd.concat([road_adv, home_adv])

        reordered_cols = \
                ['DATE', 'PLAYER_NAME', 'OWN_TEAM', 'OPP_TEAM', 'VENUE', 'MP',
                 'TS%', 'eFG%', '3PAr', 'FTr', 'ORB%', 'DRB%', 'TRB%', 'AST%',
                 'STL%', 'BLK%', 'TOV%', 'USG%', 'ORtg', 'DRtg']
        adv = adv[reordered_cols]

        if os.path.isfile(adv_box_score_file):
            header = False
        else:
            header = True

        with open(adv_box_score_file, 'a') as f:
            adv.to_csv(f, header=header, index=False)

        print(f'Grabbed {road_team} vs {home_team} box score for {game_date}')
    print('All done!')


def grabstats(date, basic_box_score_file, adv_box_score_file):
    schedule = get_schedule(date)
    get_daily_box_scores(
        schedule, basic_box_score_file, adv_box_score_file
    )
