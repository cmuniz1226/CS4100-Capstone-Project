import random
from pypokerengine.api import game
from pypokerengine.api.emulator import Emulator
from pypokerengine.engine.card import Card
from pypokerengine.players import BasePokerPlayer
from .emulator_player import EmulatorPlayer, MyModel
from pypokerengine.engine.poker_constants import PokerConstants as Const
from pypokerengine.engine.hand_evaluator import HandEvaluator
import math

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
  
    def declare_action(self, valid_actions, hole_card, round_state):      
        # Agent chooses action based on heuristic.
        if self.heuristic is not None:
            self.action = self.heuristic(hole_card, round_state)

        # Make sure agent does not ever go all in.
        if self.action == self.MAX_RAISE:
            adjusted_maximum = valid_actions[2]['amount']['max'] / 2
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
        return MCTSPlayerModel.MAX_RAISE
    elif has_pair:
        return MCTSPlayerModel.MAX_RAISE
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

    if h_val > 150000:
        return MCTSPlayerModel.MAX_RAISE
    elif h_val <= 150000 and h_val > 80000:
        return MCTSPlayerModel.MIN_RAISE
    elif h_val <= 80000 and h_val > 25000:
        return MCTSPlayerModel.CALL
    else:
        return MCTSPlayerModel.FOLD


def random_action(hole_card, round_state):
    return random.choice(ACTIONS)


class MCTSPlayer(EmulatorPlayer):

    def __init__(self, number_of_playouts, heuristic_func):
        super().__init__()
        self.number_of_playouts = number_of_playouts
        self.heuristic_func = heuristic_func

    def declare_action(self, valid_actions, hole_card, round_state):
        # The below code is running the MCTS algorithm.
        actions_and_results = {action: 0 for action in ACTIONS}
        for action in actions_and_results:
            self.my_model.set_action(action)
            emulator_game_state = self._setup_game_state(round_state, hole_card)
            next_game_state, _ = self.emulator.apply_action(emulator_game_state,
                                                            *self.my_model.declare_action(valid_actions, hole_card,
                                                                                          round_state))
            mcts_root = MCTSNode(self.emulator, next_game_state, self.uuid, hole_card, self.out_stack,
                                 simulation_model=self.player_model,
                                 declare_action_args=[valid_actions, hole_card, round_state])

            for _ in range(self.number_of_playouts):
                leaf_node = mcts_root.select_leaf()
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
                player_model.set_heuristic(self.heuristic_func)
                self.player_model = player_model
            self.emulator.register_player(uuid, player_model)

    def receive_round_start_message(self, round_count, hole_card, seats):
        # Save initial stack for use by the MCTS algorithm to determine profit upon terminal state(s)
        # for our agent.
        self.out_stack = [player for player in seats if player['uuid'] == self.uuid][0]['stack']


class MCTSNode:

    def __init__(self, emulator, current_game_state, uuid, hole_card, initial_stack, simulation_model=None, declare_action_args=None, parent=None):
        self.emulator = emulator
        self.game_state = current_game_state
        self.uuid = uuid
        self.hole_card = hole_card
        if simulation_model is None:
            self.simulation_model = MCTSPlayerModel(uuid)
        else:
            self.simulation_model = simulation_model
        self.expansion_model = MyModel()
        self.declare_action_args = declare_action_args
        self.parent = parent
        self.initial_stack = initial_stack
        self.children = []
        self.num_playouts = 0
        self.propagated_state_value = 0

    def generate_children(self):
        """
        Based on the actions available based on the current state of the game, generate child nodes to
        this node and append them to self.children.

        SIDE EFFECT: Mutates self.children. 
        """
        for a in ACTIONS:
            self.expansion_model.set_action(a)
            real_action, amount = self.expansion_model.declare_action(*self.declare_action_args)
            # print(real_action, amount)
            new_state, events = self.emulator.apply_action(self.game_state, real_action, bet_amount=amount)
            if is_terminal_state(new_state, self.uuid):
                # print("GENERATED TERMINAL STATE")
                self.children.append(MCTSNode(self.emulator, new_state, self.uuid, self.hole_card, self.initial_stack,
                                              simulation_model=self.simulation_model, parent=self))
            else:
                new_args = [events[-1]["valid_actions"], self.hole_card, events[-1]["round_state"]]
                self.children.append(MCTSNode(self.emulator, new_state, self.uuid, self.hole_card, self.initial_stack,
                                              simulation_model=self.simulation_model, declare_action_args=new_args,
                                              parent=self))
            
    def select_leaf(self):
        """
        Select a leaf node based on the number of the node's children (should be zero). Selects the child with the maximum 
        UCB1 value at each child iteration.
        """
        leaf = self
        while len(leaf.children) != 0:
            leaf = leaf._get_max_child()
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
            round_end_state, _ = self.emulator.run_until_round_finish(next_node.game_state)
            next_node.num_playouts += 1
            next_node.propagated_state_value = compute_state_value(round_end_state, self.uuid, self.initial_stack)
            next_node.back_propagation()

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

    def back_propagation(self):
        """
        Recursively propagates state value information back up the tree. This is called after rollout/playout simulation 
        is completed. Backpropagation ends when we hit the root node.
        """
        # don't compute these values for terminal state; terminal state has no children so the values would be set to 0
        if self.is_decision_node():
            child_values = [child.propagated_state_value for child in self.children]
            self.propagated_state_value = max(child_values) if len(child_values) > 0 else self.propagated_state_value
        else:
            expected_val = 0
            for child in self.children:
                expected_val += (child.propagated_state_value * child.num_playouts) / self.num_playouts
            self.propagated_state_value = expected_val
            
        if self.parent is not None:
            self.parent.num_playouts += 1
            self.parent.back_propagation()


    def get_node_value(self):
        """
        Get the value caclulated for this node from its playouts and children.
        """
        return self.propagated_state_value

    def is_decision_node(self):
        """
        Determines if this MCTSNode is a DecisionNode, aka determines if this node
        contains a game state/round state in which it is our agent's turn.
        """
        active_player_index = self.game_state['next_player']
        
        if str(active_player_index) == "not_found":
            return False
        return self.game_state['table'].seats.players[active_player_index].uuid == self.uuid


def compute_state_value(game_state, player_uuid, initial_stack):
        """
        Given the a game-state (round state), a player uuid, and the player's initial stack, computes and returns its value relative
        to how much money an agent has lost/gained. If the current state is not terminal, return zero.
        """
        if game_state["street"] == Const.Street.FINISHED:
            final_stack = get_player_stack(game_state, player_uuid)
            profit = final_stack - initial_stack
            return profit
        else:
            return 0


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
    return game_finished


def get_player_stack(game_state, uuid):
    """
    Given a Poker game state and a player's uuid, return the value of their stack
    (how many chips they have).
    """
    if 'table' in list(game_state.keys()):
        return [player for player in game_state['table'].seats.players if player.uuid == uuid][0].stack
    else:
        return [player for player in game_state['seats'] if player['uuid'] == uuid][0]['stack']
     



# Math utility functions.
     
def combination(n, r):
    """
    Calculates the combination formula given n and r.
    """
    return (math.factorial(n)) / ((math.factorial(r)) * math.factorial(n - r))