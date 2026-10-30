import os
import re
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server environment
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, mean_squared_error, r2_score
from typing import Dict, Any, List, Optional
import app.state as state

def _safe_name(name: str) -> str:
    """Makes a column name safe to use inside a chart filename."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(name))

def _check_df() -> pd.DataFrame:
    """Helper function to verify if a dataset has been loaded."""
    if state.df is None:
        raise ValueError("No dataset loaded. Please upload a CSV first.")
    return state.df

def get_dataset_schema() -> Dict[str, Any]:
    """
    Returns the schema of the loaded dataset.
    Includes columns, data types, non-null counts, and missing values.
    """
    df = _check_df()
    info = []
    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        null_pct = float((null_count / len(df)) * 100)
        info.append({
            "column": col,
            "dtype": str(df[col].dtype),
            "non_null_count": int(df[col].count()),
            "missing_count": null_count,
            "missing_percentage": round(null_pct, 2),
            "unique_values": int(df[col].nunique())
        })
    
    return {
        "shape": {"rows": df.shape[0], "columns": df.shape[1]},
        "columns": info
    }

def get_descriptive_stats(columns: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Returns descriptive statistics for numerical columns in the dataset.
    Optionally filters by a specific list of columns.
    """
    df = _check_df()
    if columns:
        valid_cols = [c for c in columns if c in df.columns]
        sub_df = df[valid_cols]
    else:
        sub_df = df.select_dtypes(include=[np.number])
        
    if sub_df.empty:
        return {"error": "No numerical columns selected or available."}
        
    stats_dict = {}
    for col in sub_df.columns:
        desc = sub_df[col].describe()
        stats_dict[col] = {
            "mean": float(desc["mean"]) if not np.isnan(desc["mean"]) else None,
            "std": float(desc["std"]) if not np.isnan(desc["std"]) else None,
            "min": float(desc["min"]) if not np.isnan(desc["min"]) else None,
            "25%": float(desc["25%"]) if not np.isnan(desc["25%"]) else None,
            "50%": float(desc["50%"]) if not np.isnan(desc["50%"]) else None,
            "75%": float(desc["75%"]) if not np.isnan(desc["75%"]) else None,
            "max": float(desc["max"]) if not np.isnan(desc["max"]) else None,
            "median": float(sub_df[col].median()),
            "skew": float(sub_df[col].skew()) if not np.isnan(sub_df[col].skew()) else None
        }
    return stats_dict

def plot_numerical_distribution(column: str, bins: int = 30) -> Dict[str, Any]:
    """
    Generates and saves a distribution plot (histogram + boxplot) for a numerical column.
    """
    df = _check_df()
    if column not in df.columns:
        return {"error": f"Column '{column}' not found in dataset."}
        
    if not np.issubdtype(df[column].dtype, np.number):
        return {"error": f"Column '{column}' is not numerical."}
        
    state.init_charts_dir()
    filename = f"dist_{_safe_name(column)}.png"
    filepath = os.path.join(state.CHARTS_DIR, filename)
    
    # Close any open plots to avoid leakage
    plt.close('all')
    
    # Set style
    sns.set_theme(style="whitegrid")
    
    # Create subplots (top: boxplot, bottom: histogram)
    fig, (ax_box, ax_hist) = plt.subplots(2, sharex=True, gridspec_kw={"height_ratios": (.15, .85)}, figsize=(8, 6))
    
    # Clean data (drop nulls for plotting)
    clean_data = df[column].dropna()
    
    # Plot components
    sns.boxplot(x=clean_data, ax=ax_box, color="#4f46e5")
    sns.histplot(x=clean_data, ax=ax_hist, bins=bins, kde=True, color="#6366f1")
    
    # Clear labels/borders
    ax_box.set(xlabel='')
    ax_box.set_title(f"Distribution of {column}", fontsize=14, fontweight='bold', pad=10)
    ax_hist.set_xlabel(column, fontsize=12)
    ax_hist.set_ylabel("Frequency", fontsize=12)
    
    plt.tight_layout()
    fig.savefig(filepath, dpi=150)
    plt.close(fig)
    
    return {
        "message": f"Successfully generated distribution plot for {column}.",
        "plot_path": f"/static/charts/{filename}",
        "summary": f"Plot shows the distribution of {column} with a median of {clean_data.median():.2f} and std of {clean_data.std():.2f}."
    }

