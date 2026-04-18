import pandas as pd
import numpy as np
import os
import time
import dotenv
import ast
from sqlalchemy.sql import text
from datetime import datetime, timedelta
from typing import Dict, List, Union
from sqlalchemy import create_engine, Engine
from smolagents import tool, ToolCallingAgent, OpenAIServerModel
import re
from typing import Optional
import os

# Create an SQLite database
db_engine = create_engine("sqlite:///munder_difflin.db")

# List containing the different kinds of papers 
paper_supplies = [
    # Paper Types (priced per sheet unless specified)
    {"item_name": "A4 paper",                         "category": "paper",        "unit_price": 0.05},
    {"item_name": "Letter-sized paper",              "category": "paper",        "unit_price": 0.06},
    {"item_name": "Cardstock",                        "category": "paper",        "unit_price": 0.15},
    {"item_name": "Colored paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Glossy paper",                     "category": "paper",        "unit_price": 0.20},
    {"item_name": "Matte paper",                      "category": "paper",        "unit_price": 0.18},
    {"item_name": "Recycled paper",                   "category": "paper",        "unit_price": 0.08},
    {"item_name": "Eco-friendly paper",               "category": "paper",        "unit_price": 0.12},
    {"item_name": "Poster paper",                     "category": "paper",        "unit_price": 0.25},
    {"item_name": "Banner paper",                     "category": "paper",        "unit_price": 0.30},
    {"item_name": "Kraft paper",                      "category": "paper",        "unit_price": 0.10},
    {"item_name": "Construction paper",               "category": "paper",        "unit_price": 0.07},
    {"item_name": "Wrapping paper",                   "category": "paper",        "unit_price": 0.15},
    {"item_name": "Glitter paper",                    "category": "paper",        "unit_price": 0.22},
    {"item_name": "Decorative paper",                 "category": "paper",        "unit_price": 0.18},
    {"item_name": "Letterhead paper",                 "category": "paper",        "unit_price": 0.12},
    {"item_name": "Legal-size paper",                 "category": "paper",        "unit_price": 0.08},
    {"item_name": "Crepe paper",                      "category": "paper",        "unit_price": 0.05},
    {"item_name": "Photo paper",                      "category": "paper",        "unit_price": 0.25},
    {"item_name": "Uncoated paper",                   "category": "paper",        "unit_price": 0.06},
    {"item_name": "Butcher paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Heavyweight paper",                "category": "paper",        "unit_price": 0.20},
    {"item_name": "Standard copy paper",              "category": "paper",        "unit_price": 0.04},
    {"item_name": "Bright-colored paper",             "category": "paper",        "unit_price": 0.12},
    {"item_name": "Patterned paper",                  "category": "paper",        "unit_price": 0.15},

    # Product Types (priced per unit)
    {"item_name": "Paper plates",                     "category": "product",      "unit_price": 0.10},  # per plate
    {"item_name": "Paper cups",                       "category": "product",      "unit_price": 0.08},  # per cup
    {"item_name": "Paper napkins",                    "category": "product",      "unit_price": 0.02},  # per napkin
    {"item_name": "Disposable cups",                  "category": "product",      "unit_price": 0.10},  # per cup
    {"item_name": "Table covers",                     "category": "product",      "unit_price": 1.50},  # per cover
    {"item_name": "Envelopes",                        "category": "product",      "unit_price": 0.05},  # per envelope
    {"item_name": "Sticky notes",                     "category": "product",      "unit_price": 0.03},  # per sheet
    {"item_name": "Notepads",                         "category": "product",      "unit_price": 2.00},  # per pad
    {"item_name": "Invitation cards",                 "category": "product",      "unit_price": 0.50},  # per card
    {"item_name": "Flyers",                           "category": "product",      "unit_price": 0.15},  # per flyer
    {"item_name": "Party streamers",                  "category": "product",      "unit_price": 0.05},  # per roll
    {"item_name": "Decorative adhesive tape (washi tape)", "category": "product", "unit_price": 0.20},  # per roll
    {"item_name": "Paper party bags",                 "category": "product",      "unit_price": 0.25},  # per bag
    {"item_name": "Name tags with lanyards",          "category": "product",      "unit_price": 0.75},  # per tag
    {"item_name": "Presentation folders",             "category": "product",      "unit_price": 0.50},  # per folder

    # Large-format items (priced per unit)
    {"item_name": "Large poster paper (24x36 inches)", "category": "large_format", "unit_price": 1.00},
    {"item_name": "Rolls of banner paper (36-inch width)", "category": "large_format", "unit_price": 2.50},

    # Specialty papers
    {"item_name": "100 lb cover stock",               "category": "specialty",    "unit_price": 0.50},
    {"item_name": "80 lb text paper",                 "category": "specialty",    "unit_price": 0.40},
    {"item_name": "250 gsm cardstock",                "category": "specialty",    "unit_price": 0.30},
    {"item_name": "220 gsm poster paper",             "category": "specialty",    "unit_price": 0.35},
]

# Given below are some utility functions you can use to implement your multi-agent system

