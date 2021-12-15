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
Orchestrator2 applies the logic of OR:
    Say a depends on requests b and c
    then one of b or c exist when a shows up
    b->a or c->a both satisfies
"""


class Orchestrator2:
    graph = None
    maxLen = 2
    bugSequences = []
    endpoint = None
    dataTypes = None

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
        self.invalidSequences = []

    def orchestrate2(self):
        """
        start with the nodes with in degree equals to 0
        meaning they have no depends on
        """
        for node in self.graph.nodes():
            if self.graph.in_degree(node) == 0:
                self.dfs([node], node)

    def dfs(self, sequence, node):
        """
        exit condition: if the length sequences is longer than maxLen:
            return
        reason for not using len(sequence) == self.maxLen:
        The sequences length with maxLen still need to be fuzzed
        """
        if len(sequence) > self.maxLen:
            return

        """
        Using the input sequence as parameter
        Have the sequence fuzzed in Requester function from utils.requester
        isValidSequences is a list with length of 2
        isValidSequences[0] is the list of valid sequences
        isValidSequences[1] is the list of invalid sequences
        """

        isValidSequences = Requester(sequence, self.endpoint, self.dataTypes).render()

        """
        Record all invalid sequences in invalidSeq of the class
        """
        for invalidSeq in isValidSequences[1]:
            self.invalidSequences.append(invalidSeq)

        """
        Using fuzzed valid sequences, resume with backtracking dfs
        """
        for validSeq in isValidSequences[0]:
            print("------------------------------------------")
            for req in validSeq:
                print(req.name)
            print("------------------------------------------")

            """
            Because the children of the node is requests that depends on node request
            add each child to the sequence and continue with dfs
            then restore the sequence by deleting the last request and iterate
            the next possible child
            """
            for child in self.graph.successors(node):
                sequence.append(child)
                self.dfs(sequence, child)
                sequence.pop()
