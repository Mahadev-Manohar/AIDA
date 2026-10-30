import os
import sys
import pandas as pd

# Add the backend directory to sys.path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import app.state as state
from app.tools import (
    get_dataset_schema,
    get_descriptive_stats,
    plot_numerical_distribution,
    plot_categorical_distribution,
    plot_bivariate_relationship,
    plot_correlation_heatmap,
    perform_statistical_test,
    train_baseline_model
)

def run_tests():
    csv_path = os.path.join(os.path.dirname(__file__), "..", "dataset", "cs-training.csv")
    print(f"Loading test dataset from: {csv_path}")
    
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} does not exist. Make sure the dataset directory is present.")
        sys.exit(1)
        
    # Load first 5000 rows for quick testing
    state.df = pd.read_csv(csv_path, nrows=5000)
    print(f"Loaded DataFrame with shape: {state.df.shape}")
    
    # Initialize charts dir
    state.init_charts_dir()
    print(f"Charts will be saved to: {state.CHARTS_DIR}")
    
    # 1. Test schema
    print("\n--- Testing get_dataset_schema ---")
    schema = get_dataset_schema()
    print(f"Shape: {schema['shape']}")
    print(f"Columns count: {len(schema['columns'])}")
    print(f"First column info: {schema['columns'][0]}")
    
    # 2. Test descriptive stats
    print("\n--- Testing get_descriptive_stats ---")
    stats_out = get_descriptive_stats(columns=["age", "MonthlyIncome"])
    print(f"Age mean: {stats_out['age']['mean']:.2f}")
    print(f"MonthlyIncome median: {stats_out['MonthlyIncome']['median']:.2f}")
    
    # 3. Test plot numerical distribution
    print("\n--- Testing plot_numerical_distribution ---")
    res_plot_num = plot_numerical_distribution("age")
    print(f"Plot num result: {res_plot_num}")
    assert os.path.exists(os.path.join(state.CHARTS_DIR, "dist_age.png")), "dist_age.png was not created!"
    
    # 4. Test plot categorical distribution
    print("\n--- Testing plot_categorical_distribution ---")
    res_plot_cat = plot_categorical_distribution("SeriousDlqin2yrs")
    print(f"Plot cat result: {res_plot_cat}")
    assert os.path.exists(os.path.join(state.CHARTS_DIR, "dist_cat_SeriousDlqin2yrs.png")), "dist_cat_SeriousDlqin2yrs.png was not created!"
    
    # 5. Test plot bivariate relationship
    print("\n--- Testing plot_bivariate_relationship ---")
    res_plot_biv = plot_bivariate_relationship("age", "SeriousDlqin2yrs", plot_type="box")
    print(f"Plot bivariate result: {res_plot_biv}")
    assert os.path.exists(os.path.join(state.CHARTS_DIR, "rel_age_vs_SeriousDlqin2yrs.png")), "rel_age_vs_SeriousDlqin2yrs.png was not created!"
    
    # 6. Test plot correlation heatmap
    print("\n--- Testing plot_correlation_heatmap ---")
    res_corr = plot_correlation_heatmap(columns=["age", "MonthlyIncome", "DebtRatio", "SeriousDlqin2yrs"])
    print(f"Heatmap result: {res_corr}")
    assert os.path.exists(os.path.join(state.CHARTS_DIR, "correlation_heatmap.png")), "correlation_heatmap.png was not created!"
    
    # 7. Test statistical tests
    print("\n--- Testing perform_statistical_test (auto) ---")
    test_res1 = perform_statistical_test("age", "MonthlyIncome")  # num vs num -> correlation
    print(f"Num vs Num Test: {test_res1['stat_name']} - p-val: {test_res1['p_value']:.4g}")
    
    test_res2 = perform_statistical_test("SeriousDlqin2yrs", "age")  # cat (binary) vs num -> t-test
    print(f"Cat vs Num Test: {test_res2['stat_name']} - p-val: {test_res2['p_value']:.4g}")
    
    # 8. Test baseline ML training
    print("\n--- Testing train_baseline_model ---")
    ml_res = train_baseline_model(target_col="SeriousDlqin2yrs", feature_cols=["age", "MonthlyIncome", "DebtRatio"])
    print(f"ML Model: {ml_res['model_type']} on {ml_res['target']}")
    print(f"Metrics: {ml_res['metrics']}")
    print(f"Top Features: {ml_res['top_feature_importances']}")
    
    print("\n=== ALL TOOL TESTS COMPLETED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_tests()
