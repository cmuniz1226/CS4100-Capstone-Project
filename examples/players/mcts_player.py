from .emulator_player import EmulatorPlayer, MyModel
from pypokerengine.engine.poker_constants import PokerConstants as Const
import random
import math

NUM_PLAYOUTS = 1000
ACTIONS = [MyModel.FOLD, MyModel.CALL, MyModel.MIN_RAISE, MyModel.MAX_RAISE]

UCB1_EXPLORATION_CONSTANT = math.sqrt(2)


class MCTSPlayer(EmulatorPlayer):

    def declare_action(self, valid_actions, hole_card, round_state):
        actions_and_results = {action: 0 for action in ACTIONS}
        for action in actions_and_results:
            self.my_model.set_action(action)
            for _ in range(NUM_PLAYOUTS):
                emulator_game_state = self._setup_game_state(round_state, hole_card)
                mcts_root = MCTSNode(self.emulator, emulator_game_state, declare_action_args=[valid_actions, hole_card, round_state])

    def receive_round_start_message(self, round_count, hole_card, seats):
        pass

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, new_action, round_state):
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        pass


class MCTSNode:
    def __init__(self, emulator, current_game_state, model=MyModel(), declare_action_args=None, parent=None):
        self.emulator = emulator
        self.game_state = current_game_state
        self.model = model
        self.declare_action_args = declare_action_args
        self.parent = parent
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
            self.model.set_action(a)
            real_action, amount = self.model.declare_action(*self.declare_action_args)
            new_state, events = self.emulator.apply_action(self.game_state, real_action, amount)
            new_args = [events[-1]["valid_actions"], events[-1]["hole_card"], events[-1]["round_state"]]
            self.children.append(MCTSNode(self.emulator, new_state, declare_action_args=new_args, parent=self))

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
        Generates 
        """
        if self.num_playouts == 0:
            return self
        else:
            self.generate_children()
            return self.children[0]

    def simulate_playout(self, node):
        """
        Runs simulated playouts of the round by selecting random actions (for both the agent and its opponents)
        until a terminal state is reached (the simulated round is over).
        """
        if not self._is_terminal_state():
            next_node = self.expand()
            round_end_state, _ = self.emulator.run_until_round_finish(next_node.game_state)
            next_node.num_playouts += 1
            
            next_node.back_propogation()
        # Nodes generated from simulating actions are not kept in the tree.
        # use this to determine if round is over
        # TODO: Understand application of actions by emulator
        # TODO: Ensure opponent actions are random.

    def _is_terminal_state(self):
        """
        Determines if this state is a terminal state (street is set to finished). Returns true if so, else false.
        """
        return self.game_state["street"] == Const.Street.FINISHED

    def selection_policy_value(self):
        """
        Computes and returns the UCB1 selection policy for this node.
        """
        exploitation_value = self.propagated_state_value / self.num_playouts

        exploration_value = math.sqrt(math.log(self.parent.num_playouts) / self.num_playouts)
        exploration_value *= UCB1_EXPLORATION_CONSTANT

        return exploitation_value + exploration_value

    def back_propagation(self):
        """
        Recursively propagates state value information back up the tree. This is called after rollout/playout simulation 
        is completed. Backpropagation ends when we hit the root node.
        """
        self.propagated_state_value = sum([child.propagated_state_value for child in self.children])
        self.num_playouts = sum([child.num_playouts for child in self.children])
        if self.parent is not None:
            self.parent.back_propagation()

def compute_state_value(initial_state, game_state):
    """
    Given the initial game state and the current game state, computes and returns its value relative 
    to how much money an agent has lost/gained. If the current state is not terminal, return zero.
    """
    if game_state["street"] == Const.Street.FINISHED:
        # TODO: How to compute difference in stacks before and after the round is over?
        # Use initial_state
        # Get Player
        pass
    else:
        return 0

