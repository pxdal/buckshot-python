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

max_items_total = 8

min_items_per_set = 2
max_items_per_set = 5

base_live_damage = 1
sawedoff_live_damage = 2

## item behaviors ##
# all item behaviors require a user and the opposite player.
# some items require additional input from the user.  not sure what to do about that yet.

def knife_behavior(run, user, opposite):
    run.is_sawed_off = True

def cigs_behavior(run, user, opposite):
    user.give_health(1)

def medicine_behavior(run, user, opposite):
    coin_flip = random.randint(0, 1) == 0
    
    if coin_flip:
        user.give_health(2)
    else:
        user.take_damage(1)

def magnifier_behavior(run, user, opposite):
    user.known_sequence[0] = run.peek_next_bullet()

def inverter_behavior(run, user, opposite):
    run.invert_next_bullet()

def phone_behavior(run, user, opposite):
    num_bullets_left = run.num_bullets_left()
    
    if num_bullets_left < 2:
        # cell phone says "how unfortunate..." for less than two rounds
        return
    
    # pick a random bullet
    reveal_pos = random.randint(1, num_bullets_left-1)
    
    user.known_sequence[reveal_pos] = run.chamber[reveal_pos]

def beer_behavior(run, user, opposite):
    run.pop_next_bullet()
    
    # run cleanup if chamber is empty
    if run.chamber_is_empty():
        run.on_set_end()
        
        # basically just indicate that the turn is over now
        raise RoundResetException()

def handcuffs_behavior(run, user, opposite):
    # can't handcuff twice
    if run.is_handcuffed(opposite):
        raise InvalidItemException("can't handcuff twice")
    
    run.handcuff_participant(opposite)
    
def adrenaline_behavior(run, user, opposite):
    # steal item stored in run    
    steal_item = run.desired_steal_item
    
    # steal item from opposite
    try:
        opposite.inventory.use(steal_item)
    except NoItemException as e:
        raise NoItemException("opposite player doesn't have " + steal_item)
    
    # give item to user
    user.inventory.add_item(steal_item)
    
    # use item immediately
    run.use_item(steal_item)
    
    # reset steal item
    run.desired_steal_item = None    
    
# item settings #
all_item_behaviors = {
    "knife": knife_behavior,
    "cigs": cigs_behavior,
    "medicine": medicine_behavior,
    "magnifier": magnifier_behavior,
    "inverter": inverter_behavior,
    "phone": phone_behavior,
    "beer": beer_behavior,
    "adrenaline": adrenaline_behavior,
    "handcuffs": handcuffs_behavior
}

all_item_names = list(all_item_behaviors.keys())


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

# just wrapper classes for exception to give these special names

# item isn't available
class NoItemException(Exception):
    pass

# bad item name/usage
class InvalidItemException(Exception):
    pass

# round is getting reset
class RoundResetException(Exception):
    pass

# player inventory
class Inventory():
    # TODO: how the game determines what items you get is not as simple as just uniform randomness.
    # generate an inventory of num random items.
    # FUTURE BEHAVIOR: limits is also an inventory of items.  it gives limits to the number of items that can be in the random inventory.  if limits is None, then no limits are applied.
    @staticmethod
    def get_random_items(num, limits=None):
        random_inventory = Inventory()
        
        for i in range(num):
            # pick random item
            random_item = random.choice(all_item_names)
            
            random_inventory.add_item(random_item)
        
        return random_inventory
    
    def __init__(self, max_items=None):
        self.inventory = dict()
        self.max_items = max_items
        
        # initialize counts
        self.reset()
    
    def __contains__(self, item_name):
        if not item_name in all_item_names:
            raise InvalidItemException("Invalid item " + item_name)
        
        return self.inventory[item_name] > 0
    
    def __str__(self):
        return str(self.inventory)
    
    def __len__(self):
        return sum(self.inventory.values())
    
    def reset(self):
        self.inventory = dict()
        
        for item_name in all_item_names:
            self.inventory[item_name] = 0
        
    def num_items(self):
        return len(self)
        
    def as_dict(self):
        return self.inventory
    
    def item_count(self, item_name):
        if not item_name in all_item_names:
            raise InvalidItemException("Invalid item " + item_name)
        
        return self.inventory[item_name]
    
    def add_item(self, item_name, count=1):
        if not item_name in all_item_names:
            raise InvalidItemException("Invalid item " + item_name)
        
        if self.max_items != None and self.num_items()+count >= self.max_items:
            count = self.max_items - self.num_items()
            
            if count == 0:
                # TODO: more than silent fail?
                return
            
        self.inventory[item_name] += count
        
    def add_inventory(self, inventory):
        for item_name in inventory.as_dict().keys():
            self.add_item(item_name, count=inventory.item_count(item_name))
        
    def use(self, item_name):
        if not item_name in self:
            raise NoItemException(item_name + " is not in inventory")
        
        self.inventory[item_name] -= 1

