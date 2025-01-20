import sys
import random

import buckshot
from buckshot import BuckshotRun, RoundResetException

import torch

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

num_total_items = len(buckshot.all_item_names)

# runs before the softmax layer to set any items that the predictor doesn't have to zero in the softmax layer
# this just sets the output of that layer to a very large negative number
class ZeroOutBadItems(torch.nn.Module):
    zero_value = -999
    
    def __init__(self, is_dealer):
        super().__init__()
        
        self.is_dealer = is_dealer
        self.run = None
        self.inventory = None
    
    def set_run(self, run):
        self.run = run
        self.inventory = run.dealer.inventory if self.is_dealer else run.player.inventory
        self.non_zeroed_count_last = 0
    
    def forward(self, item_raw):
        out = item_raw
        
        # disallow certain items under certain conditions
        do_adrenaline = self.is_dealer # can never steal adrenaline from dealer's inventory
        do_handcuffs = self.run.is_handcuffed(self.run.dealer) # can't handcuff twice
        do_handsaw = self.run.is_sawed_off # can't saw twice
        
        non_zeroed_count = len(item_raw)
        
        # disallow use adrenaline for player if dealer inventory is empty
        if not self.is_dealer:
            if self.run.dealer.inventory.num_items() < 1:
                do_adrenaline = True
        
        for i, item_name in enumerate(buckshot.all_item_names):
            if not self.inventory.has_item(item_name) or (do_adrenaline and item_name == "adrenaline") or (do_handcuffs and item_name == "handcuffs") or (do_handsaw and item_name == "handsaw"):
                out[i] = self.zero_value
                non_zeroed_count -= 1
        
        self.non_zeroed_count_last = non_zeroed_count
        
        return out

class BuckshotPredictor_CrossEntropy():
    live_int = 1
    blank_int = -1
    dont_know_int = 0
    
    def __init__(self):
        # 2 numbers for num live and num blank
        # 2 numbers for health (player and dealer)
        # 9*2 numbers for player and dealer item amounts
        # 8 numbers for known sequence
        self.input_size = 2 + 2 + num_total_items*2 + buckshot.max_shells_per_set
        
        self.feature_size = 16
        
        self.core_model = torch.nn.Sequential(
            torch.nn.Linear(self.input_size, self.feature_size)
        ).to(device)
        
        # first number = % confidence in using an item
        # second number = % confidence in shooting dealer (if not using an item)
        self.who_to_shoot_or_use_item = torch.nn.Sequential(
            torch.nn.Linear(self.feature_size, 2),
            torch.nn.Sigmoid()
        ).to(device)
        
        self.zero_out_bad_items_player = ZeroOutBadItems(is_dealer=False)
        self.zero_out_bad_items_dealer = ZeroOutBadItems(is_dealer=True)
        
        # each number = % confidence in picking that item
        self.which_item_to_use = torch.nn.Sequential(
            torch.nn.Linear(self.feature_size, num_total_items),
            
            self.zero_out_bad_items_player,
            torch.nn.Softmax(dim=0)
        ).to(device)
        
        self.which_item_to_steal = torch.nn.Sequential(
            torch.nn.Linear(self.feature_size, num_total_items),
            
            self.zero_out_bad_items_dealer,
            torch.nn.Softmax(dim=0)
        ).to(device)
    
    def set_run(self, run):
        self.run = run
        
        self.zero_out_bad_items_player.set_run(run)
        self.zero_out_bad_items_dealer.set_run(run)
    
    def weighted_coin_flip(self, success_weight):
        return random.random() < success_weight
    
    def weighted_decision(self, weights):
        return random.choices(range(len(weights)), weights)[0]
    
    def pretty_print_item_confidences(self, confidences): 
        for item_name, confidence in zip(buckshot.all_item_names, confidences):
            print(item_name.rjust(10, " ") + ":" + "{:.2%}".format(confidence.item()).rjust(8, " "))
            # print("{}: {:.2%}".format(item_name, confidence.item()).rjust(20, " "))
        
    # makes a decision from the pure game state it cares about.  not a very pretty signature
    # item_counts should be an ordered list of numbers, order depending on the order of all_item_names (inventory.as_dict().values() should do it)
    # known sequence is the known sequence of the player, not the dealer.
    # this doesn't take a complete turn; any "decision" is just something that changes the game state.
    def make_decision_from_game_state(self, num_live, num_blank, player_health, dealer_health, player_item_counts, dealer_item_counts, known_sequence, logging=False):
        # format input to list of integers
        input_list = [num_live, num_blank, player_health, dealer_health]
        
        if len(player_item_counts) != num_total_items:
            raise Exception("bad number of item counts for player: " + str(len(player_item_counts)) + " (should be " + str(num_total_items) + ")")
        
        if len(dealer_item_counts) != num_total_items:
            raise Exception("bad number of item counts for dealer: " + str(len(player_item_counts)) + " (should be " + str(num_total_items) + ")")
        
        input_list += player_item_counts
        input_list += dealer_item_counts
        
        known_sequence_as_ints = []
        
        for shell in known_sequence:
            if buckshot.shell_is_live(shell):
                known_sequence_as_ints.append(self.live_int)
            elif buckshot.shell_is_blank(shell):
                known_sequence_as_ints.append(self.blank_int)
            else:
                known_sequence_as_ints.append(self.dont_know_int)
        
        # extend to 8
        known_sequence_as_ints = known_sequence_as_ints + [self.dont_know_int] * (buckshot.max_shells_per_set - len(known_sequence_as_ints))
        
        input_list += known_sequence_as_ints
        
        # create tensor
        input_tensor = torch.tensor(input_list).float().to(device)
        
        # decision time!
        
        # get core features
        features = self.core_model(input_tensor)
        
        use_item_confidence, shoot_dealer_confidence = self.who_to_shoot_or_use_item(features)
        
        if self.zero_out_bad_items_player.non_zeroed_count_last == 0:
            # force player to not use an item
            use_item = False
        else:
            use_item = self.weighted_coin_flip(use_item_confidence)
        
        if logging:
            print("{:.2f}% sure about using an item".format(use_item_confidence.item() * 100))
            print("{:.2f}% sure about shooting the dealer".format(shoot_dealer_confidence.item() * 100))
            print("")
        
        if use_item:
            # figure out which item to use
            item_confidences = self.which_item_to_use(features)
            
            item_index = self.weighted_decision(item_confidences)
            
            if logging:
                print("item confidences:")
                self.pretty_print_item_confidences(item_confidences)
                print("")
            
            item_name = buckshot.all_item_names[item_index]
            
            if item_name == "adrenaline":
                # also choose which item to steal
                steal_item_confidences = self.which_item_to_steal(features)
                
                if logging:
                    print("steal item confidences:")
                    self.pretty_print_item_confidences(steal_item_confidences)
                    print("")
            
                steal_item_index = self.weighted_decision(steal_item_confidences)
                
                steal_item_name = buckshot.all_item_names[steal_item_index]
                
                return "use", item_name, steal_item_name
            else:
                return "use", item_name
        else:
            shoot_dealer = self.weighted_coin_flip(shoot_dealer_confidence)
            
            if shoot_dealer:
                return "shoot", "dealer"
            else:
                return "shoot", "self"
    
    def take_turn(self, logging=False):
        while True:
            # prompt for decision
            decision = self.make_decision_from_game_state(
                self.run.num_live(),
                self.run.num_blank(),
                self.run.player.health,
                self.run.dealer.health,
                self.run.player.inventory.as_dict().values(),
                self.run.dealer.inventory.as_dict().values(),
                self.run.player.known_sequence,
                logging=logging
            )
            
            action = decision[0]
            
            if action == "use":
                item = decision[1]
                
                try:
                    if item == "adrenaline":
                        steal_item = decision[2]
                        
                        self.run.use_adrenaline(steal_item)
                    else:
                        self.run.use_item(item)
                except RoundResetException as e:
                    # turn ends early
                    break
            elif action == "shoot":
                who = decision[1]
                
                shooting_self = who == "self"
                self.run.shoot(shooting_self=shooting_self)
                
                # done with turn
                break

