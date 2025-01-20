import sys
from buckshot import BuckshotRun

import torch

# runs before the softmax layer to set any items that the predictor doesn't have to zero in the softmax layer
# this just sets the output of that layer to a very large negative number
class ZeroOutBadItems(torch.nn.Module):
    zero_value = -999
    
    def __init__(self, inventory):
        self.inventory = inventory
    
    def forward(self, item_raw):
        out = item_raw
        
        for i, item_name in enumerate(buckshot.all_item_names):
            if not self.inventory.has_item(item_name):
                out[i] = self.zero_value

class BuckshotPredictor():
    def __init__(self):
        # 2 numbers for num live and num blank
        # 2 numbers for health (player and dealer)
        # 9*2 numbers for player and dealer item amounts
        # 8 numbers for known sequence
        self.input_size = 2 + 2 + len(buckshot.all_item_names)*2 + buckshot.max_shells_per_set
        
        self.feature_size = 64
        
        self.core_model = torch.nn.Sequential(
            torch.nn.Linear(input_size, self.feature_size)
        )
        
        # first number = % confidence in using an item
        # second number = % confidence in shooting dealer (if not using an item)
        self.who_to_shoot_or_use_item = torch.nn.Sequential(
            torch.nn.Linear(self.feature_size, 2)
            torch.nn.Sigmoid()
        )
        
        self.which_item_to_use = torch.nn.Sequential(
            
        )

def main(argc, argv):
    run = BuckshotRun()
    
    
    
    return

if __name__ == "__main__":
    main(len(sys.argv), sys.argv)