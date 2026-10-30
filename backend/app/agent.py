import json
import traceback
import httpx
from typing import Generator, Dict, Any, List
from openai import OpenAI

import app.config as config
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

# Map string tool names to Python functions
TOOLS_MAP = {
    "get_dataset_schema": get_dataset_schema,
    "get_descriptive_stats": get_descriptive_stats,
    "plot_numerical_distribution": plot_numerical_distribution,
    "plot_categorical_distribution": plot_categorical_distribution,
    "plot_bivariate_relationship": plot_bivariate_relationship,
    "plot_correlation_heatmap": plot_correlation_heatmap,
    "perform_statistical_test": perform_statistical_test,
    "train_baseline_model": train_baseline_model
}

SYSTEM_INSTRUCTION = (
    "You are AIDA, an expert Data Analysis Agent. You have access to a dataset loaded in-memory via Pandas.\n"
    "Your objective is to explore the data, answer the user's questions, run statistical tests, generate plots, "
    "and train baseline models to uncover insights.\n\n"
    "CRITICAL GUIDELINES:\n"
    "1. Always call `get_dataset_schema` first if you do not know the schema or column names of the dataset. "
    "Do not guess column names.\n"
    "2. If a tool call fails (e.g., column doesn't exist, type mismatch), read the error returned and try again. "
    "Use your self-correction ability to resolve parameter issues.\n"
    "3. When you generate a plot, the tool will return a static path like `/static/charts/dist_age.png`. "
    "Include this path in your final response using Markdown image syntax: `![Distribution of age](/static/charts/dist_age.png)` "
    "so the user can see it in their chat window.\n"
    "4. When calling a tool, ensure parameters strictly match the tool's defined schema as a single JSON object. Do not wrap parameters in a list (e.g. use `{\"column\": \"age\"}` instead of `[{\"column\": \"age\"}]`).\n"
    "5. Be thorough but concise. Walk the user through your steps and findings clearly."
)

