from environment.tasks import easy_task, medium_task, hard_task

print("Running Inference...\n")

easy_score = easy_task()
print(f"Easy Task Score: {easy_score}")

medium_score = medium_task()
print(f"Medium Task Score: {medium_score}")

hard_score = hard_task()
print(f"Hard Task Score: {hard_score}")