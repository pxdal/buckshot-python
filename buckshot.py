### READ THIS ###
# given the large amount of subdivisions of a single run, I've given the following names to each one:

# RUN: a run is from when the player signs the contract to when the player gets the money or dies.  it is the highest level of gameplay.
# MATCH: a set of three rounds.  if the player wins a match, they get to double their money or take it home.
# ROUND: when both the player and the dealer start with some set amount of health and play until either the dealer reaches zero (the player progresses to the next round) or the player reaches zero (the player loses).  items reset between rounds, except between the third round of a match and the first round of the following match (this is probably a game bug, but for accurate behavior I've left it in)
# SET: when the shotgun is loaded with some amount of live and blank rounds, and the player and the dealer take turns until the shotgun is empty.  both the player and the dealer get a random amount of items at the start of each set.

### ACTUAL CODE NOW ###
import sys
import random

## GLOBAL GAME SETTINGS ##

live_token = True
blank_token = False

rounds_per_match = 3

min_shells_per_set = 2
max_shells_per_set = 8

min_health = 2
max_health = 4

max_items = 8

base_live_damage = 1
sawedoff_live_damage = 2

## item behaviors ##
# all item behaviors require a user and the opposite player.
# some items require additional input from the user.  not sure what to do about that yet.

def knife_behavior(run, user, opposite):
    run.is_sawed_off = True

def cigarretes_behavior(run, user, opposite):
    user.give_health(1)

# item settings #
item_behaviors = {
    "knife": knife_behavior,
    "cigarretes": cigarretes_behavior
}

item_names = self.item_behaviors.keys()


## utility methods ##

def bullet_is_live(bullet):
    return bullet == live_token

def bullet_is_blank(bullet):
    return bullet == blank_token

# create a random sequence of lives and blanks using the global settings for live and blank tokens.
# this follows the same rules as buckshot roulette, which is a little more particular than just random selection and order.  here are the rules:
# 1. there can be between 2 and 8 shells.
# 2. the number of live shells is the total amount divided by 2 and rounded down, with the rest being blanks.
# 3. the shells are arranged in a completely random order.
# this function returns the number of lives, number of blanks, and the sequence.
def get_random_chamber_sequence():
    total_shells = random.randint(min_shells_per_set, max_shells_per_set)
    
    num_live = total_shells // 2
    num_blank = total_shells - num_live
    
    # arrange them in an array and shuffle
    sequence = [live_token] * num_live + [blank_token] * num_blank
    
    random.shuffle(sequence)
    
    return sequence

# health is a random number between 2 and 4
def get_random_health():
    return random.randint(min_health, max_health)
    
## classes ##

# player inventory
class Inventory():
    
    # TODO: how the game determines what items you get is not as simple as just uniform randomness.
    @staticmethod
    def get_random_items(self, num):
        return
    
    def __init__(self):
        self.inventory = dict()
        
        # initialize counts
        for item_name in item_names:
            self.inventory[item_name] = 0
    
    def __contains__(self, item_name):
        return self.inventory[item_name] > 0
    
    def use(self, item_name):
        if not item_name in self:
            raise Exception(item_name + " is not in inventory")
        
        self.inventory[item_name] -= 1

# a participant in the game.  there are only two, the dealer and the player, but both inherit from this for shared behavior (such as health, items, etc.)
class Participant():
    def __init__(self, name):
        self.name = name
        self.health = 0
        self.inventory = Inventory()
        
        self.current_max_health = 0
    
    def set_health(self, new_health):
        self.health = new_health
        self.current_max_health = new_health
        
    def take_damage(self, damage):
        self.health -= damage
    
    def give_health(self, health):
        self.health = min(self.health + health, self.current_max_health)
        
    def is_dead(self):
        return self.health < 1
    
    def give_items(self, items):
        self.items += items
        
        # cap items
        # this is authentic, as buckshot roulette won't let you keep any items past your limit and instead makes you put them back in the box
        self.items = self.items[:max_items]
    
    def reset_items(self):
        self.items = []
        
    def has_item(self, name):
        return name in self.items

# participant with some real authentic dealer ai
class Dealer(Participant):
    def __init__(self):
        super().__init__("Dealer")
    
    def take_turn(self, run):
        run.shoot(bool(random.randint(0, 1)))
    
