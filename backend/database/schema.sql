-- 基金表：存储基金的基本信息和费率设置
CREATE TABLE funds (
    fund_id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 基金ID，主键
    fund_code TEXT NOT NULL,                    -- 基金代码，如"000001"
    fund_name TEXT NOT NULL,                    -- 基金名称
    current_nav REAL DEFAULT 0,                 -- 当前净值
    last_update_time DATETIME,                  -- 最后更新时间
    buy_fee REAL DEFAULT 0,                    -- 买入费率
    sell_fee_lt7 REAL DEFAULT 0,               -- 持有期小于7天的赎回费率
    sell_fee_lt365 REAL DEFAULT 0,             -- 持有期7-365天的赎回费率
    sell_fee_gt365 REAL DEFAULT 0,             -- 持有期大于365天的赎回费率
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fund_code)                          -- 基金代码唯一约束
);

-- 基金交易表：记录基金的买入卖出交易
CREATE TABLE fund_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 交易ID，主键
    fund_id INTEGER NOT NULL,                         -- 关联的基金ID
    transaction_type TEXT NOT NULL,                   -- 交易类型：buy(买入)或sell(卖出)
    amount REAL NOT NULL,                            -- 交易金额
    nav REAL NOT NULL,                              -- 交易时的净值
    fee REAL DEFAULT 0,                             -- 手续费
    transaction_date DATE NOT NULL,                 -- 交易日期
    shares REAL NOT NULL,                           -- 交易份额
    FOREIGN KEY (fund_id) REFERENCES funds(fund_id) -- 外键约束，关联funds表
);