"""
TODO: Sequence generation
James
"""
import pdb
from utils.requester import Requester
import networkx as nx
import copy


class Orchestrator:
    graph = None
    maxLen = 2
    bugSequences = []
    endpoint = None
    dataTypes = None

    # constructor
    def __init__(self, graph, maxLen=2, bugSequences=[], endpoint="http://localhost:3000", dataTypes=None):
        self.graph = graph
        self.maxLen = maxLen
        self.bugSequences = bugSequences
        self.endpoint = endpoint
        self.dataTypes = dataTypes

    # main orchestrate function
    def orchestrate(self):
        new_graph = copy.deepcopy(self.graph)
        for node in new_graph.nodes():
            if new_graph.out_degree(node) == 0:

                node_to_delete = None
                for n in self.graph.nodes():
                    if n.name == node.name:
                        node_to_delete = n
                        break
                node_temp = copy.deepcopy(node_to_delete)
                self.graph.remove_node(node_to_delete)
                self.dfs([node_temp])

                self.graph = copy.deepcopy(new_graph)
                """"
                temp = []
                self.graph.add_node(node_temp)
                for edge in list(deletedEdges):
                    temp.append(edge)
                self.graph.add_edges_from(temp)
                """

        """
        TODO: main method to run
        """
        pass

    def dfs(self, sequence):
        if len(sequence) > self.maxLen:
            return

        isValidSequences = Requester(sequence, self.endpoint, self.dataTypes).render()

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

                    node_temp = copy.deepcopy(node_to_delete)
                    self.graph.remove_node(node_to_delete)
                    seq.append(node_temp)

                    self.dfs(seq)

                    seq.pop()
                    self.graph = copy.deepcopy(new_graph)

                    """
                    temp = []
                    self.graph.add_node(node_temp)
                    for edge in list(deletedEdges):
                        temp.append(edge)
                    self.graph.add_edges_from(temp)
                    """
