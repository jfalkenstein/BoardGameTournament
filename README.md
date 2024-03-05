Usage: game-tournament [OPTIONS] COMMAND [ARGS]...

  This is a CLI Tool for creating and running rankings for a Board Game
  Tournament.

  It creates a "meta-score" for each game, whether there are points for the
  game or only just a set of rankings.

  Rather than being an "elimination" tournament, it calculates an average
  meta-score across all games.

  In order to run a tournament, you need to run the "init" command to set up
  the database. After that, you can use the "add-scores" command

Options:
  --help  Show this message and exit.

Commands:
  add-scores  Adds scores for a game
  get-scores  Gets the current rankings/scores for the tournament
  init        Sets up the tournament database.
  log         Gets ALL scores currently entered for the game
  recalc      Recalculate all scores
