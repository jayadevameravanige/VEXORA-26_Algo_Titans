"""
Test what keys are in ghost_explanations and duplicate_explanations
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from ml.pipeline import VoteGuardPipeline

# Run a quick pipeline on a small dataset
pipeline = VoteGuardPipeline()
result = pipeline.run('smoketest_data.csv')

print("\n=== GHOST EXPLANATIONS STRUCTURE ===")
if result.ghost_explanations:
    print(f"Total: {len(result.ghost_explanations)} ghost voters\n")
    print("First ghost explanation keys:")
    print(result.ghost_explanations[0].keys())
    print("\nFirst ghost explanation:")
    import json
    print(json.dumps(result.ghost_explanations[0], indent=2, default=str))
else:
    print("No ghost voters detected")

print("\n=== DUPLICATE EXPLANATIONS STRUCTURE ===")
if result.duplicate_explanations:
    print(f"Total: {len(result.duplicate_explanations)} duplicate voters\n")
    print("First duplicate explanation keys:")
    print(result.duplicate_explanations[0].keys())
    print("\nFirst duplicate explanation:")
    print(json.dumps(result.duplicate_explanations[0], indent=2, default=str))
else:
    print("No duplicate voters detected")
