from environment.env import ColorSortingEnv

# EASY TASK
def easy_task():
    env = ColorSortingEnv()
    state = env.reset()

    reward = 0

    while not state.done:
        action = state.items[0].color
        prev_score = env.score
        state = env.step(action)
        reward += (env.score - prev_score)

    return min(1.0, reward / 10)


# MEDIUM TASK
def medium_task():
    env = ColorSortingEnv()
    state = env.reset()

    reward = 0

    while not state.done:
        action = "red"
        prev_score = env.score
        state = env.step(action)
        reward += (env.score - prev_score)

    return max(0.0, min(1.0, reward / 10))


# HARD TASK
def hard_task():
    env = ColorSortingEnv()
    state = env.reset()

    reward = 0

    while not state.done:
        action = "blue"
        prev_score = env.score
        state = env.step(action)
        reward += (env.score - prev_score)

    return max(0.0, min(1.0, reward / 10))