import datetime

def main(argc, argv):
    ai_player = BuckshotPredictor_CrossEntropy()
    
    total_rounds_won = 0
    total_sets_survived = 0
    
    most_rounds_won = 0
    most_sets_survived = 0
    
    total_games = 1000
    
    logging=False
    
    start = datetime.datetime.now()
    
    for i in range(total_games):
        run = BuckshotRun(logging=logging)
        ai_player.set_run(run)
        
        while not run.is_over():
            if run.is_player_turn():
                ai_player.take_turn(logging=logging)
            else:
                try:
                    run.dealer_ai_turn()
                except RoundResetException:
                    pass
        
        total_rounds_won += run.rounds_won()
        total_sets_survived += run.sets_won
        
        most_rounds_won = max(run.rounds_won(), most_rounds_won)
        most_sets_survived = max(run.sets_won, most_sets_survived)
        # print("ai won " + str(run.rounds_won()) + " rounds and survived " + str(run.sets_won) + " sets")
    
    end = datetime.datetime.now()
    
    millis_elapsed = (end - start).total_seconds() * 1000
    millis_per_game = millis_elapsed / total_games
    millis_per_round = millis_elapsed / (total_games + total_rounds_won)
    
    print("ai performance out of " + str(total_games) + " games:")
    print("total rounds won: " + str(total_rounds_won))
    print("most rounds won: " + str(most_rounds_won))
    print("total sets survived: " + str(total_sets_survived))
    print("most sets survived: " + str(most_sets_survived))
    print("")
    
    print("total time: {:.2f}ms".format(millis_elapsed))
    print("ms/game: {:.2f}ms".format(millis_per_game))
    print("ms/round: {:.2f}ms".format(millis_per_round))
    
    return

if __name__ == "__main__":
    main(len(sys.argv), sys.argv)