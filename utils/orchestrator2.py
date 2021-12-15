import pdb
from utils.requester import Requester
import networkx as nx
import copy


class Orchestrator2:
    graph = None
    maxLen = 2
    bugSequences = []
    endpoint = None
    dataTypes = None

    def __init__(self, graph, maxLen=2, bugSequences=[], endpoint="http://localhost:3000", dataTypes=None):
        self.graph = graph
        self.maxLen = maxLen
        self.bugSequences = bugSequences
        self.endpoint = endpoint
        self.dataTypes = dataTypes
        self.invalidSequences = []

    def orchestrate2(self):
        for node in self.graph.nodes():
            if self.graph.in_degree(node) == 0:
                self.dfs([node], node)

    def dfs(self, sequence, node):
        if len(sequence) > self.maxLen:
            return

        isValidSequences = Requester(sequence, self.endpoint, self.dataTypes).render()

        for invalidSeq in isValidSequences[1]:
            self.invalidSequences.append(invalidSeq)

        for validSeq in isValidSequences[0]:
            print("------------------------------------------")
            for req in validSeq:
                print(req.name)
            print("------------------------------------------")

            for child in self.graph.successors(node):
                sequence.append(child)
                self.dfs(sequence, child)
                sequence.pop()
