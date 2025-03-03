-- 基金表：存储基金的基本信息和费率设置
CREATE TABLE funds (
    fund_code TEXT PRIMARY KEY,  -- 使用 fund_code 作为主键
    fund_name TEXT NOT NULL,
    current_nav REAL DEFAULT 0,
    last_update_time DATETIME,
    buy_fee REAL DEFAULT 0,
    fund_type TEXT,  -- 新增字段：基金类型
    target_investment REAL DEFAULT 0,  -- 新增字段：目标投入金额
    investment_strategy TEXT,  -- 新增字段：投资策略
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 基金交易表：记录基金的买入卖出交易
CREATE TABLE fund_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT NOT NULL,     -- 改为直接引用 fund_code
    transaction_type TEXT NOT NULL,
    amount REAL NOT NULL,
    nav REAL NOT NULL,
    fee REAL DEFAULT 0,
    transaction_date DATE NOT NULL,
    shares REAL NOT NULL,
    FOREIGN KEY (fund_code) REFERENCES funds(fund_code)
);