# a participant in the game.  there are only two, the dealer and the player, but both inherit from this for shared behavior (such as health, items, etc.)
class Participant():
    def __init__(self, name):
        self.name = name
        self.health = 0
        self.inventory = Inventory(max_items_total)
        
        # sequence containing rounds that the participant knows through any items that reveal shells.
        # note that this doesn't include any shells that may be implicitly known, as in through shell counting or otherwise
        # known shells will be either the live or blank token, or None if the shell isn't known.
        # this represents the number of shells left in the chamber, not the number of shells at the start.  the first item always corresponds to the next shell
        self.known_sequence = []
        
        self.current_max_health = 0
    
    def reset_known_sequence(self, num_shells):
        self.known_sequence = [None] * num_shells
    
    def pop_known_sequence(self):
        return self.known_sequence.pop(0)
    
    def peek_known_sequence(self, i):
        return self.known_sequence[i]
    
    def set_health(self, new_health):
        self.health = new_health
        self.current_max_health = new_health
        
    def take_damage(self, damage):
        self.health -= damage
    
    def give_health(self, health):
        self.health = min(self.health + health, self.current_max_health)
        
    def is_dead(self):
        return self.health < 1
    
    def give_items(self, inventory_of_items):
        self.inventory.add_inventory(inventory_of_items)
    
    def reset_items(self):
        self.inventory.reset()
        
    def has_item(self, name):
        return name in self.inventory
    
    def use_item(self, name):
        self.inventory.use(name)

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
        
        # the polarity of the last shell fired (including if it was inverted) or None if none have been fired yet
        self.last_shell_fired = None
        
        # the desired item to steal from opposite of whomever is using adrenaline
        self.desired_steal_item = None
        
        # initialize game
        self.on_set_end()
    
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
    
    def num_live(self):
        return self.chamber.count(live_token)
    
    def num_blank(self):
        return self.chamber.count(blank_token)
    
    def num_bullets_left(self):
        return len(self.chamber)
    
    # returns the next bullet without removing it from the chamber
    def peek_next_bullet(self):
        return self.chamber[0]
    
    # pops the bullet from the front and returns it
    def pop_next_bullet(self):
        self.player.pop_known_sequence()
        self.dealer.pop_known_sequence()
        
        return self.chamber.pop(0)
    
    def invert_next_bullet(self):
        if self.chamber[0] == live_token:
            self.chamber[0] = blank_token
        else:
            self.chamber[0] = live_token
        
    def chamber_is_empty(self):
        return len(self.chamber) == 0
    
    def empty_chamber(self):
        self.chamber = []
    
    def load_chamber(self):
        self.chamber = get_random_chamber_sequence()
    
    def get_last_shell_fired(self):
        return self.last_shell_fired
    
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
    
    def handcuff_participant(self, participant):
        self.who_handcuffed_id = self.get_id(participant)
    
    # check if the participant is handcuffed.  optionally uncuffs the participant if applicable.
    # note that this function will still return true even if the participant is uncuffed.  this is intended to be used such that the participant gets a turn afterward (where applicable)
    def is_handcuffed(self, participant, uncuff=False):
        is_cuffed = self.get_id(participant) == self.who_handcuffed_id
        
        if is_cuffed and uncuff:
            self.who_handcuffed_id = self.nobody_id
        
        return is_cuffed
    
    # whomever has this turn uses the named item, or throws an exception if that item isn't in the participant's inventory.
    def use_item(self, item_name):
        if item_name == "adrenaline" and self.desired_steal_item is None:
            raise InvalidItemException("adrenaline was used but no steal item was set (are you using use_item instead of use_adrenaline)?")
        
        user, opposite = self.whose_turn()
        
        if user.has_item(item_name):
            # use item
            user.use_item(item_name)
            self.call_item_behavior(item_name, user, opposite)
        else:
            raise NoItemException(item_name + " isn't in " + user.name + "'s inventory.")
    
    # whomever has this turn uses their adrenaline to steal the provided item from the opposite participant and use it immediately.
    def use_adrenaline(self, steal_item_name):
        # can't steal more adrenaline
        if steal_item_name == "adrenaline":
            raise InvalidItemException("you can't use adrenaline to take adrenaline")
        
        # set steal item
        self.desired_steal_item = steal_item_name
        
        self.use_item("adrenaline")
        
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
            self.on_round_end()
        
        # is this set over?
        if self.chamber_is_empty():
            self.on_set_end()
        
        self.last_shell_fired = bullet
        
        # return fired shell
        return bullet
    
    def on_set_end(self):
        # reset game state as needed
        
        # NOTE: we do this because we don't necessarily know that this was called after a shell was fired
        self.is_sawed_off = False
        
        # reload
        self.load_chamber()
        
        # participants don't know new sequence
        self.player.reset_known_sequence(len(self.chamber))
        self.dealer.reset_known_sequence(len(self.chamber))
        
        # player always gets first turn
        self.whose_turn_id = self.player_id
        
        # give each items
        num_items = random.randint(min_items_per_set, max_items_per_set)
        
        player_items = Inventory.get_random_items(num_items)
        dealer_items = Inventory.get_random_items(num_items)
        
        self.player.give_items(player_items)
        self.dealer.give_items(dealer_items)
        
    def on_round_end(self):
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
        
    # if it's the dealer's turn, run the dealer ai until the dealer finishes his turn.
    def dealer_ai_turn(self):
        if not self.is_player_turn():
            self.dealer.take_turn(self)
        
    def is_over(self):
        return self.game_over
    
    def call_item_behavior(self, item_name, user, opposite):
        return all_item_behaviors[item_name](self, user, opposite)