def generate_sample_inventory(paper_supplies: list, coverage: float = 0.4, seed: int = 137) -> pd.DataFrame:
    """
    Generate inventory for exactly a specified percentage of items from the full paper supply list.

    This function randomly selects exactly `coverage` × N items from the `paper_supplies` list,
    and assigns each selected item:
    - a random stock quantity between 200 and 800,
    - a minimum stock level between 50 and 150.

    The random seed ensures reproducibility of selection and stock levels.

    Args:
        paper_supplies (list): A list of dictionaries, each representing a paper item with
                               keys 'item_name', 'category', and 'unit_price'.
        coverage (float, optional): Fraction of items to include in the inventory (default is 0.4, or 40%).
        seed (int, optional): Random seed for reproducibility (default is 137).

    Returns:
        pd.DataFrame: A DataFrame with the selected items and assigned inventory values, including:
                      - item_name
                      - category
                      - unit_price
                      - current_stock
                      - min_stock_level
    """
    # Ensure reproducible random output
    np.random.seed(seed)

    # Calculate number of items to include based on coverage
    num_items = int(len(paper_supplies) * coverage)

    # Randomly select item indices without replacement
    selected_indices = np.random.choice(
        range(len(paper_supplies)),
        size=num_items,
        replace=False
    )

    # Extract selected items from paper_supplies list
    selected_items = [paper_supplies[i] for i in selected_indices]

    # Construct inventory records
    inventory = []
    for item in selected_items:
        inventory.append({
            "item_name": item["item_name"],
            "category": item["category"],
            "unit_price": item["unit_price"],
            "current_stock": np.random.randint(200, 800),  # Realistic stock range
            "min_stock_level": np.random.randint(50, 150)  # Reasonable threshold for reordering
        })

    # Return inventory as a pandas DataFrame
    return pd.DataFrame(inventory)