# an entire run of buckshot roulette, see big comment at the start of the file for definition
class BuckshotRun():
    nobody_id = -1
    player_id = 0
    dealer_id = 1
    
    def __init__(self):
        self.player = Participant("Player")
        self.dealer = Dealer()
        
        # initial health
        self.give_both_random_health()
        
        # the current sequence of bullets in the chamber
        self.chamber = []
        self.load_chamber()
        
        # matches won by the player (if the dealer wins any, it's just game over)
        self.matches_won = 0
        
        # game state settings #
        
        # will be set to true if the game is over for the player
        self.game_over = False
        
        # starts at 1 and goes up to rounds_per_match
        self.current_round = 1
        
        # who has the gun?
        self.whose_turn_id = self.player_id
        
        # NOTE: it is impossible for both player and dealer to be handcuffed at the same time
        self.who_handcuffed_id = self.nobody_id
        
        # is the end of the barrel currently sawed off?
        self.is_sawed_off = False
    
    # check integer ids
    def is_player(self, int_id):
        return int_id == self.player_id
    
    def is_dealer(self, int_id):
        return int_id == self.dealer_id
    
    def is_nobody(self, int_id):
        return int_id == self.nobody_id
    
    def get_id(self, participant):
        if participant == self.player:
            return self.player_id
        elif participant == self.dealer:
            return self.dealer_id
    
    # returns the next bullet without removing it from the chamber
    def peek_next_bullet(self):
        return self.chamber[0]
    
    # pops the bullet from the front and returns it
    def pop_next_bullet(self):
        return self.chamber.pop(0)
    
    def chamber_is_empty(self):
        return len(self.chamber) == 0
    
    def empty_chamber(self):
        self.chamber = []
    
    def load_chamber(self):
        self.chamber = get_random_chamber_sequence()
    
    def is_match_over(self):
        return self.current_round > rounds_per_match
    
    def give_both_random_health(self):
        health = get_random_health()
        
        self.player.set_health(health)
        self.dealer.set_health(health)
    
    # get the provided bullet's damage accounting for current game state
    def get_bullet_current_damage(self, bullet):
        if bullet_is_blank(bullet):
            return 0
        elif self.is_sawed_off:
            return sawedoff_live_damage
        else:
            return base_live_damage
    
    def swap_turn(self):
        if self.is_player(self.whose_turn_id):
            self.whose_turn_id = self.dealer_id
        else:
            self.whose_turn_id = self.player_id
    
    # returns a tuple, with the first item being the participant taking the turn, and the second being the one not
    def whose_turn(self):
        if self.is_player(self.whose_turn_id):
            return self.player, self.dealer
        else:
            return self.dealer, self.player
    
    def is_player_turn(self):
        return self.is_player(self.whose_turn_id)
    
    # check if the participant is handcuffed.  optionally uncuffs the participant if applicable.
    # note that this function will still return true even if the participant is uncuffed.  this is intended to be used such that the participant gets a turn afterward (where applicable)
    def is_handcuffed(self, participant, uncuff=False):
        is_cuffed = self.get_id(participant) == self.who_handcuffed_id
        
        if is_cuffed and uncuff:
            self.who_handcuffed_id = self.nobody_id
        
        return is_cuffed
    
    # whomever has this turn uses the named item, or throws an exception if that item isn't in the participant's inventory.
    def use_item(self, item_name):
        user, opposite = self.whose_turn()
        
        if user.has_item(item_name):
            # use item
            self.get_item_behavior(item_name)(user, opposite)
        else:
            raise Exception(item_name + " isn't in " + user.name + "'s inventory.")
    
    # whomever has this turn fires the gun.  because shooting the gun tends to be the last action before switching turns, sets, etc., this also handles most of the state transition logic
    def shoot(self, shooting_self):
        bullet = self.pop_next_bullet()
        damage = self.get_bullet_current_damage(bullet)
        
        shooter, opposite = self.whose_turn()
        
        if not shooting_self:
            print(shooter.name + " shot " + opposite.name)
            
            opposite.take_damage(damage)
            
            if not self.is_handcuffed(opposite, uncuff=True):
                self.swap_turn()
        else:
            print(shooter.name + " shot themselves")
            
            shooter.take_damage(damage)
            
            if bullet_is_live(bullet):
                # this is nested so that the uncuff only happens if the shell is live.  if the shell is blank then the shooter gets the next turn anyways without checking the cuffs
                if not self.is_handcuffed(opposite, uncuff=True):
                    self.swap_turn()
        
        # reset game state as needed
        
        # always resets
        self.is_sawed_off = False
        
        # check game end conditions
        if self.player.is_dead():
            # game over, quit logic
            self.game_over = True
            return
        elif self.dealer.is_dead():
            # advance to next round
            self.current_round += 1
            
            if self.is_match_over():
                self.matches_won += 1
                
                self.current_round = 1
            else:
                # NOTE: this is intended behavior. the items don't reset between the third round of a match and the first round of the following match in the game
                self.player.reset_items()
                self.dealer.reset_items()
            
            self.give_both_random_health()
            self.empty_chamber()
        
        # is this set over?
        if self.chamber_is_empty():
            # reload
            self.load_chamber()
            
            # player always gets first turn
            self.whose_turn_id = self.player_id
            
            # give each items
    
    # if it's the dealer's turn, run the dealer ai until the dealer finishes his turn.
    def dealer_ai_turn(self):
        if not self.is_player_turn():
            self.dealer.take_turn(self)
        
    def is_over(self):
        return self.game_over
    
    def get_item_behavior(self, item_name):
        return self.item_behaviors[item_name]
    
    # TODO: the rules for this are actually rather specific.  for now, they've been made a lot simpler
    def get_random_item_sequence(self):
        min_items = 2
        max_items = 6
        
        item_counts = dict()

def main(argc, argv):
    run = BuckshotRun()
    
    while not run.is_over():
        print(run.chamber)
        print("round " + str(run.current_round))
        print("player has won: " + str(run.matches_won) + " matches")
        print("player health: " + str(run.player.health))
        print("dealer health: " + str(run.dealer.health))
        
        if run.is_player_turn():
            print("taking player turn")
            run.shoot(bullet_is_blank(run.peek_next_bullet()))
            # run.shoot(bool(random.randint(0, 1)))
        else:
            print("taking dealer turn")
            run.dealer_ai_turn()
        
        input("enter to continue...")
        print("")
    
    print("Game over!")

if __name__ == "__main__":
    main(len(sys.argv), sys.argv)