class DependencyNotMetException(Exception):
    def __init__(self, dependency_name):
        self.dependency_name = dependency_name

    def __str__(self):
        return f"dependency not met: {self.dependency_name}"
