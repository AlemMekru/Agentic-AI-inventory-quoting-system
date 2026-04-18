# Beaver’s Choice Paper Company Multi-Agent System Report

## 1. System Overview

I implemented a multi-agent inventory, quoting, and sales workflow for Beaver’s Choice Paper Company. The final system uses the **smolagents** framework through framework-registered tools (`@tool`) while preserving separate responsibilities for orchestration, inventory, quoting, and sales.

The system contains four agents:

1. **Orchestrator Agent**  
   Receives customer requests, parses requested items and quantities, delegates work to worker agents, and combines the final customer-facing response.

2. **Inventory Agent**  
   Checks stock levels, determines whether an order can be fulfilled immediately, and decides when a reorder is required.

3. **Quote Agent**  
   Builds quotes using catalog pricing, bulk discount rules, and historical quote context.

4. **Sales Agent**  
   Records sales transactions and returns delivery timeline information.

The agents use tools backed by the helper functions in `project_starter.py`, which interact with the SQLite database.

---

## 2. Workflow Design

The workflow begins when a customer request is received by the Orchestrator Agent. The request is parsed into one or more line items. For each supported line item, the Inventory Agent checks stock and decides whether fulfillment can happen immediately or whether a reorder is required. The Quote Agent then generates a quote using pricing and discount logic. Finally, the Sales Agent records the sale and provides an estimated delivery date.

If a requested item is not supported by the company catalog, the system returns a clear customer-facing message explaining that the item is not offered.

---

## 3. Use of Starter Helper Functions

The solution uses the required helper functions from `project_starter.py`, including:

- `create_transaction()`
- `get_all_inventory()`
- `get_stock_level()`
- `get_supplier_delivery_date()`
- `get_cash_balance()`
- `generate_financial_report()`
- `search_quote_history()`

These functions are wrapped as framework tools and then used by the agents.

---

## 4. Evaluation Results

The system was evaluated using `quote_requests_sample.csv`, and the execution generated `test_results.csv`.

The evaluation demonstrates that the system:
- processes multi-item requests,
- fulfills supported requests,
- places reorders when inventory is insufficient,
- records sales transactions,
- changes financial state over time,
- reports unsupported items clearly.

### Concrete examples from `test_results.csv`

- **Request 1** was fully fulfilled across three supported items: Glossy paper, Cardstock, and Colored paper. The cash balance increased from **$45059.70** to **$45124.70**, showing successful order completion and sales recording.

- **Request 2** showed a mixed outcome. Poster paper was successfully quoted and fulfilled through reorder logic, while unsupported party items were reported as not offered by the company. This demonstrates partial fulfillment with a clear reason.

- **Request 7** demonstrated successful multi-item handling. Glossy paper, Matte paper, Poster paper, and Cardstock were all processed, and the system placed reorders where inventory was insufficient.

- **Request 15** demonstrated large-order handling. A4 paper and Colored paper were fulfilled through reorder logic, while **cardboard for signage** was reported as **not offered by our company**.

- **Request 17** also showed mixed handling. A4 paper, Colored paper, Paper cups, and Paper plates were processed, while **table napkins (white)** were reported as unsupported.

These results show that the system does not simply approve every request. It can both fulfill supported items and reject unsupported ones with explicit reasons.

---

## 5. Strengths of the System

The final system has several strengths:

- clear separation of responsibilities across agents,
- use of the required starter helper functions,
- use of the required framework through registered tools,
- support for multi-item customer requests,
- automatic reorder decisions when stock is low,
- generation of `test_results.csv` for evaluation,
- customer-facing handling of unsupported items.

---

## 6. Limitations and Areas for Improvement

The current system still has some limitations:

1. **Rule-based parsing**  
   The request parser is rule-based and may still merge or simplify some unsupported free-text items instead of always separating them perfectly.

2. **Catalog interpretation**  
   Some real-world product descriptions may still require richer synonym support or more advanced natural-language understanding.

3. **More realistic business logic**  
   A production version could model supplier lead times, partial shipments, and payment timing more realistically.

---

## 7. Conclusion

Overall, the final system meets the project goals by combining agent-based orchestration, inventory review, quote generation, sales processing, and evaluation. It uses the provided helper functions, produces the required test output, and demonstrates both successful fulfillment and clear handling of unsupported requests.