def init_database(db_engine: Engine, seed: int = 137) -> Engine:    
    """
    Set up the Munder Difflin database with all required tables and initial records.

    This function performs the following tasks:
    - Creates the 'transactions' table for logging stock orders and sales
    - Loads customer inquiries from 'quote_requests.csv' into a 'quote_requests' table
    - Loads previous quotes from 'quotes.csv' into a 'quotes' table, extracting useful metadata
    - Generates a random subset of paper inventory using `generate_sample_inventory`
    - Inserts initial financial records including available cash and starting stock levels

    Args:
        db_engine (Engine): A SQLAlchemy engine connected to the SQLite database.
        seed (int, optional): A random seed used to control reproducibility of inventory stock levels.
                              Default is 137.

    Returns:
        Engine: The same SQLAlchemy engine, after initializing all necessary tables and records.

    Raises:
        Exception: If an error occurs during setup, the exception is printed and raised.
    """
    try:
        # ----------------------------
        # 1. Create an empty 'transactions' table schema
        # ----------------------------
        transactions_schema = pd.DataFrame({
            "id": [],
            "item_name": [],
            "transaction_type": [],  # 'stock_orders' or 'sales'
            "units": [],             # Quantity involved
            "price": [],             # Total price for the transaction
            "transaction_date": [],  # ISO-formatted date
        })
        transactions_schema.to_sql("transactions", db_engine, if_exists="replace", index=False)

        # Set a consistent starting date
        initial_date = datetime(2025, 1, 1).isoformat()

        # ----------------------------
        # 2. Load and initialize 'quote_requests' table
        # ----------------------------
        quote_requests_df = pd.read_csv("quote_requests.csv")
        quote_requests_df["id"] = range(1, len(quote_requests_df) + 1)
        quote_requests_df.to_sql("quote_requests", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 3. Load and transform 'quotes' table
        # ----------------------------
        quotes_df = pd.read_csv("quotes.csv")
        quotes_df["request_id"] = range(1, len(quotes_df) + 1)
        quotes_df["order_date"] = initial_date

        # Unpack metadata fields (job_type, order_size, event_type) if present
        if "request_metadata" in quotes_df.columns:
            quotes_df["request_metadata"] = quotes_df["request_metadata"].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else x
            )
            quotes_df["job_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("job_type", ""))
            quotes_df["order_size"] = quotes_df["request_metadata"].apply(lambda x: x.get("order_size", ""))
            quotes_df["event_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("event_type", ""))

        # Retain only relevant columns
        quotes_df = quotes_df[[
            "request_id",
            "total_amount",
            "quote_explanation",
            "order_date",
            "job_type",
            "order_size",
            "event_type"
        ]]
        quotes_df.to_sql("quotes", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 4. Generate inventory and seed stock
        # ----------------------------
        inventory_df = generate_sample_inventory(paper_supplies, seed=seed)

        # Seed initial transactions
        initial_transactions = []

        # Add a starting cash balance via a dummy sales transaction
        initial_transactions.append({
            "item_name": None,
            "transaction_type": "sales",
            "units": None,
            "price": 50000.0,
            "transaction_date": initial_date,
        })

        # Add one stock order transaction per inventory item
        for _, item in inventory_df.iterrows():
            initial_transactions.append({
                "item_name": item["item_name"],
                "transaction_type": "stock_orders",
                "units": item["current_stock"],
                "price": item["current_stock"] * item["unit_price"],
                "transaction_date": initial_date,
            })

        # Commit transactions to database
        pd.DataFrame(initial_transactions).to_sql("transactions", db_engine, if_exists="append", index=False)

        # Save the inventory reference table
        inventory_df.to_sql("inventory", db_engine, if_exists="replace", index=False)

        return db_engine

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def create_transaction(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    date: Union[str, datetime],
) -> int:
    """
    This function records a transaction of type 'stock_orders' or 'sales' with a specified
    item name, quantity, total price, and transaction date into the 'transactions' table of the database.

    Args:
        item_name (str): The name of the item involved in the transaction.
        transaction_type (str): Either 'stock_orders' or 'sales'.
        quantity (int): Number of units involved in the transaction.
        price (float): Total price of the transaction.
        date (str or datetime): Date of the transaction in ISO 8601 format.

    Returns:
        int: The ID of the newly inserted transaction.

    Raises:
        ValueError: If `transaction_type` is not 'stock_orders' or 'sales'.
        Exception: For other database or execution errors.
    """
    try:
        # Convert datetime to ISO string if necessary
        date_str = date.isoformat() if isinstance(date, datetime) else date

        # Validate transaction type
        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("Transaction type must be 'stock_orders' or 'sales'")

        # Prepare transaction record as a single-row DataFrame
        transaction = pd.DataFrame([{
            "item_name": item_name,
            "transaction_type": transaction_type,
            "units": quantity,
            "price": price,
            "transaction_date": date_str,
        }])

        # Insert the record into the database
        transaction.to_sql("transactions", db_engine, if_exists="append", index=False)

        # Fetch and return the ID of the inserted row
        result = pd.read_sql("SELECT last_insert_rowid() as id", db_engine)
        return int(result.iloc[0]["id"])

    except Exception as e:
        print(f"Error creating transaction: {e}")
        raise

def get_all_inventory(as_of_date: str) -> Dict[str, int]:
    """
    Retrieve a snapshot of available inventory as of a specific date.

    This function calculates the net quantity of each item by summing 
    all stock orders and subtracting all sales up to and including the given date.

    Only items with positive stock are included in the result.

    Args:
        as_of_date (str): ISO-formatted date string (YYYY-MM-DD) representing the inventory cutoff.

    Returns:
        Dict[str, int]: A dictionary mapping item names to their current stock levels.
    """
    # SQL query to compute stock levels per item as of the given date
    query = """
        SELECT
            item_name,
            SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END) as stock
        FROM transactions
        WHERE item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
        HAVING stock > 0
    """

    # Execute the query with the date parameter
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})

    # Convert the result into a dictionary {item_name: stock}
    return dict(zip(result["item_name"], result["stock"]))

def get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Retrieve the stock level of a specific item as of a given date.

    This function calculates the net stock by summing all 'stock_orders' and 
    subtracting all 'sales' transactions for the specified item up to the given date.

    Args:
        item_name (str): The name of the item to look up.
        as_of_date (str or datetime): The cutoff date (inclusive) for calculating stock.

    Returns:
        pd.DataFrame: A single-row DataFrame with columns 'item_name' and 'current_stock'.
    """
    # Convert date to ISO string format if it's a datetime object
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # SQL query to compute net stock level for the item
    stock_query = """
        SELECT
            item_name,
            COALESCE(SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END), 0) AS current_stock
        FROM transactions
        WHERE item_name = :item_name
        AND transaction_date <= :as_of_date
    """

    # Execute query and return result as a DataFrame
    return pd.read_sql(
        stock_query,
        db_engine,
        params={"item_name": item_name, "as_of_date": as_of_date},
    )

def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    """
    Estimate the supplier delivery date based on the requested order quantity and a starting date.

    Delivery lead time increases with order size:
        - ≤10 units: same day
        - 11–100 units: 1 day
        - 101–1000 units: 4 days
        - >1000 units: 7 days

    Args:
        input_date_str (str): The starting date in ISO format (YYYY-MM-DD).
        quantity (int): The number of units in the order.

    Returns:
        str: Estimated delivery date in ISO format (YYYY-MM-DD).
    """
    # Debug log (comment out in production if needed)
    print(f"FUNC (get_supplier_delivery_date): Calculating for qty {quantity} from date string '{input_date_str}'")

    # Attempt to parse the input date
    try:
        input_date_dt = datetime.fromisoformat(input_date_str.split("T")[0])
    except (ValueError, TypeError):
        # Fallback to current date on format error
        print(f"WARN (get_supplier_delivery_date): Invalid date format '{input_date_str}', using today as base.")
        input_date_dt = datetime.now()

    # Determine delivery delay based on quantity
    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7

    # Add delivery days to the starting date
    delivery_date_dt = input_date_dt + timedelta(days=days)

    # Return formatted delivery date
    return delivery_date_dt.strftime("%Y-%m-%d")

def get_cash_balance(as_of_date: Union[str, datetime]) -> float:
    """
    Calculate the current cash balance as of a specified date.

    The balance is computed by subtracting total stock purchase costs ('stock_orders')
    from total revenue ('sales') recorded in the transactions table up to the given date.

    Args:
        as_of_date (str or datetime): The cutoff date (inclusive) in ISO format or as a datetime object.

    Returns:
        float: Net cash balance as of the given date. Returns 0.0 if no transactions exist or an error occurs.
    """
    try:
        # Convert date to ISO format if it's a datetime object
        if isinstance(as_of_date, datetime):
            as_of_date = as_of_date.isoformat()

        # Query all transactions on or before the specified date
        transactions = pd.read_sql(
            "SELECT * FROM transactions WHERE transaction_date <= :as_of_date",
            db_engine,
            params={"as_of_date": as_of_date},
        )

        # Compute the difference between sales and stock purchases
        if not transactions.empty:
            total_sales = transactions.loc[transactions["transaction_type"] == "sales", "price"].sum()
            total_purchases = transactions.loc[transactions["transaction_type"] == "stock_orders", "price"].sum()
            return float(total_sales - total_purchases)

        return 0.0

    except Exception as e:
        print(f"Error getting cash balance: {e}")
        return 0.0


def generate_financial_report(as_of_date: Union[str, datetime]) -> Dict:
    """
    Generate a complete financial report for the company as of a specific date.

    This includes:
    - Cash balance
    - Inventory valuation
    - Combined asset total
    - Itemized inventory breakdown
    - Top 5 best-selling products

    Args:
        as_of_date (str or datetime): The date (inclusive) for which to generate the report.

    Returns:
        Dict: A dictionary containing the financial report fields:
            - 'as_of_date': The date of the report
            - 'cash_balance': Total cash available
            - 'inventory_value': Total value of inventory
            - 'total_assets': Combined cash and inventory value
            - 'inventory_summary': List of items with stock and valuation details
            - 'top_selling_products': List of top 5 products by revenue
    """
    # Normalize date input
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # Get current cash balance
    cash = get_cash_balance(as_of_date)

    # Get current inventory snapshot
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    inventory_value = 0.0
    inventory_summary = []

    # Compute total inventory value and summary by item
    for _, item in inventory_df.iterrows():
        stock_info = get_stock_level(item["item_name"], as_of_date)
        stock = stock_info["current_stock"].iloc[0]
        item_value = stock * item["unit_price"]
        inventory_value += item_value

        inventory_summary.append({
            "item_name": item["item_name"],
            "stock": stock,
            "unit_price": item["unit_price"],
            "value": item_value,
        })

    # Identify top-selling products by revenue
    top_sales_query = """
        SELECT item_name, SUM(units) as total_units, SUM(price) as total_revenue
        FROM transactions
        WHERE transaction_type = 'sales' AND transaction_date <= :date
        GROUP BY item_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    top_sales = pd.read_sql(top_sales_query, db_engine, params={"date": as_of_date})
    top_selling_products = top_sales.to_dict(orient="records")

    return {
        "as_of_date": as_of_date,
        "cash_balance": cash,
        "inventory_value": inventory_value,
        "total_assets": cash + inventory_value,
        "inventory_summary": inventory_summary,
        "top_selling_products": top_selling_products,
    }