def format_openai_tools() -> List[Dict[str, Any]]:
    """Converts tools into OpenAI function specifications for Groq."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_dataset_schema",
                "description": "Returns the schema of the loaded dataset (columns, data types, null counts, shape). Always call this first.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_descriptive_stats",
                "description": "Returns statistical summaries (mean, median, standard deviation, min, max, skew) for specified numeric columns.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of column names to summarize. If omitted, summarizes all numeric columns."
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "plot_numerical_distribution",
                "description": "Generates and saves a distribution plot (histogram + boxplot) for a numeric column.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Column name to plot"},
                        "bins": {"type": "integer", "description": "Number of histogram bins (default: 30)"}
                    },
                    "required": ["column"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "plot_categorical_distribution",
                "description": "Generates and saves a bar chart of frequency counts for a categorical/discrete column.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Column name to plot"}
                    },
                    "required": ["column"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "plot_bivariate_relationship",
                "description": "Plots relationship between two columns. Auto-detects chart type (scatter, box, bar) based on variable types.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x_col": {"type": "string", "description": "X-axis column name"},
                        "y_col": {"type": "string", "description": "Y-axis column name"},
                        "plot_type": {"type": "string", "enum": ["auto", "scatter", "box", "bar"], "description": "Type of plot (default: auto)"}
                    },
                    "required": ["x_col", "y_col"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "plot_correlation_heatmap",
                "description": "Computes correlation matrix and generates a Seaborn correlation heatmap.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional subset of numerical columns. If omitted, computes correlations for all numerical columns."
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "perform_statistical_test",
                "description": "Performs hypothesis testing (Welch's t-test, ANOVA, Pearson correlation, Chi-square) between two columns.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "col_a": {"type": "string", "description": "First column name"},
                        "col_b": {"type": "string", "description": "Second column name"},
                        "test_type": {"type": "string", "enum": ["auto", "correlation", "t-test", "anova", "chi-square"], "description": "Type of statistical test (default: auto)"}
                    },
                    "required": ["col_a", "col_b"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "train_baseline_model",
                "description": "Splits the dataset, trains a baseline Random Forest classifier or regressor on a target column, and evaluates performance.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_col": {"type": "string", "description": "Target variable column to predict"},
                        "feature_cols": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of feature columns. If omitted, uses all valid columns."
                        },
                        "model_type": {"type": "string", "enum": ["auto", "classification", "regression"], "description": "Type of model (default: auto)"}
                    },
                    "required": ["target_col"]
                }
            }
        }
    ]

def run_agent_loop(query: str) -> Generator[Dict[str, Any], None, None]:
    """
    Main generator running the ReAct agent loop using Groq.
    Yields intermediate thought steps, tool calls, tool results, and the final answer.
    """
    if state.df is None:
        yield {"type": "error", "content": "No dataset uploaded yet. Please upload a CSV first."}
        return

    if not config.GROQ_API_KEY:
        yield {"type": "error", "content": "GROQ_API_KEY is not configured in the .env file."}
        return

    try:
        # Initialize OpenAI client with Groq base URL and Groq API Key
        # Custom http_client bypasses proxy version mismatch issues in environment
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=config.GROQ_API_KEY,
            http_client=httpx.Client()
        )
        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": query}
        ]
        openai_tools = format_openai_tools()
        
        yield {"type": "info", "content": f"Starting analysis using Groq ({config.GROQ_MODEL})..."}
        
        max_iterations = 8
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            try:
                response = client.chat.completions.create(
                    model=config.GROQ_MODEL,
                    messages=messages,
                    tools=openai_tools,
                    tool_choice="auto"
                )
            except Exception as e:
                err_msg = str(e)
                # If it's a tool-calling/BadRequest parsing error, catch it and ask the LLM to self-correct
                if "tool_use_failed" in err_msg or "BadRequestError" in type(e).__name__ or "400" in err_msg:
                    yield {"type": "thought", "content": f"Warning: Groq API tool-call parsing failed. Attempting to self-correct...\nError detail: {err_msg}"}
                    messages.append({
                        "role": "user",
                        "content": (
                            f"System Error: Your last tool invocation attempt was rejected by the API server with error: '{err_msg}'.\n"
                            "Please try again. Ensure you call get_dataset_schema first to see the exact column names, "
                            "and generate parameter calls strictly as a single JSON object matching the function's schema."
                        )
                    })
                    continue
                else:
                    # Reraise other fatal errors (auth, rate limits)
                    raise e
            
            choice = response.choices[0]
            message = choice.message
            
            # Save message to history
            messages.append(message)
            
            # Yield text thought if present
            if message.content:
                yield {"type": "thought", "content": message.content}
                
            # Check if tools are called
            tool_calls = message.tool_calls
            if not tool_calls:
                # No more tools called, we have final answer
                yield {"type": "final_answer", "content": message.content or ""}
                return
                
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_id = tool_call.id
                
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                    if not isinstance(tool_args, dict):
                        tool_args = {}
                except (json.JSONDecodeError, TypeError):
                    tool_args = {}
                    
                yield {"type": "tool_call", "name": tool_name, "arguments": tool_args}
                
                # Execute tool
                if tool_name not in TOOLS_MAP:
                    result = {"error": f"Tool '{tool_name}' is not registered."}
                else:
                    try:
                        result = TOOLS_MAP[tool_name](**tool_args)
                    except Exception as e:
                        result = {"error": f"Exception executing tool: {str(e)}", "traceback": traceback.format_exc()}
                        
                yield {"type": "tool_output", "name": tool_name, "result": result}
                
                # Append tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "name": tool_name,
                    "content": json.dumps(result, default=str)
                })

        yield {"type": "error", "content": f"Agent exceeded maximum reasoning turns ({max_iterations})."}
        
    except Exception as e:
        yield {"type": "error", "content": f"Groq Loop Error: {str(e)}", "traceback": traceback.format_exc()}
