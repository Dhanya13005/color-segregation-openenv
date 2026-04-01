import random
from environment.models import Item, State

class ColorSortingEnv:

    def __init__(self):
        self.colors = ["red", "blue", "green"]
        self.reset()

    def reset(self):
        self.items = [Item(color=random.choice(self.colors), position=0)]
        self.score = 0
        self.done = False
        return self.state()

    def state(self):
        return State(items=self.items, score=self.score, done=self.done)

    def step(self, action):
        item = self.items[0]

        item.position += 1

        if item.position >= 5:
            if action == item.color:
                self.score += 10
            else:
                self.score -= 5

            self.done = True

        return self.state()