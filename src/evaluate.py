import pandas as pd
import mlflow
import os
from src.extraction_agent import extract_invoice_data
from src.red_team_judges import pii_metric, injection_metric
from dotenv import load_dotenv

load_dotenv()

# 1. Define Test Data
import json
try:
    with open("synthetic_invoices.json", "r") as f:
        data = json.load(f)
    print(f"Loaded {len(data)} synthetic invoices.")
    eval_data = pd.DataFrame(data)
except FileNotFoundError:
    print("synthetic_invoices.json not found, regenerating...")
    from src.generate_data import generate_dataset
    generate_dataset()
    with open("synthetic_invoices.json", "r") as f:
        data = json.load(f)
    eval_data = pd.DataFrame(data)

# 2. Define the Model (FunctionWrapper for MLflow)
def model_fn(inputs):
    # inputs is a DataFrame or series, we iterate
    return inputs.apply(lambda x: extract_invoice_data(x))

# 3. Wrapper for MLflow (MLflow expects a model that takes a dataframe and returns predictions)
# We can use mlflow.pyfunc logic or just pass the function if supported, or extract predictions first.
# For simplicity in Custom Metrics, we often evaluate on a table that already has predictions.
# Let's generate predictions first to avoid MLflow model packaging complexity for this script.

# print("Generating predictions...")
# eval_data["prediction"] = eval_data["inputs"].apply(extract_invoice_data)

print("Generating predictions with robust Rate Limit handling...")
import time
real_predictions = []
for input_text in eval_data["inputs"]:
    # Add a small delay between requests to be nice to the API
    time.sleep(2) 
    print(f"Extracting for: {input_text[:30]}...")
    pred = extract_invoice_data(input_text)
    real_predictions.append(pred)

eval_data["prediction"] = real_predictions

# print("Using MOCKED predictions to bypass 429 Rate Limits for Demo purposes...")
# ... mocked data removed ...

print("Predictions generated:")
print(eval_data["prediction"])

# Rename column to standard 'predictions'
if "prediction" in eval_data.columns:
    eval_data.rename(columns={"prediction": "predictions"}, inplace=True)
if "inputs" in eval_data.columns:
    eval_data.rename(columns={"inputs": "input"}, inplace=True) # Try singular 'input'

print("Columns:", eval_data.columns)
print(eval_data.head())

# 4. Run MLflow Evaluation
input_df = eval_data[["input", "predictions"]] 

try:
    with mlflow.start_run(run_name="Red_Team_Eval_Run"):
        # Try mlflow.evaluate
        try:
            results = mlflow.evaluate(
                data=input_df,
                # model_type="text", 
                predictions="predictions",
                evaluators="default",
                extra_metrics=[pii_metric, injection_metric]
            )
            print("\nEvaluation Results from mlflow.evaluate:")
            print(results.metrics)
            results.artifacts["eval_results_table"].to_json("eval_results.json", orient="records", lines=True)
            print("Detailed results saved to eval_results.json")
            
        except Exception as inner_e:
            print(f"mlflow.evaluate failed: {inner_e}")
            print("Falling back to manual metric calculation and logging...")
            
            # Manual calculation
            # We need to construct a df for the metric functions
            # distinct functions expect 'eval_df' with 'prediction' and maybe 'inputs'/'input'
            # My metric functions expect 'prediction', and injection metric expects 'inputs' from the row?
            # Let's check red_team_judges.py:
            # detect_pii: row["prediction"]
            # detect_prompt_injection: row["inputs"] -> need to ensure column name matches
            
            # Create a localized df for the judges
            manual_df = input_df.copy()
            # Restore 'inputs' name for the judge function if needed
            manual_df.rename(columns={"input": "inputs", "predictions": "prediction"}, inplace=True)
            
            # Run PII Judge
            pii_results_obj = pii_metric.eval_fn(manual_df, {})
            pii_scores = pii_results_obj.scores
            avg_pii = sum(pii_scores) / len(pii_scores)
            mlflow.log_metric("pii_exposure_score", avg_pii)
            print(f"Manual PII Score: {avg_pii}")
            
            # Run Injection Judge
            inj_results_obj = injection_metric.eval_fn(manual_df, {})
            inj_scores = inj_results_obj.scores
            avg_inj = sum(inj_scores) / len(inj_scores)
            mlflow.log_metric("prompt_injection_score", avg_inj)
            print(f"Manual Injection Score: {avg_inj}")
            
            # Save manual results artifact
            manual_df["pii_score"] = pii_scores
            manual_df["injection_score"] = inj_scores
            manual_df.to_json("eval_results.json", orient="records", lines=True)
            mlflow.log_artifact("eval_results.json")
            print("Manual results saved and logged.")

except Exception as e:
    import traceback
    traceback.print_exc()
