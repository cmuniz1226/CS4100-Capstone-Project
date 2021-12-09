import random
from pypokerengine.api import game
from pypokerengine.api.emulator import Emulator
from pypokerengine.engine.card import Card
from pypokerengine.players import BasePokerPlayer
from .emulator_player import EmulatorPlayer, MyModel
from pypokerengine.engine.poker_constants import PokerConstants as Const
from pypokerengine.engine.hand_evaluator import HandEvaluator
import math
import time

ACTIONS = [MyModel.FOLD, MyModel.CALL, MyModel.MIN_RAISE, MyModel.MAX_RAISE]

BAD_HAND_NUMBER = 4000

STR_TO_STREET = {
    'preflop': Const.Street.PREFLOP,
    'flop': Const.Street.FLOP,
    'turn': Const.Street.TURN,
    'river': Const.Street.RIVER,
    'showdown': Const.Street.SHOWDOWN,
    'finished': Const.Street.FINISHED
}

UCB1_EXPLORATION_CONSTANT = math.sqrt(2)

class MCTSPlayerModel(MyModel):
    def __init__(self, uuid):
        super().__init__()
        self.uuid = uuid
        self.heuristic = None

    def set_heuristic(self, heuristic):
        self.heuristic = heuristic

    """
    Decides actions based on our
    """    
    def declare_action(self, valid_actions, hole_card, round_state):      
        # Agent chooses action based on heuristic.
        if self.heuristic is not None:
            self.action = self.heuristic(hole_card, round_state)

        # Make sure agent does not ever go all in.
        if self.action == self.MAX_RAISE:
            adjusted_maximum = valid_actions[2]['amount']['max'] / 10
            adjusted_maximum = int(adjusted_maximum)
            return valid_actions[2]['action'], adjusted_maximum
        
        action, amount = super().declare_action(valid_actions, hole_card, round_state)
        return action, amount


def nyu_heuristic_function(hole_card, round_state):
    """
    Given the hole card (cards in agent's hand) and the state of a round (including pot and 
    commyunity cards), return an action based on the specified heuristic 
    (http://game.engineering.nyu.edu/wp-content/uploads/2018/05/generating-beginner-heuristics-for-simple-texas-holdem.pdf).
    """
    cards_in_hole = [Card.from_str(card) for card in hole_card]
    cards_on_table = [Card.from_str(card) for card in round_state["community_card"]]
    available_cards = cards_in_hole.extend(cards_on_table)
    
    # Hand Strength Info
    lowest_card_rank = min([card.rank for card in cards_in_hole])
    highest_card_rank = max([card.rank for card in cards_in_hole])
    has_pair = highest_card_rank == lowest_card_rank

    big_blind_amount = 2 * round_state['small_blind_amount']
    pot = round_state['pot']['main']['amount']

    # Betting info    
    big_blinds_in_pot = pot / big_blind_amount

    if lowest_card_rank <= 7 and highest_card_rank <= 11:
        return MCTSPlayerModel.CALL
    elif big_blinds_in_pot <= 2:
        return MCTSPlayerModel.MIN_RAISE
    elif has_pair:
        return MCTSPlayerModel.MIN_RAISE
    # elif big_blinds_in_pot >= 6:
    #     return MCTSPlayerModel.FOLD
    else:
        return MCTSPlayerModel.CALL


def custom_heuristic(hole_card, round_state):
    """
    Given the hole card (cards in agent's hand) and the round state, return a desireable 
    action based on the information provided. This heuristic is based on our idea of what
    we think is a desireable actino to take.
    """
    cards_in_hole = [Card.from_str(card) for card in hole_card]
    cards_on_table = [Card.from_str(card) for card in round_state["community_card"]]
    h_val = HandEvaluator.eval_hand(cards_in_hole, cards_on_table)

    # TODO: Better way to get last bet. 
    # if h_val > 175000: #and valid_actions[MCTSPlayerModel.CALL]['amount'] \
    #     #>= get_player_stack(round_state, self.uuid):
    #     return MCTSPlayerModel.CALL
    if h_val > 150000:
        return MCTSPlayerModel.MAX_RAISE
    elif h_val <= 150000 and h_val > 80000:
        return MCTSPlayerModel.MIN_RAISE
    elif h_val <= 80000 and h_val > 25000:
        return MCTSPlayerModel.CALL
    else:
        return MCTSPlayerModel.FOLD