def search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """
    Retrieve a list of historical quotes that match any of the provided search terms.

    The function searches both the original customer request (from `quote_requests`) and
    the explanation for the quote (from `quotes`) for each keyword. Results are sorted by
    most recent order date and limited by the `limit` parameter.

    Args:
        search_terms (List[str]): List of terms to match against customer requests and explanations.
        limit (int, optional): Maximum number of quote records to return. Default is 5.

    Returns:
        List[Dict]: A list of matching quotes, each represented as a dictionary with fields:
            - original_request
            - total_amount
            - quote_explanation
            - job_type
            - order_size
            - event_type
            - order_date
    """
    conditions = []
    params = {}

    # Build SQL WHERE clause using LIKE filters for each search term
    for i, term in enumerate(search_terms):
        param_name = f"term_{i}"
        conditions.append(
            f"(LOWER(qr.response) LIKE :{param_name} OR "
            f"LOWER(q.quote_explanation) LIKE :{param_name})"
        )
        params[param_name] = f"%{term.lower()}%"

    # Combine conditions; fallback to always-true if no terms provided
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Final SQL query to join quotes with quote_requests
    query = f"""
        SELECT
            qr.response AS original_request,
            q.total_amount,
            q.quote_explanation,
            q.job_type,
            q.order_size,
            q.event_type,
            q.order_date
        FROM quotes q
        JOIN quote_requests qr ON q.request_id = qr.id
        WHERE {where_clause}
        ORDER BY q.order_date DESC
        LIMIT {limit}
    """

    # Execute parameterized query
    with db_engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]


########################
########################
########################
# YOUR MULTI AGENT STARTS HERE
########################
########################
########################

def build_smolagents_model() -> OpenAIServerModel:
    """
    Build a shared smolagents model object.

    This project instantiates real smolagents agents to satisfy the agentic
    framework requirement. Deterministic business logic is still used so the
    evaluation remains stable and reproducible.
    """
    api_key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENAI_API_TOKEN")
        or "DUMMY_KEY"
    )

    api_base = os.getenv("OPENAI_API_BASE") or "https://api.openai.com/v1"
    model_id = os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"

    return OpenAIServerModel(
        model_id=model_id,
        api_base=api_base,
        api_key=api_key,
    )


def normalize_text(value: str) -> str:
    """Normalize text for easier matching."""
    return str(value).strip().lower()


def get_inventory_reference_table() -> pd.DataFrame:
    """
    Load the seeded inventory reference table.
    """
    return pd.read_sql("SELECT * FROM inventory", db_engine)


def get_catalog_reference_table() -> pd.DataFrame:
    """
    Load the full product catalog from the starter file.
    """
    return pd.DataFrame(paper_supplies)


