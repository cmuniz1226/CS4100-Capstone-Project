from .emulator_player import EmulatorPlayer, MyModel
from pypokerengine.engine.poker_constants import PokerConstants as Const
import random

NUM_PLAYOUTS = 1000
ACTIONS = [MyModel.FOLD, MyModel.CALL, MyModel.MIN_RAISE, MyModel.MAX_RAISE]


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
        self.num_wins = 0
        self._generate_children()

    def _generate_children(self):
        for a in ACTIONS:
            self.model.set_action(a)
            real_action, amount = self.model.declare_action(*self.declare_action_args)
            new_state, events = self.emulator.apply_action(self.game_state, real_action, amount)
            new_args = [events[-1]["valid_actions"], events[-1]["hole_card"], events[-1]["round_state"]]
            self.children.append(MCTSNode(self.emulator, new_state, declare_action_args=new_args, parent=self))

    def select_leaf(self):
        leaf = None
        for child in self.children:
            if child.num_playouts == 0:
                leaf = child
                break

        if leaf is None:
            for child in self.children:
                leaf = child.select_leaf()
                if leaf is not None:
                    break

        return leaf

    @staticmethod
    def _expand(node):
        return random.choice(node.children)

    def simulate_playout(self, node):
        next_node = MCTSNode._expand(node) # only do this if this is not terminal state
        is_round_finished = next_node.game_state["street"] == Const.Street.FINISHED # use this to determine if round is over

    # TODO: maybe add helpers for expansion and back-propogation
