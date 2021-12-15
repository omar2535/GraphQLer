"""
TODO: Sequence generation
James
"""
import pdb
from utils.requester import Requester
import networkx as nx
import copy

"""
The difference between Orchestrator2 and Orchestrator :
Orchestrator applies the logic of AND:
    Say a depends on requests b and c
    then b and c should both exist before a is requested
    Either b->c->a or c->b->a
    Also if a depends on b, then a points to b
Orchestrator2 applies the logic of OR:
    Say a depends on requests b and c
    then one of b or c exist when a shows up
    b->a or c->a both satisfies
    If a depends on b, then b points to a
"""


class Orchestrator:
    graph = None
    maxLen = 2
    bugSequences = []
    endpoint = None
    dataTypes = None

    # constructor
    def __init__(self, graph, maxLen=2, bugSequences=[], endpoint="http://localhost:3000", dataTypes=None):
        """
        Take the parameters from main.py
        self.graph is directional graph of networkx
        determine the max length of the sequence so that dfs terminates appropriately
        The main goal of orchestrator2 is to record all invalid fuzzed sequences
        Using the valid fuzzed sequences, add more request to fuzz
        All should be based on the graph built upon depends on relationship of yaml file
        """
        self.graph = graph
        self.maxLen = maxLen
        self.bugSequences = bugSequences
        self.endpoint = endpoint
        self.dataTypes = dataTypes

    # main orchestrate function
    def orchestrate(self):
        """
        start with the nodes with out degree equals to 0
        meaning they have no depends on
        new_graph is deep copied from self.graph
        It is used to restore the modified graph after dfs
        Also the iterated self.graph shouldn't be modified in for loop
        new_graph serves as the one-to-one node mapping for iteration of nodes
        """
        new_graph = copy.deepcopy(self.graph)
        for node in new_graph.nodes():
            if new_graph.out_degree(node) == 0:

                node_to_delete = None
                for n in self.graph.nodes():
                    if n.name == node.name:
                        node_to_delete = n
                        break

                """
                For the nodes without depends on
                add them into the sequence as the first request
                Modify the graph:
                    delete the node and all its in edges
                    So that all depends on that node relationship will not be
                    considered later
                """
                node_temp = copy.deepcopy(node_to_delete)
                self.graph.remove_node(node_to_delete)
                self.dfs([node_temp])

                """
                after dfs, using new_graph to restore self.graph
                """

                self.graph = copy.deepcopy(new_graph)
                """"
                temp = []
                self.graph.add_node(node_temp)
                for edge in list(deletedEdges):
                    temp.append(edge)
                self.graph.add_edges_from(temp)
                """

    def dfs(self, sequence):
        """
        exit condition: if the length sequences is longer than maxLen:
            return
        reason for not using len(sequence) == self.maxLen:
        The sequences length with maxLen still need to be fuzzed
        """
        if len(sequence) > self.maxLen:
            return

        isValidSequences = Requester(sequence, self.endpoint, self.dataTypes).render()

        """
        Using the input sequence as parameter
        Have the sequence fuzzed in Requester function from utils.requester
        isValidSequences is a list with length of 2
        isValidSequences[0] is the list of valid sequences
        isValidSequences[1] is the list of invalid sequences
        """
        # If orchestrator is applied, de-annotate the above content to record
        # the fuzzed invalid sequences
        """"
        for bSeq in isValidSequences[1]:
            self.bugSequences.append(bSeq)
        """
        for seq in isValidSequences[0]:

            print("----------------------------")
            for request in seq:
                print(request.body)
            print("----------------------------")
            new_graph = copy.deepcopy(self.graph)
            for node in new_graph.nodes():
                if new_graph.out_degree(node) == 0:

                    # find the real node to be deleted: node_to_delete
                    node_to_delete = None
                    for n in self.graph.nodes():
                        if n.name == node.name:
                            node_to_delete = n
                            break

                    """"
                    Logic is similar to orchestrate function
                    those nodes with 0 out degree, meaning:
                        either they have no depends on
                        or their depends on requests are appended already
                    add the node to the sequence and delete the node in self.graph
                    temporarily
                    And the graph is updated
                    """
                    node_temp = copy.deepcopy(node_to_delete)
                    self.graph.remove_node(node_to_delete)
                    seq.append(node_temp)

                    self.dfs(seq)

                    """"
                    After dfs, restore the graph
                    """
                    seq.pop()
                    self.graph = copy.deepcopy(new_graph)

                    """
                    temp = []
                    self.graph.add_node(node_temp)
                    for edge in list(deletedEdges):
                        temp.append(edge)
                    self.graph.add_edges_from(temp)
                    """