def plot_categorical_distribution(column: str) -> Dict[str, Any]:
    """
    Generates and saves a bar chart showing frequency counts for a categorical/discrete column.
    """
    df = _check_df()
    if column not in df.columns:
        return {"error": f"Column '{column}' not found in dataset."}
        
    state.init_charts_dir()
    filename = f"dist_cat_{_safe_name(column)}.png"
    filepath = os.path.join(state.CHARTS_DIR, filename)
    
    plt.close('all')
    sns.set_theme(style="whitegrid")
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Get top 15 values to avoid cluttered charts
    value_counts = df[column].value_counts()
    if len(value_counts) > 15:
        value_counts = value_counts.head(15)
        title_suffix = " (Top 15 values)"
    else:
        title_suffix = ""
        
    sns.barplot(x=value_counts.values, y=value_counts.index.astype(str), ax=ax, palette="viridis", hue=value_counts.index.astype(str), legend=False)
    
    ax.set_title(f"Frequency Counts of {column}{title_suffix}", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Count", fontsize=12)
    ax.set_ylabel(column, fontsize=12)
    
    plt.tight_layout()
    fig.savefig(filepath, dpi=150)
    plt.close(fig)
    
    return {
        "message": f"Successfully generated categorical distribution plot for {column}.",
        "plot_path": f"/static/charts/{filename}",
        "summary": f"Plot shows the value counts for {column}. Total unique categories: {df[column].nunique()}."
    }

def plot_bivariate_relationship(x_col: str, y_col: str, plot_type: str = "auto") -> Dict[str, Any]:
    """
    Plots the relationship between two variables.
    Supported plot types: 'scatter' (num vs num), 'box' (cat vs num), 'bar' (cat vs cat / counts), or 'auto'.
    """
    df = _check_df()
    if x_col not in df.columns or y_col not in df.columns:
        return {"error": f"One or both columns ({x_col}, {y_col}) not found in dataset."}
        
    x_is_num = np.issubdtype(df[x_col].dtype, np.number)
    y_is_num = np.issubdtype(df[y_col].dtype, np.number)
    
    # Automatically infer plot type if set to 'auto'
    if plot_type == "auto":
        if x_is_num and y_is_num:
            plot_type = "scatter"
        elif (x_is_num and not y_is_num) or (not x_is_num and y_is_num):
            plot_type = "box"
        else:
            plot_type = "bar"
            
    state.init_charts_dir()
    filename = f"rel_{_safe_name(x_col)}_vs_{_safe_name(y_col)}.png"
    filepath = os.path.join(state.CHARTS_DIR, filename)
    
    plt.close('all')
    sns.set_theme(style="whitegrid")
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Drop rows where either column is null for this plot
    plot_df = df[[x_col, y_col]].dropna()
    
    if plot_df.empty:
        return {"error": f"No non-null overlapping data for columns {x_col} and {y_col}."}
        
    if plot_type == "scatter":
        sns.scatterplot(data=plot_df, x=x_col, y=y_col, ax=ax, alpha=0.6, color="#4f46e5")
        # Add regression line if numeric
        try:
            sns.regplot(data=plot_df, x=x_col, y=y_col, ax=ax, scatter=False, color="#ef4444")
        except Exception:
            pass
        ax.set_title(f"Scatter Plot: {y_col} vs {x_col}", fontsize=14, fontweight='bold', pad=15)
        
    elif plot_type == "box":
        # Ensure category is on the x-axis
        cat_col = x_col if not x_is_num else y_col
        num_col = y_col if not x_is_num else x_col
        
        # Limit to top 10 categories to avoid rendering too many boxes
        top_cats = plot_df[cat_col].value_counts().head(10).index
        filtered_df = plot_df[plot_df[cat_col].isin(top_cats)]
        
        sns.boxplot(data=filtered_df, x=cat_col, y=num_col, ax=ax, palette="Set2", hue=cat_col, legend=False)
        ax.set_title(f"Box Plot of {num_col} by {cat_col}", fontsize=14, fontweight='bold', pad=15)
        plt.xticks(rotation=45)
        
    elif plot_type == "bar":
        # Grouped bar chart or count plot
        sns.countplot(data=plot_df, x=x_col, hue=y_col, ax=ax, palette="Set2")
        ax.set_title(f"Count Plot: {x_col} grouped by {y_col}", fontsize=14, fontweight='bold', pad=15)
        plt.xticks(rotation=45)
        
    else:
        plt.close(fig)
        return {"error": f"Unsupported plot type: '{plot_type}'."}
        
    plt.tight_layout()
    fig.savefig(filepath, dpi=150)
    plt.close(fig)
    
    return {
        "message": f"Successfully generated {plot_type} plot for {x_col} vs {y_col}.",
        "plot_path": f"/static/charts/{filename}",
        "summary": f"Plotting {y_col} against {x_col} using plot type '{plot_type}'."
    }

def plot_correlation_heatmap(columns: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Computes Pearson correlation for numerical columns and generates a heatmap.
    """
    df = _check_df()
    
    if columns:
        valid_cols = [c for c in columns if c in df.columns]
        sub_df = df[valid_cols].select_dtypes(include=[np.number])
    else:
        sub_df = df.select_dtypes(include=[np.number])
        
    if sub_df.shape[1] < 2:
        return {"error": "Need at least 2 numerical columns to calculate correlation."}
        
    corr_matrix = sub_df.corr()
    
    state.init_charts_dir()
    filename = "correlation_heatmap.png"
    filepath = os.path.join(state.CHARTS_DIR, filename)
    
    plt.close('all')
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Mask for upper triangle
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    
    sns.heatmap(
        corr_matrix, 
        mask=mask, 
        annot=True, 
        fmt=".2f", 
        cmap="coolwarm", 
        vmin=-1, 
        vmax=1, 
        square=True, 
        linewidths=.5, 
        cbar_kws={"shrink": .8},
        ax=ax
    )
    
    ax.set_title("Correlation Matrix Heatmap", fontsize=14, fontweight='bold', pad=15)
    
    plt.tight_layout()
    fig.savefig(filepath, dpi=150)
    plt.close(fig)
    
    # Extract top correlations (excluding self-correlations)
    corr_unstacked = corr_matrix.unstack()
    corr_pairs = corr_unstacked[corr_unstacked.index.get_level_values(0) != corr_unstacked.index.get_level_values(1)]
    abs_corr = corr_pairs.abs().sort_values(ascending=False)
    
    top_3_pairs = []
    seen = set()
    for idx, val in abs_corr.items():
        sorted_pair = tuple(sorted(idx))
        if sorted_pair not in seen:
            seen.add(sorted_pair)
            top_3_pairs.append({
                "var1": idx[0],
                "var2": idx[1],
                "correlation": float(corr_matrix.loc[idx[0], idx[1]])
            })
            if len(top_3_pairs) == 3:
                break
                
    return {
        "message": "Successfully generated correlation heatmap.",
        "plot_path": "/static/charts/correlation_heatmap.png",
        "top_correlations": top_3_pairs
    }

def perform_statistical_test(col_a: str, col_b: str, test_type: str = "auto") -> Dict[str, Any]:
    """
    Executes a statistical test (t-test, ANOVA, or Chi-square) between two columns.
    If test_type is 'auto', automatically select appropriate test based on column types.
    """
    df = _check_df()
    if col_a not in df.columns or col_b not in df.columns:
        return {"error": f"One or both columns ({col_a}, {col_b}) not found in dataset."}
        
    # Drop missing values
    data = df[[col_a, col_b]].dropna()
    if len(data) < 10:
        return {"error": "Not enough data points after dropping missing values (minimum 10 needed)."}
        
    a_is_num = np.issubdtype(df[col_a].dtype, np.number)
    b_is_num = np.issubdtype(df[col_b].dtype, np.number)
    
    # Check if a column should be treated as categorical (non-numeric OR numeric with low unique values <= 10)
    a_is_cat = not a_is_num or df[col_a].nunique() <= 10
    b_is_cat = not b_is_num or df[col_b].nunique() <= 10
    
    # Auto-select test type
    if test_type == "auto":
        if not a_is_cat and not b_is_cat:
            test_type = "correlation"
        elif (not a_is_cat and b_is_cat) or (a_is_cat and not b_is_cat):
            # Numeric vs Categorical
            num_col = col_a if not a_is_cat else col_b
            cat_col = col_b if not a_is_cat else col_a
            unique_cats = data[cat_col].nunique()
            if unique_cats == 2:
                test_type = "t-test"
            else:
                test_type = "anova"
        else:
            # Categorical vs Categorical
            test_type = "chi-square"
            
    # Implement tests
    result = {"test_type": test_type, "column_a": col_a, "column_b": col_b}
    
    if test_type == "correlation":
        coef, p_val = stats.pearsonr(data[col_a], data[col_b])
        result.update({
            "coefficient": float(coef),
            "p_value": float(p_val),
            "stat_name": "Pearson Correlation",
            "interpretation": f"Pearson Correlation coef = {coef:.4f} (p-value = {p_val:.4g}). " +
                             ("Statistically significant relationship." if p_val < 0.05 else "Not statistically significant.")
        })
        
    elif test_type == "t-test":
        cat_col = col_a if a_is_cat else col_b
        num_col = col_b if a_is_cat else col_a
        groups = data[cat_col].unique()
        if len(groups) != 2:
            return {"error": f"t-test requires exactly 2 groups in category column '{cat_col}', found {len(groups)}."}
            
        group1 = data[data[cat_col] == groups[0]][num_col]
        group2 = data[data[cat_col] == groups[1]][num_col]
        
        stat, p_val = stats.ttest_ind(group1, group2, equal_var=False)
        result.update({
            "statistic": float(stat),
            "p_value": float(p_val),
            "stat_name": f"Welch's t-test (comparing {groups[0]} vs {groups[1]} on {num_col})",
            "interpretation": f"t-statistic = {stat:.4f} (p-value = {p_val:.4g}). " +
                             ("The difference in means is statistically significant (p < 0.05)." if p_val < 0.05 else "The difference is not statistically significant.")
        })
        
    elif test_type == "anova":
        cat_col = col_a if a_is_cat else col_b
        num_col = col_b if a_is_cat else col_a
        groups = data[cat_col].unique()
        
        if len(groups) < 2:
            return {"error": f"ANOVA requires at least 2 groups in '{cat_col}', found {len(groups)}."}
            
        group_data = [data[data[cat_col] == g][num_col] for g in groups]
        stat, p_val = stats.f_oneway(*group_data)
        result.update({
            "statistic": float(stat),
            "p_value": float(p_val),
            "stat_name": f"One-way ANOVA (comparing {num_col} across groups of {cat_col})",
            "interpretation": f"F-statistic = {stat:.4f} (p-value = {p_val:.4g}). " +
                             ("At least one group mean is significantly different (p < 0.05)." if p_val < 0.05 else "No statistically significant difference between group means.")
        })
        
    elif test_type == "chi-square":
        contingency_table = pd.crosstab(data[col_a], data[col_b])
        stat, p_val, dof, expected = stats.chi2_contingency(contingency_table)
        result.update({
            "statistic": float(stat),
            "p_value": float(p_val),
            "degrees_of_freedom": int(dof),
            "stat_name": f"Chi-Square Test of Independence ({col_a} vs {col_b})",
            "interpretation": f"Chi-square statistic = {stat:.4f} (p-value = {p_val:.4g}). " +
                             ("Significant association between variables (p < 0.05)." if p_val < 0.05 else "No significant association.")
        })
    else:
        return {"error": f"Unknown statistical test type: '{test_type}'."}
        
    return result

def train_baseline_model(target_col: str, feature_cols: Optional[List[str]] = None, model_type: str = "auto") -> Dict[str, Any]:
    """
    Trains a baseline Random Forest model on the dataset.
    Splits the data, imputes missing values, processes features, and returns validation metrics and feature importances.
    This provides a highly impressive baseline analysis tool for the agent.
    """
    df = _check_df()
    
    if target_col not in df.columns:
        return {"error": f"Target column '{target_col}' not found in dataset."}
        
    # Drop rows where target is null
    df_clean = df.dropna(subset=[target_col]).copy()
    if len(df_clean) < 50:
        return {"error": f"Insufficient data for modeling (only {len(df_clean)} non-null targets available)."}
        
    # Decide features if not specified
    if feature_cols:
        valid_features = [f for f in feature_cols if f in df_clean.columns and f != target_col]
    else:
        # Exclude high cardinality ID-like columns automatically
        exclude = [target_col]
        for col in df_clean.columns:
            if df_clean[col].nunique() == len(df_clean) or col.lower() in ["id", "index", "unnamed: 0"]:
                exclude.append(col)
        valid_features = [c for c in df_clean.columns if c not in exclude]
        
    if not valid_features:
        return {"error": "No valid feature columns available or specified."}
        
    X = df_clean[valid_features]
    y = df_clean[target_col]
    
    # Auto-detect classification vs regression
    unique_targets = y.nunique()
    target_is_numeric = np.issubdtype(y.dtype, np.number)
    
    if model_type == "auto":
        if unique_targets <= 10 or not target_is_numeric:
            model_type = "classification"
        else:
            model_type = "regression"
            
    # Identify feature types
    numeric_features = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_features = X.select_dtypes(exclude=[np.number]).columns.tolist()
    
    # Preprocessing pipelines
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ]
    )
    
    # Define Model
    if model_type == "classification":
        model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=8)
    else:
        model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=8)
        
    clf = Pipeline(steps=[('preprocessor', preprocessor),
                          ('classifier', model)])
    
    # Train-test split
    # For large datasets (like 150k rows), cap model training size to 10k rows to ensure quick execution times (under 5 seconds)
    if len(df_clean) > 15000:
        df_sample = df_clean.sample(15000, random_state=42)
        X_sample = df_sample[valid_features]
        y_sample = df_sample[target_col]
        X_train, X_test, y_train, y_test = train_test_split(X_sample, y_sample, test_size=0.2, random_state=42)
        sampled_note = f"Model trained on a random sample of 15,000 rows (from total {len(df_clean)} rows) for performance."
    else:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        sampled_note = f"Model trained on all {len(df_clean)} rows."
        
    try:
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)
        
        metrics = {}
        if model_type == "classification":
            metrics["accuracy"] = float(accuracy_score(y_test, y_pred))
            # Binary checks for advanced metrics
            if unique_targets == 2:
                # Map potential categorical classes to 0/1 for AUC
                y_test_numeric = y_test
                if not np.issubdtype(y_test.dtype, np.number):
                    classes = sorted(y_test.unique())
                    y_test_numeric = y_test.map({classes[0]: 0, classes[1]: 1})
                    # Re-map predictions
                    y_pred_numeric = pd.Series(y_pred).map({classes[0]: 0, classes[1]: 1}).values
                else:
                    y_pred_numeric = y_pred
                
                try:
                    y_prob = clf.predict_proba(X_test)[:, 1]
                    metrics["roc_auc"] = float(roc_auc_score(y_test_numeric, y_prob))
                except Exception:
                    pass
                metrics["precision"] = float(precision_score(y_test, y_pred, average='binary', pos_label=y_test.unique()[0]))
                metrics["recall"] = float(recall_score(y_test, y_pred, average='binary', pos_label=y_test.unique()[0]))
                metrics["f1_score"] = float(f1_score(y_test, y_pred, average='binary', pos_label=y_test.unique()[0]))
        else:
            mse = mean_squared_error(y_test, y_pred)
            metrics["rmse"] = float(np.sqrt(mse))
            metrics["r2_score"] = float(r2_score(y_test, y_pred))
            
        # Get Feature Importance
        # Extract features transformed by pipeline
        feature_names = []
        feature_names.extend(numeric_features)
        
        if categorical_features:
            cat_encoder = clf.named_steps['preprocessor'].named_transformers_['cat'].named_steps['onehot']
            cat_encoded_names = cat_encoder.get_feature_names_out(categorical_features).tolist()
            feature_names.extend(cat_encoded_names)
            
        importances = clf.named_steps['classifier'].feature_importances_
        
        # Sort and return top 10
        imp_df = pd.DataFrame({'feature': feature_names, 'importance': importances})
        imp_df = imp_df.sort_values('importance', ascending=False).head(10)
        top_importances = imp_df.to_dict(orient='records')
        
        return {
            "model_type": model_type,
            "target": target_col,
            "features_used": valid_features,
            "metrics": metrics,
            "top_feature_importances": top_importances,
            "note": sampled_note
        }
    except Exception as e:
        return {"error": f"Failed to train baseline model: {str(e)}"}
