# buckshot-python 

a GUI-less implementation of buckshot roulette in python, meant for training agents to play the game.

it's worth nothing that this isn't particularly special and that implementations of this game in python for the specific purpose of RL training has been done before.  I mostly did this because it was fun.

if `buckshot.py` is run as the main script, it includes a very crappy user interface that mostly just exists for debugging purposes, but gives a good guideline as to how to use the `BuckshotRun` class appropriately.

# getting started

a single run (from starting the game to player death) of buckshot roulette is managed by the `BuckshotRun` class.

```python
run = BuckshotRun()
```

on it's own, this creates a player and a dealer (including AI), and has all of the game logic.  a simple flow of a single run should look something like this:

```python
run = BuckshotRun()

while not run.is_over():

    if run.is_player_turn():
        # take player actions...
    else:
        try:
            run.dealer_ai_turn()
        except RoundResetException:
            pass
```

quick explanation:

`run.is_over()` is `True` if the player is dead.

`run.is_player_turn()` is `True` if the player should take actions, such as shooting and using items.

`run.dealer_ai_turn()` runs the dealer AI for taking turns until the dealer shoots someone.

`RoundResetException` is raised when use of an item causes the round to be reset or the game to end.  for example, this can happen if someone uses medicine at 1 health remaining and dies.

## player actions

`BuckshotRun` gives a few methods for allowing the player to do things.  note that these methods are actually shared by the player and the dealer, and the participant that actually does the thing depends on whose turn it is.  therefore you should be careful to only call these methods when you're sure that it is the player's turn.

`run.use_item(item_name)` uses an item in the player's inventory.  if this causes the player's turn to end, a `RoundResetException` is raised.  if the item isn't in the player's inventory, a `NoItemException` is raised.  if the item doesn't exist or is being used illegally (i.e. trying to handcuff twice) an `InvalidItemException` is raised.  **NOTE:** you should not use this method to use adrenaline.  see `run.use_adrenaline` below for that.

`run.use_adrenaline(steal_item_name)` uses adrenaline to steal an item from the dealer's inventory.  this will raise a `NoItemException` if the player doesn't have adrenaline, and all of the exceptions for `run.use_item` apply to the item being stolen.

`run.shoot(shooting_self)` shoots the next shell in the chamber.  the player will shoot at themselves if `shooting_self` is `True`, and the dealer otherwise.