# simple wrapper around single run.  mostly for debugging, not really intended to be fun gameplay.
def main(argc, argv):
    def get_user_input(prompt):
        return input(prompt + ": ").strip().lower()
    
    run = BuckshotRun()
    
    while not run.is_over():
        # print(run.chamber)
        print("round " + str(run.current_round))
        print("player has won: " + str(run.matches_won) + " matches")
        print("")
        
        print("player health: " + str(run.player.health))
        print("dealer health: " + str(run.dealer.health))
        print("")
        
        print("player items: " + str(run.player.inventory))
        print("dealer items: " + str(run.dealer.inventory))
        print("")
        
        print("num live: " + str(run.num_live()))
        print("num blank: " + str(run.num_blank()))
        print("known sequence: "  + str(run.player.known_sequence))
        print("")
        
        if run.is_player_turn():
            dont_shoot = False
            
            while True:
                use_item = get_user_input("use an item?  enter name or press enter for no")
                
                if use_item == "":
                    break
                
                try:
                    used_adrenaline = False
                    
                    if use_item == "adrenaline":
                        # run special adrenaline behavior
                        use_item = get_user_input("what are you stealing?")
                        
                        run.use_adrenaline(use_item)
                        
                        used_adrenaline = True
                        
                        print("used adrenaline to steal " + use_item)
                    else:
                        run.use_item(use_item)
                        
                        print("used " + use_item)
                    
                    if use_item == "cigs" or use_item == "medicine":
                        print("player health: " + str(run.player.health))
                    elif use_item == "magnifier" or use_item == "phone" or use_item == "beer":
                        if use_item == "beer":
                            print("num live: " + str(run.num_live()))
                            print("num blank: " + str(run.num_blank()))
                        
                        print("known sequence: "  + str(run.player.known_sequence))
                    
                    print("player items: " + str(run.player.inventory))
                    
                    if used_adrenaline:
                        print("dealer items: " + str(run.dealer.inventory))
                except NoItemException as e:
                    print(e)
                except InvalidItemException as e:
                    print(e)
                except RoundResetException as e:
                    # skip item usage and gunshot
                    dont_shoot = True
                    break

            while not dont_shoot:
                who_to_shoot = get_user_input("who to shoot?  type \"dealer\" or \"self\"")
                
                if who_to_shoot == "dealer":
                    fired = run.shoot(shooting_self=False)
                    break
                elif who_to_shoot == "self":
                    fired = run.shoot(shooting_self=True)
                    break
                else:
                    print("pick!")
            
            # print("taking player turn")
            # run.shoot(bullet_is_blank(run.peek_next_bullet()))
            # run.shoot(bool(random.randint(0, 1)))
        else:
            print("taking dealer turn")
            run.dealer_ai_turn()
        
        fired = run.get_last_shell_fired()
        
        if not dont_shoot:
            if bullet_is_live(fired):
                print("shell was live")
            else:
                print("shell was blank")
        
        input("enter to continue...")
        print("\n")
    
    print("Game over!")

if __name__ == "__main__":
    main(len(sys.argv), sys.argv)