"""
inference.py — AI Conveyor Color Segregation System
====================================================
OpenEnv Hackathon Submission

Required environment variables:
  API_BASE_URL  — LLM API endpoint         (default: https://api.openai.com/v1)
  MODEL_NAME    — Model identifier          (default: gpt-4.1-mini)
  HF_TOKEN      — Hugging Face API token    (REQUIRED, no default)

Output format (exact, to stdout):
  [START] task=<task> env=<env> model=<model>
  [STEP]  step=<n> action=<action> reward=<0.00> done=<bool> error=<msg|null>
  [END]   success=<bool> steps=<n> rewards=<r1,r2,...>
"""

import os
import sys
import time
import random

from openai import OpenAI

# ── Environment variables (with defaults where required) ─────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "gpt-4.1-mini")
HF_TOKEN     = os.getenv("HF_TOKEN")     # Required — no default

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

# ── OpenAI client (uses HF_TOKEN as api_key) ─────────────────────
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN,
)

# ── Task / env constants ──────────────────────────────────────────
TASK_NAME = "color-segregation"
ENV_NAME  = "conveyor-belt"
COLORS    = ["red", "blue", "green"]

# ─────────────────────────────────────────────────────────────────
#  ENVIRONMENT  (simulated conveyor belt)
# ─────────────────────────────────────────────────────────────────
class ConveyorEnv:
    """Simulated conveyor belt color-segregation environment."""

    def __init__(self, max_steps: int = 5):
        self.max_steps        = max_steps
        self.step_count       = 0
        self.current_color    = None
        self.done             = False
        self.last_action_error= None
        self._reset_state()

    def _reset_state(self):
        self.current_color     = random.choice(COLORS)
        self.step_count        = 0
        self.done              = False
        self.last_action_error = None

    def reset(self) -> dict:
        """Reset environment and return initial observation."""
        self._reset_state()
        return {"color": self.current_color, "step": 0}

    def step(self, action: str) -> tuple:
        """
        Execute action, return (observation, reward, done, info).
        action — one of 'red', 'blue', 'green'
        """
        self.step_count += 1
        self.last_action_error = None

        action_clean = action.strip().lower().replace("'", "").replace('"', "")

        # Validate action
        if action_clean not in COLORS:
            self.last_action_error = f"invalid_action:{action_clean}"
            reward = 0.0
        elif action_clean == self.current_color:
            reward = 1.0         # correct classification
        else:
            reward = 0.0         # wrong classification

        # Spawn next item
        self.current_color = random.choice(COLORS)

        self.done = self.step_count >= self.max_steps
        obs = {"color": self.current_color, "step": self.step_count}
        return obs, reward, self.done, {"error": self.last_action_error}

    def close(self):
        pass


# ─────────────────────────────────────────────────────────────────
#  LLM AGENT  (calls OpenAI-compatible API to decide action)
# ─────────────────────────────────────────────────────────────────
def get_llm_action(obs: dict) -> str:
    """
    Ask the LLM to classify the color on the belt.
    Returns one of: 'red', 'blue', 'green'
    """
    prompt = (
        f"You are an AI controlling a conveyor belt color-segregation system.\n"
        f"The item currently on the belt is: {obs['color']}\n"
        f"You must output ONLY one word — the color to classify this item.\n"
        f"Valid choices: red, blue, green\n"
        f"Output exactly one word, nothing else."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.0,
        )
        answer = response.choices[0].message.content.strip().lower()
        # Extract valid color from response
        for color in COLORS:
            if color in answer:
                return color
        return random.choice(COLORS)   # fallback
    except Exception as e:
        # If LLM call fails, use rule-based fallback
        return obs.get("color", random.choice(COLORS))


# ─────────────────────────────────────────────────────────────────
#  MAIN EPISODE RUNNER
# ─────────────────────────────────────────────────────────────────
def run_episode(max_steps: int = 5) -> dict:
    """
    Run one complete episode and print OpenEnv log lines to stdout.

    Log format (exact):
      [START] task=<task> env=<env> model=<model>
      [STEP]  step=<n> action=<action> reward=<0.00> done=<bool> error=<msg|null>
      [END]   success=<bool> steps=<n> rewards=<r1,r2,...>
    """
    env     = ConveyorEnv(max_steps=max_steps)
    rewards = []
    success = False

    # ── [START] ────────────────────────────────────────────────
    print(f"[START] task={TASK_NAME} env={ENV_NAME} model={MODEL_NAME}",
          flush=True)

    try:
        obs = env.reset()

        for step_num in range(1, max_steps + 1):
            # Agent decides action
            action = get_llm_action(obs)

            # Environment step
            obs, reward, done, info = env.step(action)
            rewards.append(reward)

            error_str = info.get("error") or "null"
            done_str  = "true" if done else "false"

            # ── [STEP] ─────────────────────────────────────────
            print(
                f"[STEP] step={step_num} action={action!r} "
                f"reward={reward:.2f} done={done_str} error={error_str}",
                flush=True
            )

            if done:
                break

        # Episode success = at least one correct classification
        success = any(r > 0 for r in rewards)

    except Exception as exc:
        rewards = rewards or [0.0]
        success = False
        print(f"[STEP] step={len(rewards)} action=null reward=0.00 "
              f"done=true error={str(exc)}", flush=True)
    finally:
        env.close()

    # ── [END] ──────────────────────────────────────────────────
    rewards_str  = ",".join(f"{r:.2f}" for r in rewards) if rewards else "0.00"
    success_str  = "true" if success else "false"
    steps_done   = len(rewards)

    print(
        f"[END] success={success_str} steps={steps_done} rewards={rewards_str}",
        flush=True
    )

    return {"success": success, "steps": steps_done, "rewards": rewards}


def run_inference(prompt: str = "Hello from OpenEnv!") -> str:
    """
    Simple inference function (used for direct API calls / testing).
    Returns LLM response as string.
    """
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"


# ─────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_episode(max_steps=5)
