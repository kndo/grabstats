"""
Split basic and advanced box scores into a player only and team only version
"""

import pandas as pd
pd.set_option('expand_frame_repr', False)
pd.set_option('max_rows', 100)


basic_box_score_file = 'basic_box_score.csv'
adv_box_score_file = 'adv_box_score.csv'

basic = pd.read_csv(basic_box_score_file)
adv = pd.read_csv(adv_box_score_file)

pl_basic = basic[basic.PLAYER_NAME != 'Team Totals'].copy()
tm_basic = basic[basic.PLAYER_NAME == 'Team Totals'].copy()
tm_basic.drop(columns=['PLAYER_NAME', '+/-', 'USG%'], inplace=True)
