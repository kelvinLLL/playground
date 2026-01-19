# Task List for Stock Backtesting Framework

- [ ] Project Initialization & Architecture Design
    - [/] Create project structure and environment setup
    - [/] Design core abstract base classes (Data, Strategy, Engine, Portfolio) <!-- id: 0 -->
- [/] Core Component Implementation
    - [x] Implement DataHandler (CSV/Mock for now, extensible for API later) <!-- id: 1 -->
    - [x] Implement Portfolio & Order Management <!-- id: 2 -->
    - [x] Implement Strategy Base Class <!-- id: 3 -->
    - [x] Implement Event-Driven Backtest Engine <!-- id: 4 -->
- [x] Basic Strategy & Verification
    - [x] Write a simple Moving Average Crossover strategy <!-- id: 5 -->
    - [x] Run backtest on sample data <!-- id: 6 -->
    - [x] Calculate basic performance metrics (Sharpe, Max Drawdown) <!-- id: 7 -->
- [ ] Visualization (Optional/Later)
    - [ ] Basic plot of equity curve
