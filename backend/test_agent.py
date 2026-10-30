import os
import sys
import pandas as pd

# Add the backend directory to sys.path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import app.state as state
import app.config as config
from app.agent import run_agent_loop

def run_agent_test():
    # Load dataset
    csv_path = os.path.join(os.path.dirname(__file__), "..", "dataset", "cs-training.csv")
    print(f"Loading dataset from: {csv_path}")
    
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} does not exist.")
        sys.exit(1)
        
    state.df = pd.read_csv(csv_path, nrows=5000)
    print(f"Loaded DataFrame: {state.df.shape}")
    
    # Initialize charts dir
    state.init_charts_dir()
    
    # Quick check for API key
    if not config.GROQ_API_KEY:
        print("\n[WARNING] GROQ_API_KEY is not set in backend/.env or your environment variables.")
        print("Please edit backend/.env and put your Groq API Key before running.")
        return

    # Define query
    query = "Profile the columns and plot the distribution of 'age'. Then train a model to predict 'SeriousDlqin2yrs' using 'age' and 'MonthlyIncome'."
    
    print(f"\nSending Query to Agent: '{query}'")
    print("----------------------------------------------------------------------")
    
    # Run loop
    for step in run_agent_loop(query):
        step_type = step.get("type")
        
        if step_type == "info":
            print(f"[INFO] {step.get('content')}")
        elif step_type == "thought":
            print(f"\n[THOUGHT]\n{step.get('content')}")
        elif step_type == "tool_call":
            print(f"\n[TOOL CALL] Calling function '{step.get('name')}' with arguments:")
            print(step.get("arguments"))
        elif step_type == "tool_output":
            print(f"[TOOL OUTPUT] Function '{step.get('name')}' output summary:")
            res = step.get("result")
            if isinstance(res, dict) and "error" in res:
                print(f"  --> ERROR: {res['error']}")
            elif isinstance(res, dict) and "plot_path" in res:
                print(f"  --> Saved plot: {res['plot_path']}")
            elif isinstance(res, dict) and "metrics" in res:
                print(f"  --> Model trained! Metrics: {res['metrics']}")
            else:
                # Truncate output representation
                s = str(res)
                print(f"  --> {s[:120]}..." if len(s) > 120 else f"  --> {s}")
        elif step_type == "error":
            print(f"\n[AGENT ERROR] {step.get('content')}")
            if "traceback" in step:
                print(step["traceback"])
        elif step_type == "final_answer":
            print(f"\n==============================================================")
            print(f"[FINAL RESPONSE]\n{step.get('content')}")
            print(f"==============================================================")

if __name__ == "__main__":
    run_agent_test()
