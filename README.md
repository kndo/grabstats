# grabstats

Grabstats is a super simple command-line interface to scrape NBA box scores
from www.basketball-reference.com.

You can grab the box scores for all games in a given day
(e.g. `grabstats 2018-11-15`) or a given month (e.g. `grabstats 2018-10`).

By default, the grabbed box scores are saved as CSV files called
`basic_box_score.csv` and `adv_box_score.csv`. If they don't already exist,
those files will be created. You can also specify somewhere else to save the
box scores with the `-b/--basic` and `-a/--adv` flags. For example,
`grabstats -b my_basic_boxscore.csv -a my_adv_boxscore.csv 2018-10-23` will
grab all the box scores for October 23, 2018 and save them to those files.