# def heuristic_function(hole_card, community_card):
#     """
#     Generates a heuristic value based on the agent's hole card and the community cards
#     on the table. This value is used in the MCTSPlayerModel to make decisions based on how
#     well the player is likely to do against its opponents.
#     """
#     hole_cards = [Card.from_str(card) for card in hole_card]
#     comm_cards = [Card.from_str(card) for card in community_card]
#     available_cards = get_available_cards(hole_cards, comm_cards)
#     ev_opponents = expected_value_of_opponents(available_cards, comm_cards)
#     value = HandEvaluator.eval_hand(hole_cards, comm_cards) / ev_opponents
#     return value


# def get_available_cards(hole_card, community_card):
#     """
#     Given the hole cards (agent's hand) and the community cards on the table,
#     determine what cards are still available and return that list.
#     """
#     available_cards = []
#     for suit in Card.SUIT_MAP.keys():
#         for rank in Card.RANK_MAP.keys():
#             possible_card = Card(suit, rank)
#             if possible_card not in hole_card and possible_card not in community_card:
#                 available_cards.append(possible_card)
#     return available_cards


# def expected_value_of_opponents(available_cards, community_card, depth=10):
#     expected_value = 0
#     hand_len = 2
#     total_combinations = combination(len(available_cards), hand_len)
#     for first_card_index in range(min(len(available_cards), depth)):
#         if first_card_index != (len(available_cards) - 1):
#             for second_card_index in range(first_card_index + 1, len(available_cards)):
#                 hole_card = [available_cards[first_card_index], available_cards[second_card_index]]
#                 expected_value += HandEvaluator.eval_hand(hole_card, community_card) / total_combinations
#     return expected_value


class MCTSPlayer(EmulatorPlayer):

    def __init__(self, number_of_playouts):
        super().__init__()
        self.number_of_playouts = number_of_playouts

    def declare_action(self, valid_actions, hole_card, round_state):
        # The below code is running the MCTS algorithm.
        actions_and_results = {action: 0 for action in ACTIONS}
        for action in actions_and_results:
            self.my_model.set_action(action)
            self.player_model.set_action(action)
            emulator_game_state = self._setup_game_state(round_state, hole_card)
            mcts_root = MCTSNode(self.emulator, emulator_game_state, self.uuid, hole_card, model=self.player_model,
                                 declare_action_args=[valid_actions, hole_card, round_state])
            leaf_node = mcts_root
            for _ in range(self.number_of_playouts):
                leaf_node = leaf_node.select_leaf()
                leaf_node.simulate_playout()
            
            actions_and_results[action] = mcts_root.get_node_value()
        print(actions_and_results)
        best_action = max(actions_and_results, key=actions_and_results.get)
        self.my_model.set_action(best_action)
        return self.my_model.declare_action(valid_actions, hole_card, round_state)

    def receive_game_start_message(self, game_info):
        self.my_model = MCTSPlayerModel(self.uuid)
        nb_player = game_info['player_num']
        max_round = game_info['rule']['max_round']
        sb_amount = game_info['rule']['small_blind_amount']
        ante_amount = game_info['rule']['ante']

        self.emulator = Emulator()
        self.emulator.set_game_rule(nb_player, max_round, sb_amount, ante_amount)
        for player_info in game_info['seats']:
            uuid = player_info['uuid']
            player_model = MCTSPlayerModel(self.uuid) if uuid == self.uuid else self.opponents_model
            if uuid == self.uuid:
                self.player_model = player_model
            self.emulator.register_player(uuid, player_model)

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, new_action, round_state):
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        pass


