# Finance Management Platform UML Documentation

These diagrams are the streamlined final-delivery view of the packaged GUI application. They focus on GUI users, core business logic, dashboard analytics, and the shared SQLite database. Internal developer-only entry points, support utilities, test classes, and the internals of Tkinter, Matplotlib, and the Python standard library are intentionally omitted.

## Required Diagrams

The following four diagram types are the primary UML deliverables for this project:

| Requirement | Files | Purpose |
| --- | --- | --- |
| Context Modeling Diagram | [`Source`](./00-context-modeling.puml) / [`PNG`](./rendered/png/00-context-modeling.png) / [`SVG`](./rendered/svg/00-context-modeling.svg) | Defines GUI-only packaged-user access, the desktop environment, and shared SQLite storage |
| Use Case Diagram | [`Source`](./02-use-cases.puml) / [`PNG`](./rendered/png/02-use-cases.png) / [`SVG`](./rendered/svg/02-use-cases.svg) | Separates current personal-finance GUI capabilities from planned household- and business-finance GUI capabilities |
| Class Diagram | [`Source`](./03-essential-class-diagram.puml) / [`PNG`](./rendered/png/03-essential-class-diagram.png) / [`SVG`](./rendered/svg/03-essential-class-diagram.svg) | Describes the principal classes, attributes, methods, inheritance, composition, and dependencies |
| Sequence Diagram | [`Source`](./06-gui-add-transaction-sequence.puml) / [`PNG`](./rendered/png/06-gui-add-transaction-sequence.png) / [`SVG`](./rendered/svg/06-gui-add-transaction-sequence.svg) | Uses the GUI Add Transaction workflow to show the order of calls between objects |

The required class diagram is supplemented by a custom data-structure diagram. The required GUI Add Transaction sequence is supplemented by the Dashboard scenario.

## Complete Diagram Index

| File | Diagram Type | Focus |
| --- | --- | --- |
| [`00-context-modeling.puml`](./00-context-modeling.puml) | Context Modeling Diagram | GUI access for the three core end-user roles, desktop environment, and shared SQLite storage |
| [`01-system-components.puml`](./01-system-components.puml) | Component Diagram | Packaged GUI, core business services, domain models, analytics, and SQLite persistence |
| [`02-use-cases.puml`](./02-use-cases.puml) | Use Case Diagram | Current personal GUI features and explicitly planned household- and business-finance GUI scope |
| [`03-essential-class-diagram.puml`](./03-essential-class-diagram.puml) | Core Class Diagram | Primary class relationships suitable for a report or printed submission |
| [`04-detailed-class-diagram.puml`](./04-detailed-class-diagram.puml) | Detailed GUI Class Diagram | GUI classes, domain models, business services, and SQLite persistence |
| [`05-data-structures.puml`](./05-data-structures.puml) | Supplementary Class Diagram | Custom data structures used by `TransactionManager` and their node relationships |
| [`06-gui-add-transaction-sequence.puml`](./06-gui-add-transaction-sequence.puml) | Sequence Diagram | GUI workflow for adding a transaction, atomically saving transactions and budgets to SQLite, and handling stale-state conflicts |
| [`07-dashboard-sequence.puml`](./07-dashboard-sequence.puml) | Sequence Diagram | Dashboard creation, data aggregation, chart rendering, and refresh behavior |
| [`08-undo-redo-activity.puml`](./08-undo-redo-activity.puml) | Activity Diagram | Undo and redo branches implemented by `TransactionManager` |

## Reading Notes

- A solid composition arrow indicates that an object directly creates and owns another object in the current implementation.
- A dashed dependency arrow indicates a temporary call, parameter transfer, or factory-style creation.
- `TransactionManager` maintains a hash table, two binary search trees, a doubly linked list, a category tree, and two stacks. The same transaction object is referenced by multiple indexes.
- `Queue` is implemented and imported by `transaction_manager.py`, but `TransactionManager` does not currently instantiate or call it. The data-structure diagram therefore marks it as not currently integrated.
- Personal, household, and company users are the three core product roles. The packaged product is represented as a GUI-only application; household and company interfaces remain planned.
- The GUI uses `FinanceApplicationState` to serialize transactions and budgets together and save them to the shared SQLite database.
- The SQLite backend uses an application revision inside a write transaction. A stale process cannot silently overwrite newer committed data.
- Transactions, budgets, and application metadata are stored in the shared SQLite database. Runtime code does not read or write JSON files.
- Household and company ledgers appear only in the use case diagram as `<<planned>>` capabilities and are not implemented in this release.
- The GUI lazily imports the Dashboard. The Dashboard obtains the transaction list through a callback and passes it to the pure data-analysis function `build_dashboard_data()`.

## Rendering

The source files use PlantUML syntax. They can be viewed or rendered in any of the following ways:

1. Install a PlantUML extension in VS Code, IntelliJ IDEA, or PyCharm, then open a `.puml` file and use the preview command.
2. If the PlantUML command-line tool is available, run the following command from the project root:

   ```powershell
   plantuml .\docs\uml\*.puml
   ```

3. If PlantUML is available as a JAR file, run:

   ```powershell
   java -jar plantuml.jar .\docs\uml\*.puml
   ```

PlantUML generates PNG files next to the source files by default. Pass `-tsvg` to generate SVG output. The rendered files in this project are stored under `rendered/png/` and `rendered/svg/`.

