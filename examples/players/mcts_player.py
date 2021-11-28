from pypokerengine.players import BasePokerPlayer


class MCTSPlayer(BasePokerPlayer):
# TODO: maybe inheirit from EmulatorPlayer class
    def declare_action(self, valid_actions, hole_card, round_state):
        pass

    def receive_game_start_message(self, game_info):
        pass

    def receive_round_start_message(self, round_count, hole_card, seats):
        pass

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, new_action, round_state):
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        pass


class MCTSNode:
    def __init__(self, actions, hole_card, round_state, parent=None):
        self.parent = parent
        self.children = []

    def select_leaf(self):
        pass

    def simulate_playout(self):
        pass

    # TODO: maybe add helpers for expansion and back-propogation