class MCTSNode:
    def __init__(self, emulator, current_game_state, uuid, hole_card, model=None, declare_action_args=None, parent=None):
        self.emulator = emulator
        self.game_state = current_game_state
        self.uuid = uuid
        self.hole_card = hole_card
        if model is None:
            self.model = MCTSPlayerModel(uuid)
        else:
            self.model = model
        self.declare_action_args = declare_action_args
        self.parent = parent
        self.initial_state = current_game_state
        if self.parent is not None:
            self.initial_state = self.parent.initial_state
        self.children = []
        self.num_playouts = 0
        self.propagated_state_value = 0

    def generate_children(self):
        """
        Based on the actions available based on the current state of the game, generate child nodes to
        this node and append them to self.children.

        SIDE EFFECT: Mutates self.children. 
        """
        if self.model.heuristic is not None:
            self.model.set_heuristic(None)
        for a in ACTIONS:
            self.model.set_action(a)
            real_action, amount = self.model.declare_action(*self.declare_action_args)
            new_state, events = self.emulator.apply_action(self.game_state, real_action, amount)
            if is_terminal_state(new_state, self.uuid):
                self.children.append(MCTSNode(self.emulator, new_state, self.uuid, self.hole_card, model=self.model, parent=self))
            else:
                new_args = [events[-1]["valid_actions"], self.hole_card, events[-1]["round_state"]]
                self.children.append(MCTSNode(self.emulator, new_state, self.uuid, self.hole_card, model=self.model, declare_action_args=new_args, parent=self))
            
    def select_leaf(self):
        """
        Select a leaf node based on the number of the node's children (should be zero). Selects the child with the maximum 
        UCB1 value at each child iteration.
        """
        leaf = self
        while len(leaf.children) != 0:
            leaf = self._get_max_child()
        return leaf

    def _get_max_child(self):
        """
        Given the children of a MCTSNode, return the node with the highest UCB1 value.
        """
        bestNode = None
        bestUCBValue = math.inf * -1
        for child_node in self.children:
            childValue = child_node.selection_policy_value()
            if bestUCBValue < childValue:
                bestUCBValue = childValue
                bestNode = child_node
        return bestNode

    def expand(self):
        """
        Generates the next node that does not have any playouts to simulate
        The MCTSNode that this function is called on cannot have any children (must be a leaf node)
        """
        assert len(self.children) == 0, "Node being expanded is not a leaf"

        if self.num_playouts == 0:
            return self
        else:
            self.generate_children()
            return self.children[0]

    def simulate_playout(self):
        """
        Runs simulated playouts of the round by selecting random actions (for both the agent and its opponents)
        until a terminal state is reached (the simulated round is over).
        """
        if not is_terminal_state(self.game_state, self.uuid):
            next_node = self.expand()
            next_node.model.set_heuristic(custom_heuristic)
            round_end_state, _ = self.emulator.run_until_round_finish(next_node.game_state)
            next_node.num_playouts += 1
            next_node.propagated_state_value = next_node.compute_state_value(round_end_state)
            if next_node.parent is not None:
                next_node.back_propagation(next_node.compute_state_value(round_end_state))
        else:
            self.back_propagation(self.compute_state_value(self.game_state))

    def selection_policy_value(self):
        """
        Computes and returns the UCB1 selection policy for this node.
        """
        if self.num_playouts == 0:
            return math.inf

        exploitation_value = self.get_node_value()

        exploration_value = math.sqrt(math.log(self.parent.num_playouts) / self.num_playouts)
        exploration_value *= UCB1_EXPLORATION_CONSTANT

        return exploitation_value + exploration_value

    def back_propagation(self, value_to_propagate):
        """
        Recursively propagates state value information back up the tree. This is called after rollout/playout simulation 
        is completed. Backpropagation ends when we hit the root node.
        """
        # don't compute these values for terminal state; terminal state has no children so the values would be set to 0
        if self.parent is not None:
            self.parent.num_playouts += 1
            self.parent.propagated_state_value += value_to_propagate
            self.parent.back_propagation(value_to_propagate)

    def compute_state_value(self, final_state):
        """
        Given the initial game state, player id, and the final game state, computes and returns its value relative
        to how much money an agent has lost/gained. If the current state is not terminal, return zero.
        """
        if is_terminal_state(final_state, self.uuid):
            initial_stack = get_player_stack(self.initial_state, self.uuid)
            final_stack = get_player_stack(final_state, self.uuid)
            return final_stack - initial_stack
        else:
            return 0

    def get_node_value(self):
        """
        Get the value caclulated for this node from its playouts and children.
        """
        return self.propagated_state_value / self.num_playouts

def is_table_player_active(table, uuid):
    """
    Given the table during a poker game and the uuid of a player,
    return True if the player is still active (hasn't folded), else
    return False.
    """ 
    for player in table.seats.players:
        if player.uuid == uuid:
            return player.is_active()


def is_terminal_state(game_state, uuid):
    """
    Given a game state and a player's uuid, returns True if the player is done 
    for that round. Else, returns False.
    """
    game_finished = game_state["street"] == Const.Street.FINISHED
    player_active = is_table_player_active(game_state["table"], uuid)
    
    return not player_active or game_finished


def get_player_stack(game_state, uuid):
    """
    Given a Poker game state and a player's uuid, return the value of their stack
    (how many chips they have).
    """
    if 'table' in list(game_state.keys()):
        return [player for player in game_state['table'].seats.players if player.uuid == uuid][0].stack
    else:
        return [player for player in game_state['seats'] if player['uuid'] == uuid][0]['stack']
     
    


def combination(n, r):
    """
    Calculates the combination formula given n and r.
    """
    return (math.factorial(n)) / ((math.factorial(r)) * math.factorial(n - r))