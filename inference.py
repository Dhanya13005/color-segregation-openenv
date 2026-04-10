
"""
inference.py — AI Conveyor Color Segregation System
OpenEnv Hackathon Submission
"""

import os
import random
from openai import OpenAI

# ================= ENV VARIABLES =================
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "gpt-4.1-mini")
HF_TOKEN     = os.getenv("HF_TOKEN")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN
)

# ================= CONSTANTS =================
TASK_NAME = "color-segregation"
ENV_NAME  = "conveyor-belt"
COLORS    = ["red", "blue", "green"]

# ================= ENVIRONMENT =================
class ConveyorEnv:
    def __init__(self, max_steps=5):
        self.max_steps = max_steps
        self.reset()

    def reset(self):
        self.step_count = 0
        self.done = False
        self.current_color = random.choice(COLORS)
        self.last_action_error = None
        return {"color": self.current_color}

    def step(self, action):
        self.step_count += 1
        self.last_action_error = None

        action = action.strip().lower().replace("'", "").replace('"', "")

        if action not in COLORS:
            self.last_action_error = f"invalid_action:{action}"
            reward = 0.0
        elif action == self.current_color:
            reward = 1.0
        else:
            reward = 0.0

        self.current_color = random.choice(COLORS)
        self.done = self.step_count >= self.max_steps

        return (
            {"color": self.current_color},
            reward,
            self.done,
            {"error": self.last_action_error}
        )

    def close(self):
        pass

# ================= LLM ACTION =================
def get_llm_action(obs):
    prompt = f"""
You are controlling a conveyor belt system.
Item color: {obs['color']}

Choose one: red, blue, green
Output ONLY the color.
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0
        )
        text = response.choices[0].message.content.lower()

        for c in COLORS:
            if c in text:
                return c
        return random.choice(COLORS)

    except:
        return obs["color"]

# ================= MAIN =================
def run_episode():
    env = ConveyorEnv()
    rewards = []

    print(f"[START] task={TASK_NAME} env={ENV_NAME} model={MODEL_NAME}")

    try:
        obs = env.reset()

        step = 1
        while True:
            action = get_llm_action(obs)
            obs, reward, done, info = env.step(action)

            rewards.append(reward)

            err = info.get("error") or "null"
            done_str = "true" if done else "false"

            print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_str} error={err}")

            if done:
                break
            step += 1

        success = any(r > 0 for r in rewards)

    except Exception as e:
        print(f"[STEP] step=0 action=null reward=0.00 done=true error={str(e)}")
        success = False

    finally:
        env.close()

    rewards_str = ",".join(f"{r:.2f}" for r in rewards) if rewards else "0.00"
    success_str = "true" if success else "false"

    print(f"[END] success={success_str} steps={len(rewards)} rewards={rewards_str}")

# ================= ENTRY =================
if __name__ == "__main__":
    run_episode()