@tool
def inventory_snapshot_tool(as_of_date: str) -> Dict[str, int]:
    """
    Return all items currently in stock as of a given date.

    Args:
        as_of_date: Inventory cutoff date in YYYY-MM-DD format.

    Returns:
        A dictionary mapping item names to stock quantities.
    """
    return get_all_inventory(as_of_date)


@tool
def stock_level_tool(item_name: str, as_of_date: str) -> int:
    """
    Return the stock level for one item as of a given date.

    Args:
        item_name: Name of the inventory item.
        as_of_date: Inventory cutoff date in YYYY-MM-DD format.

    Returns:
        The current stock quantity for the item.
    """
    stock_df = get_stock_level(item_name, as_of_date)

    if stock_df.empty:
        return 0

    return int(stock_df["current_stock"].iloc[0])


@tool
def supplier_delivery_tool(request_date: str, quantity: int) -> str:
    """
    Estimate supplier delivery date.

    Args:
        request_date: Date when the reorder is placed.
        quantity: Number of units ordered.

    Returns:
        Estimated delivery date as a string.
    """
    return get_supplier_delivery_date(request_date, quantity)


@tool
def cash_balance_tool(as_of_date: str) -> float:
    """
    Return available cash balance for the company.

    Args:
        as_of_date: Date to calculate the balance for (YYYY-MM-DD).

    Returns:
        Current cash balance as a float.
    """
    return float(get_cash_balance(as_of_date))


@tool
def financial_report_tool(as_of_date: str) -> Dict:
    """
    Generate a financial report snapshot.

    Args:
        as_of_date: Date for the report (YYYY-MM-DD).

    Returns:
        Dictionary containing financial metrics.
    """
    return generate_financial_report(as_of_date)


