from .emulator_player import EmulatorPlayer, MyModel
from pypokerengine.engine.poker_constants import PokerConstants as Const
import math

NUM_PLAYOUTS = 1000
ACTIONS = [MyModel.FOLD, MyModel.CALL, MyModel.MIN_RAISE, MyModel.MAX_RAISE]

UCB1_EXPLORATION_CONSTANT = math.sqrt(2)


class MCTSPlayer(EmulatorPlayer):

    def declare_action(self, valid_actions, hole_card, round_state):
        actions_and_results = {action: 0 for action in ACTIONS}
        for action in actions_and_results:
            self.my_model.set_action(action)
            emulator_game_state = self._setup_game_state(round_state, hole_card)
            mcts_root = MCTSNode(self.emulator, emulator_game_state, self.uuid,
                                 declare_action_args=[valid_actions, hole_card, round_state])
            leaf_node = mcts_root
            for _ in range(NUM_PLAYOUTS):
                leaf_node = leaf_node.select_leaf()
                leaf_node.simulate_playout()

            actions_and_results[action] = mcts_root.propagated_state_value

        best_action = max(actions_and_results, key=actions_and_results.get)
        self.my_model.set_action(best_action)
        return self.my_model.declare_action(valid_actions, hole_card, round_state)

    def receive_round_start_message(self, round_count, hole_card, seats):
        pass

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, new_action, round_state):
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        pass


class MCTSNode:
    def __init__(self, emulator, current_game_state, uuid, model=MyModel(), declare_action_args=None, parent=None):
        self.emulator = emulator
        self.game_state = current_game_state
        self.uuid = uuid
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
        if not self._is_terminal_state():
            next_node = self.expand()
            round_end_state, _ = self.emulator.run_until_round_finish(next_node.game_state)
            next_node.num_playouts += 1
            next_node.propagated_state_value = ((next_node.propagated_state_value * (next_node.num_playouts - 1)) +
                                                next_node.compute_state_value(round_end_state)) / next_node.num_playouts
            next_node.back_propogation()
        else:
            self.back_propagation()
        # Nodes generated from simulating actions are not kept in the tree.
        # use this to determine if round is over
        # TODO: Understand application of actions by emulator

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
        # don't compute these values for terminal state; terminal state has no children so the values would be set to 0
        if not self._is_terminal_state():
            self.propagated_state_value = sum([child.propagated_state_value for child in self.children])
            self.num_playouts = sum([child.num_playouts for child in self.children])

        if self.parent is not None:
            self.parent.back_propagation()

    def compute_state_value(self, final_state):
        """
        Given the initial game state, player id, and the final game state, computes and returns its value relative
        to how much money an agent has lost/gained. If the current state is not terminal, return zero.
        """
        if final_state["street"] == Const.Street.FINISHED:
            initial_stack = [player for player in self.initial_state['table'].seats.players if player.uuid == self.uuid][0].stack
            final_stack = [player for player in final_state['table'].seats.players if player.uuid == self.uuid][0].stack
            return final_stack - initial_stack
        else:
            return 0
