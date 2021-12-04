from pypokerengine.api import game
from pypokerengine.api.emulator import Emulator
from pypokerengine.players import BasePokerPlayer
from .emulator_player import EmulatorPlayer, MyModel
from pypokerengine.engine.poker_constants import PokerConstants as Const
import math

NUM_PLAYOUTS = 10000
ACTIONS = [MyModel.FOLD, MyModel.CALL, MyModel.MIN_RAISE, MyModel.MAX_RAISE]

UCB1_EXPLORATION_CONSTANT = math.sqrt(2)

class MCTSPlayerModel(MyModel):
    """
    Decides actions based on our
    """    
    def declare_action(self, valid_actions, hole_card, round_state):
        if self.action == self.MAX_RAISE:
            adjusted_maximum = valid_actions[2]['amount']['max'] / 10
            adjusted_maximum = int(adjusted_maximum)
            return valid_actions[2]['action'], adjusted_maximum
        return super().declare_action(valid_actions, hole_card, round_state)


class MCTSPlayer(EmulatorPlayer):

    def declare_action(self, valid_actions, hole_card, round_state):
        # The below code is running the MCTS algorithm.
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
        print(actions_and_results)
        best_action = max(actions_and_results, key=actions_and_results.get)
        self.my_model.set_action(best_action)
        return self.my_model.declare_action(valid_actions, hole_card, round_state)

    def receive_game_start_message(self, game_info):
        self.my_model = MCTSPlayerModel()
        nb_player = game_info['player_num']
        max_round = game_info['rule']['max_round']
        sb_amount = game_info['rule']['small_blind_amount']
        ante_amount = game_info['rule']['ante']

        self.emulator = Emulator()
        self.emulator.set_game_rule(nb_player, max_round, sb_amount, ante_amount)
        for player_info in game_info['seats']:
            uuid = player_info['uuid']
            player_model = self.my_model if uuid == self.uuid else self.opponents_model
            self.emulator.register_player(uuid, player_model)

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, new_action, round_state):
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        pass


class MCTSNode:
    def __init__(self, emulator, current_game_state, uuid, model=MCTSPlayerModel(), declare_action_args=None, parent=None):
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
            if is_terminal_state(new_state, self.uuid):
                self.children.append(MCTSNode(self.emulator, new_state, self.uuid, parent=self))
            else:
                new_args = [events[-1]["valid_actions"], None, events[-1]["round_state"]]
                self.children.append(MCTSNode(self.emulator, new_state, self.uuid, declare_action_args=new_args, parent=self))
            
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
            # print("No Playouts.")
            return self
        else:
            # print("Creating children.")
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
            # TODO: Can num_playouts ever be 0?
            next_node.propagated_state_value = ((next_node.propagated_state_value * (next_node.num_playouts - 1)) +
                                                next_node.compute_state_value(round_end_state)) / next_node.num_playouts
            # print(next_node.propagated_state_value)
            if next_node.parent is not None:
                next_node.back_propagation()
        else:
            # print("ATTEMPTING TO SIMULATE PLAYOUT WITH NODE CONTAINING TERMINAL STATE")
            self.back_propagation()

    def selection_policy_value(self):
        """
        Computes and returns the UCB1 selection policy for this node.
        """
        if self.num_playouts == 0:
            return 0

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
        if self.parent is not None:
            self.parent.propagated_state_value += self.propagated_state_value
            self.parent.num_playouts += 1
        # if not is_terminal_state(self.game_state, self.uuid):
        #     self.propagated_state_value = sum([child.propagated_state_value for child in self.children])
        #     self.num_playouts = sum([child.num_playouts for child in self.children])

        # if self.parent is not None:
        #     self.parent.back_propagation()

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
    return [player for player in game_state['table'].seats.players if player.uuid == uuid][0].stack