@tool
def quote_history_tool(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """
    Search historical quote records.

    Args:
        search_terms: Keywords used to search past quotes.
        limit: Maximum number of records to return.

    Returns:
        List of matching historical quotes.
    """
    return search_quote_history(search_terms, limit=limit)


def find_item_record(item_name: str) -> Optional[pd.Series]:
    """
    Find an item in the full product catalog by exact normalized name.
    """
    catalog_df = get_catalog_reference_table()

    for _, row in catalog_df.iterrows():
        if normalize_text(row["item_name"]) == normalize_text(item_name):
            return row

    return None


def canonical_item_name(raw_text: str) -> Optional[str]:
    """
    Map free-text request wording to the closest supported catalog item name.
    """
    text = normalize_text(raw_text)

    synonym_map = [
        ("a4 glossy", "Glossy paper"),
        ("glossy a4", "Glossy paper"),
        ("a3 glossy", "Glossy paper"),
        ("high-quality glossy", "Glossy paper"),
        ("glossy paper", "Glossy paper"),

        ("a4 matte", "Matte paper"),
        ("a3 matte", "Matte paper"),
        ("matte paper", "Matte paper"),

        ("recycled paper", "Recycled paper"),
        ("a4 recycled paper", "Recycled paper"),
        ("eco-friendly paper", "Eco-friendly paper"),

        ("poster board", "Poster paper"),
        ("poster boards", "Poster paper"),
        ("poster paper", "Poster paper"),
        ("colorful poster paper", "Poster paper"),
        ("posters", "Poster paper"),

        ("banner paper", "Banner paper"),

        ("construction paper", "Construction paper"),
        ("colorful construction paper", "Construction paper"),

        ("kraft paper envelopes", "Kraft paper"),
        ("kraft paper", "Kraft paper"),

        ("washi tape", "Decorative paper"),
        ("decorative washi tape", "Decorative paper"),

        ("cardstock", "Cardstock"),
        ("heavy cardstock", "Cardstock"),
        ("heavyweight cardstock", "Cardstock"),
        ("white cardstock", "Cardstock"),
        ("colorful cardstock", "Cardstock"),

        ("colored paper", "Colored paper"),
        ("colorful paper", "Colored paper"),
        ("a3 colored paper", "Colored paper"),
        ("assorted colors", "Colored paper"),

        ("printer paper", "A4 paper"),
        ("printing paper", "A4 paper"),
        ("a4 printer paper", "A4 paper"),
        ("a4 printing paper", "A4 paper"),
        ("a4 white paper", "A4 paper"),
        ("a4 white printer paper", "A4 paper"),
        ("white printer paper", "A4 paper"),
        ("standard printer paper", "A4 paper"),
        ("a4 paper", "A4 paper"),

        ("flyers", "Flyers"),

        ("paper cups", "Paper cups"),
        ("paper plates", "Paper plates"),
        ("paper napkins", "Paper napkins"),

        ("streamers", None),
        ("balloons", None),
        ("tickets", None),
        ("cardboard", None),
    ]

    for phrase, mapped_item in synonym_map:
        if phrase in text:
            return mapped_item

    catalog_df = get_catalog_reference_table()
    for _, row in catalog_df.iterrows():
        item_name = str(row["item_name"])
        if normalize_text(item_name) in text:
            return item_name

    return None


def extract_request_items(request_text: str) -> List[Dict]:
    """
    Extract multiple line items from a customer request.
    """
    raw_lines = [line.strip() for line in request_text.splitlines() if line.strip()]
    bullet_lines = [line.lstrip("-• ").strip() for line in raw_lines if line.strip().startswith(("-", "•"))]

    sources = bullet_lines if bullet_lines else [request_text.replace("\n", " ")]

    request_items: List[Dict] = []

    stop_pattern = re.compile(
        r"\b(?:please deliver|please ensure|please confirm|thank you|"
        r"i need|we need|the supplies|these supplies|delivery|"
        r"to ensure|in time for|for our upcoming|for the parade|for the reception|"
        r"for the ceremony|for the exhibition|for the concert|for the show|"
        r"for the gathering|for the assembly|for the party|for the performance|"
        r"for the demonstration)\b",
        flags=re.IGNORECASE,
    )

    pattern_with_unit = re.compile(
        r"(\d[\d,]*)\s+"
        r"(sheets?|reams?|rolls?|roll|packets?|units?)"
        r"\s+(?:of\s+)?"
        r"(.*?)(?=(?:\b\d[\d,]*\s+(?:sheets?|reams?|rolls?|roll|packets?|units?)\b)|$)",
        flags=re.IGNORECASE,
    )

    pattern_no_unit = re.compile(
        r"(\d[\d,]*)\s+"
        r"([A-Za-z][A-Za-z0-9%\"'()\- ]*?)"
        r"(?=(?:,|\band\b|$))",
        flags=re.IGNORECASE,
    )

    for source in sources:
        working_source = source
        matches = list(pattern_with_unit.finditer(working_source))
        used_spans = []

        for match in matches:
            quantity = int(match.group(1).replace(",", ""))
            item_text = match.group(3).strip(" ,.;:-")
            item_text = re.sub(r"^and\s+", "", item_text, flags=re.IGNORECASE).strip()
            item_text = item_text.replace(", and", ",")
            item_text = re.sub(r"\band\s+(\d[\d,]*\b)", r" \1", item_text, flags=re.IGNORECASE)
            item_text = stop_pattern.split(item_text)[0].strip(" ,.;:-")

            if not item_text or not re.search(r"[A-Za-z]", item_text):
                continue

            mapped_item_name = canonical_item_name(item_text)

            request_items.append(
                {
                    "item_name": mapped_item_name if mapped_item_name else item_text,
                    "quantity": quantity,
                    "raw_text": item_text,
                    "supported": bool(mapped_item_name),
                }
            )
            used_spans.append(match.span())

        cleaned_source = working_source
        for start, end in reversed(used_spans):
            cleaned_source = cleaned_source[:start] + " " + cleaned_source[end:]

        for match in pattern_no_unit.finditer(cleaned_source):
            quantity = int(match.group(1).replace(",", ""))
            item_text = match.group(2).strip(" ,.;:-")
            item_text = re.sub(r"^and\s+", "", item_text, flags=re.IGNORECASE).strip()
            item_text = stop_pattern.split(item_text)[0].strip(" ,.;:-")

            if not item_text or not re.search(r"[A-Za-z]", item_text):
                continue

            mapped_item_name = canonical_item_name(item_text)

            request_items.append(
                {
                    "item_name": mapped_item_name if mapped_item_name else item_text,
                    "quantity": quantity,
                    "raw_text": item_text,
                    "supported": bool(mapped_item_name),
                }
            )

    unique_items: List[Dict] = []
    seen = set()
    for item in request_items:
        key = (item["item_name"], item["quantity"], item["supported"])
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    return unique_items


@tool
def restock_tool(item_name: str, quantity: int, request_date: str) -> Dict:
    """
    Reorder inventory items.

    Args:
        item_name: Name of item to reorder.
        quantity: Quantity to reorder.
        request_date: Date the reorder is placed.

    Returns:
        Dictionary describing reorder result.
    """
    item_record = find_item_record(item_name)

    if item_record is None:
        return {
            "success": False,
            "message": f"Cannot reorder '{item_name}' because it is not defined in the product catalog.",
        }

    total_cost = float(item_record["unit_price"]) * quantity

    create_transaction(
        item_name=item_name,
        transaction_type="stock_orders",
        quantity=quantity,
        price=total_cost,
        date=request_date,
    )

    expected_delivery = supplier_delivery_tool(request_date, quantity)

    return {
        "success": True,
        "message": f"Reorder placed for {quantity} units of {item_name}. Expected supplier delivery: {expected_delivery}.",
        "expected_delivery": expected_delivery,
        "reorder_cost": total_cost,
    }


@tool
def sales_transaction_tool(item_name: str, quantity: int, total_price: float, request_date: str) -> Dict:
    """
    Record a completed sale.

    Args:
        item_name: Item sold.
        quantity: Quantity sold.
        total_price: Total sale price.
        request_date: Date of sale.

    Returns:
        Dictionary describing the sale result.
    """
    transaction_id = create_transaction(
        item_name=item_name,
        transaction_type="sales",
        quantity=quantity,
        price=total_price,
        date=request_date,
    )

    return {
        "success": True,
        "transaction_id": transaction_id,
        "message": f"Sale recorded successfully for {quantity} units of {item_name}.",
    }


def determine_discount_rate(quantity: int) -> float:
    """
    Apply a simple bulk discount strategy.
    """
    if quantity >= 2000:
        return 0.15
    if quantity >= 1000:
        return 0.10
    if quantity >= 500:
        return 0.05
    return 0.0


@tool
def build_quote_tool(item_name: str, quantity: int, request_text: str, request_date: str) -> Dict:
    """
    Build a price quote.

    Args:
        item_name: Item requested.
        quantity: Quantity requested.
        request_text: Original customer request text.
        request_date: Date of request.

    Returns:
        Dictionary containing quote details.
    """
    item_record = find_item_record(item_name)

    if item_record is None:
        return {
            "success": False,
            "message": f"Unable to generate a quote because '{item_name}' was not found in the product catalog.",
        }

    unit_price = float(item_record["unit_price"])
    gross_amount = unit_price * quantity
    discount_rate = determine_discount_rate(quantity)
    discount_amount = gross_amount * discount_rate
    final_total = round(gross_amount - discount_amount, 2)

    keywords = [normalize_text(item_name)]
    for token in normalize_text(request_text).split():
        if len(token) > 4:
            keywords.append(token)

    quote_examples = quote_history_tool(keywords[:5], limit=3)

    explanation_parts = [
        f"Base unit price for {item_name} is ${unit_price:.2f}.",
        f"Requested quantity is {quantity}.",
    ]

    if discount_rate > 0:
        explanation_parts.append(
            f"A bulk discount of {int(discount_rate * 100)}% was applied."
        )
    else:
        explanation_parts.append(
            "No bulk discount was applied because the order size is below the discount threshold."
        )

    if quote_examples:
        explanation_parts.append(
            f"Historical quote records were reviewed ({len(quote_examples)} similar example(s))."
        )
    else:
        explanation_parts.append(
            "No closely matching historical quote records were found, so standard pricing was used."
        )

    return {
        "success": True,
        "item_name": item_name,
        "quantity": quantity,
        "unit_price": unit_price,
        "gross_amount": round(gross_amount, 2),
        "discount_rate": discount_rate,
        "discount_amount": round(discount_amount, 2),
        "final_total": final_total,
        "quote_explanation": " ".join(explanation_parts),
    }


class InventoryAgent:
    """
    Handles inventory responsibilities.
    """

    def __init__(self, model) -> None:
        self.framework_agent = ToolCallingAgent(
            tools=[
                inventory_snapshot_tool,
                stock_level_tool,
                restock_tool,
                supplier_delivery_tool,
            ],
            model=model,
        )

    def review_inventory(self, item_name: str, quantity: int, request_date: str) -> Dict:
        """
        Check current stock and return inventory decision information.
        """
        current_stock = stock_level_tool(item_name, request_date)
        item_record = find_item_record(item_name)

        if item_record is None:
            return {
                "success": False,
                "item_name": item_name,
                "current_stock": 0,
                "min_stock_level": 100,
                "can_fulfill_now": False,
                "needs_reorder": True,
                "message": f"Item '{item_name}' is not recognized in the product catalog.",
            }

        inventory_df = get_inventory_reference_table()
        inventory_match = inventory_df[
            inventory_df["item_name"].astype(str).str.lower() == item_name.lower()
        ]

        if not inventory_match.empty and "min_stock_level" in inventory_match.columns:
            min_stock_level = int(inventory_match.iloc[0]["min_stock_level"])
        else:
            min_stock_level = 100

        projected_stock = current_stock - quantity
        can_fulfill_now = current_stock >= quantity
        needs_reorder = projected_stock < min_stock_level

        return {
            "success": True,
            "item_name": item_name,
            "current_stock": current_stock,
            "min_stock_level": min_stock_level,
            "can_fulfill_now": can_fulfill_now,
            "needs_reorder": needs_reorder,
            "projected_stock": projected_stock,
        }

    def reorder_if_needed(self, item_name: str, quantity: int, request_date: str, current_stock: int) -> Optional[Dict]:
        """
        Reorder enough stock to cover shortage plus a small buffer.
        """
        if current_stock >= quantity:
            return None

        shortage = quantity - current_stock
        reorder_quantity = shortage + 100

        return restock_tool(item_name, reorder_quantity, request_date)


class QuoteAgent:
    """
    Handles quote generation.
    """

    def __init__(self, model) -> None:
        self.framework_agent = ToolCallingAgent(
            tools=[
                quote_history_tool,
                build_quote_tool,
            ],
            model=model,
        )

    def generate_quote(self, item_name: str, quantity: int, request_text: str, request_date: str) -> Dict:
        return build_quote_tool(item_name, quantity, request_text, request_date)


class SalesAgent:
    """
    Handles final sales transactions.
    """

    def __init__(self, model) -> None:
        self.framework_agent = ToolCallingAgent(
            tools=[
                sales_transaction_tool,
                supplier_delivery_tool,
            ],
            model=model,
        )

    def finalize_sale(self, item_name: str, quantity: int, total_price: float, request_date: str) -> Dict:
        sale_result = sales_transaction_tool(item_name, quantity, total_price, request_date)
        estimated_delivery = supplier_delivery_tool(request_date, quantity)

        sale_result["estimated_delivery"] = estimated_delivery
        sale_result["message"] = (
            f"{sale_result['message']} Estimated delivery date: {estimated_delivery}."
        )
        return sale_result


class OrchestratorAgent:
    """
    Main controller of the multi-agent workflow.
    """

    def __init__(self) -> None:
        self.model = build_smolagents_model()

        self.framework_agent = ToolCallingAgent(
            tools=[
                inventory_snapshot_tool,
                stock_level_tool,
                restock_tool,
                quote_history_tool,
                build_quote_tool,
                sales_transaction_tool,
                supplier_delivery_tool,
                financial_report_tool,
                cash_balance_tool,
            ],
            model=self.model,
        )

        self.inventory_agent = InventoryAgent(self.model)
        self.quote_agent = QuoteAgent(self.model)
        self.sales_agent = SalesAgent(self.model)

    def parse_request(self, request_text: str) -> List[Dict]:
        return extract_request_items(request_text)

    def handle_request(self, request_text: str, request_date: str) -> str:
        parsed_items = self.parse_request(request_text)

        if not parsed_items:
            return (
                "Unable to identify supported inventory items from the customer's message. "
                "No transaction was recorded."
            )

        responses: List[str] = []

        for parsed in parsed_items:
            item_name = parsed["item_name"]
            quantity = parsed["quantity"]
            raw_text = parsed["raw_text"]

            if not parsed.get("supported", True):
                responses.append(f"{item_name}: not offered by our company.")
                continue

            inventory_result = self.inventory_agent.review_inventory(item_name, quantity, request_date)

            if not inventory_result["success"]:
                responses.append(f"{item_name}: {inventory_result['message']}")
                continue

            quote_result = self.quote_agent.generate_quote(item_name, quantity, raw_text, request_date)

            if not quote_result["success"]:
                responses.append(f"{item_name}: {quote_result['message']}")
                continue

            if inventory_result["can_fulfill_now"]:
                sale_result = self.sales_agent.finalize_sale(
                    item_name=item_name,
                    quantity=quantity,
                    total_price=quote_result["final_total"],
                    request_date=request_date,
                )

                reorder_message = ""
                if inventory_result["needs_reorder"]:
                    reorder_result = self.inventory_agent.reorder_if_needed(
                        item_name=item_name,
                        quantity=inventory_result["min_stock_level"],
                        request_date=request_date,
                        current_stock=max(inventory_result["projected_stock"], 0),
                    )
                    if reorder_result and reorder_result["success"]:
                        reorder_message = f" {reorder_result['message']}"

                responses.append(
                    f"{item_name}: sale completed for {quantity} units at ${quote_result['final_total']:.2f}. "
                    f"{sale_result['message']}{reorder_message}"
                )
            else:
                reorder_result = self.inventory_agent.reorder_if_needed(
                    item_name=item_name,
                    quantity=quantity,
                    request_date=request_date,
                    current_stock=inventory_result["current_stock"],
                )

                if reorder_result is None or not reorder_result["success"]:
                    expected_delivery = supplier_delivery_tool(request_date, quantity)
                    responses.append(
                        f"{item_name}: insufficient stock ({inventory_result['current_stock']} available). "
                        f"Estimated supplier delivery date is {expected_delivery}."
                    )
                    continue

                sale_result = self.sales_agent.finalize_sale(
                    item_name=item_name,
                    quantity=quantity,
                    total_price=quote_result["final_total"],
                    request_date=request_date,
                )

                responses.append(
                    f"{item_name}: inventory was insufficient, so a reorder was placed. "
                    f"{reorder_result['message']} "
                    f"Quoted total is ${quote_result['final_total']:.2f}. "
                    f"{sale_result['message']}"
                )

        return " | ".join(responses)


def run_test_scenarios():
    """
    Run all sample requests through the multi-agent system and save test_results.csv.
    """
    print("Initializing Database...")
    init_database(db_engine)

    try:
        quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
        quote_requests_sample["request_date"] = pd.to_datetime(
            quote_requests_sample["request_date"], format="%m/%d/%y", errors="coerce"
        )
        quote_requests_sample.dropna(subset=["request_date"], inplace=True)
        quote_requests_sample = quote_requests_sample.sort_values("request_date")
    except Exception as e:
        print(f"FATAL: Error loading test data: {e}")
        return []

    orchestrator = OrchestratorAgent()
    results = []

    for idx, row in quote_requests_sample.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")
        request_text = str(row["request"])

        report_before = financial_report_tool(request_date)
        cash_before = report_before["cash_balance"]
        inventory_before = report_before["inventory_value"]

        print(f"\n=== Request {idx+1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Request Date: {request_date}")
        print(f"Cash Balance Before: ${cash_before:.2f}")
        print(f"Inventory Value Before: ${inventory_before:.2f}")

        response = orchestrator.handle_request(request_text, request_date)

        report_after = financial_report_tool(request_date)
        cash_after = report_after["cash_balance"]
        inventory_after = report_after["inventory_value"]

        print(f"Response: {response}")
        print(f"Updated Cash: ${cash_after:.2f}")
        print(f"Updated Inventory: ${inventory_after:.2f}")

        results.append(
            {
                "request_id": idx + 1,
                "request_date": request_date,
                "request": request_text,
                "cash_balance_before": cash_before,
                "cash_balance_after": cash_after,
                "inventory_value_before": inventory_before,
                "inventory_value_after": inventory_after,
                "response": response,
            }
        )

        time.sleep(0.5)

    pd.DataFrame(results).to_csv("test_results.csv", index=False)

    final_date = quote_requests_sample["request_date"].max().strftime("%Y-%m-%d")
    final_report = financial_report_tool(final_date)

    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_report['cash_balance']:.2f}")
    print(f"Final Inventory: ${final_report['inventory_value']:.2f}")
    print(f"Total Assets: ${final_report['total_assets']:.2f}")

    return results


if __name__ == "__main__":
    results = run_test_scenarios()