"""
"""

import os

from bs4 import BeautifulSoup
import pandas as pd
import requests


def _get_data_stat(row, data_stat, is_header=False):
    if is_header:
        return row.find('th', {'data-stat': data_stat}).text
    return row.find('td', {'data-stat': data_stat}).text


def format_time(mp):
    """Convert minutes played from analog time to digital time.

    :param str mp: minutes played, e.g. '24:30'

    :return int: e.g. 24.5
    """
    (m, s) = mp.split(':')
    digital = int(m) + int(s) / 60
    return round(digital, 1)


class BoxScore:
    def __init__(self, soup):
        self.soup = soup

    def get(self, team_name):
        box_score = pd.DataFrame()
        table = self.soup.find('table', {'id': f'box_{team_name}_{self.box_score_type}'})
        rows = table.find('tbody').find_all('tr')

        player_rows = [row for row in rows if row.td]

        active_player_rows = [row for row in player_rows
                              if row.td.get('data-stat') == 'mp']
        inactive_player_rows = [row for row in player_rows
                                if row.td.get('data-stat') == 'reason']

        for data_stat in self.data_stats:
            if data_stat == 'player':
                is_header = True
            else:
                is_header = False
            box_score[data_stat] = [_get_data_stat(row, data_stat, is_header)
                                    for row in active_player_rows]

        box_score['mp'] = box_score['mp'].apply(format_time)
        return box_score


class BasicBoxScore(BoxScore):
    def __init__(self, soup):
        super().__init__(soup)

        self.box_score_type = 'basic'
        self.data_stats = [
            'player', 'mp',
            'fg', 'fga', 'fg_pct',
#             'fg3', 'fg3a', 'fg3_pct',
#             'ft', 'fta', 'ft_pct',
#             'orb', 'drb', 'trb',
#             'ast', 'stl', 'blk',
#             'tov', 'pf',
            'pts',
            'plus_minus',
        ]


class AdvBoxScore(BoxScore):
    def __init__(self, soup):
        super().__init__(soup)

        self.box_score_type = 'advanced'
        self.data_stats = [
            'player', 'mp',
#             'ts_pct', 'efg_pct',
#             'fg3a_per_fga_pct', 'fta_per_fga_pct',
#             'orb_pct', 'drb_pct', 'trb_pct',
#             'ast_pct', 'stl_pct', 'blk_pct',
            'tov_pct', 'usg_pct',
            'off_rtg', 'def_rtg',
        ]


def box_scores_get_one(team_name, url):
    """Get the basic and advanced box scores for one team and one game.

    :param str team_name: the capitalized abbreviated name, e.g. 'DEN'
    :param str url: the URL to the box score page on basketball-reference.com
    """

    page = requests.get(url).text
    soup = BeautifulSoup(page, 'lxml')

    basic = BasicBoxScore(soup).get(team_name.lower())
    adv = AdvBoxScore(soup).get(team_name.lower())

    basic['usg_pct'] = adv['usg_pct']

    return basic, adv


def box_scores_get_many(schedule):
    """
    :param pd.DataFrame schedule: contains game info for the schedule of games

    :return tuple: to be finished ...
    """

    basic_box_scores = []
    adv_box_scores = []

    for idx, row in schedule.iterrows():
        game_date = row['DATE']
        road_team_abbr = row['ROAD_TEAM_ABBR']
        home_team_abbr = row['HOME_TEAM_ABBR']
        box_score_url = row['BOX_SCORE_URL']

        road_basic, road_adv = box_scores_get_one(road_team_abbr, box_score_url)
        home_basic, home_adv = box_scores_get_one(home_team_abbr, box_score_url)

        # BASIC BOX SCORE
        # Road team
        road_basic['DATE'] = game_date
        road_basic['OWN_TEAM'] = road_team_abbr
        road_basic['OPP_TEAM'] = home_team_abbr
        road_basic['VENUE'] = 'R'

        # Home team
        home_basic['DATE'] = game_date
        home_basic['OWN_TEAM'] = home_team_abbr
        home_basic['OPP_TEAM'] = road_team_abbr
        home_basic['VENUE'] = 'H'

        basic = pd.concat([road_basic, home_basic])

#         reordered_cols = [
#             'DATE', 'PLAYER_NAME', 'OWN_TEAM', 'OPP_TEAM', 'VENUE', 'MP',
#             'FG', 'FGA', 'FG%', '3P', '3PA', '3P%', 'FT', 'FTA', 'FT%',
#             'ORB', 'DRB', 'TRB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS',
#             '+/-', 'USG%', 'PACE'
#         ]
#         basic = basic[reordered_cols]
        basic_box_scores.append(basic)

        # ADVANCED BOX SCORE
        # Road team
        road_adv['DATE'] = game_date
        road_adv['OWN_TEAM'] = road_team_abbr
        road_adv['OPP_TEAM'] = home_team_abbr
        road_adv['VENUE'] = 'R'

        # Home team
        home_adv['DATE'] = game_date
        home_adv['OWN_TEAM'] = home_team_abbr
        home_adv['OPP_TEAM'] = road_team_abbr
        home_adv['VENUE'] = 'H'

        adv = pd.concat([road_adv, home_adv])

#         reordered_cols = [
#             'DATE', 'PLAYER_NAME', 'OWN_TEAM', 'OPP_TEAM', 'VENUE', 'MP',
#             'TS%', 'eFG%', '3PAr', 'FTr', 'ORB%', 'DRB%', 'TRB%', 'AST%',
#             'STL%', 'BLK%', 'TOV%', 'USG%', 'ORtg', 'DRtg'
#         ]
#         adv = adv[reordered_cols]
        adv_box_scores.append(adv)

    return basic_box_scores, adv_box_scores


def to_csv(box_score, outfile):
    if os.path.isfile(outfile):
        header = False
    header = True

    with open(outfile, 'a') as f:
        box_score.to_csv(f, header=header, index=False)