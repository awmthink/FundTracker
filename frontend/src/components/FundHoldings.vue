<template>
  <div class="fund-holdings">
    <div class="header">
      <h2>基金持仓</h2>
      <div class="actions">
        <el-button type="primary" :loading="updating" @click="updateAllNavs">
          更新全部净值
        </el-button>
        <span v-if="lastUpdateTime" class="last-update-time">
          最后更新时间：{{ formatDateTime(lastUpdateTime) }}
        </span>
      </div>
    </div>

    <!-- 添加汇总信息卡片 -->
    <div class="summary-cards">
      <el-card class="summary-card">
        <div class="summary-title">持有总市值</div>
        <div class="summary-value">¥ {{ formatCurrency(totalMarketValue) }}</div>
      </el-card>
      <el-card class="summary-card">
        <div class="summary-title">总投入</div>
        <div class="summary-value">¥ {{ formatCurrency(totalInvestment) }}</div>
      </el-card>
      <el-card class="summary-card">
        <div class="summary-title">持有收益</div>
        <div class="summary-value" :class="getProfitClass(totalHoldingProfit)">
          ¥ {{ formatCurrency(totalHoldingProfit) }}
        </div>
      </el-card>
      <el-card class="summary-card">
        <div class="summary-title">累计收益</div>
        <div class="summary-value" :class="getProfitClass(totalProfit)">
          ¥ {{ formatCurrency(totalProfit) }}
        </div>
      </el-card>
    </div>

    <!-- 将资产配置和投入计划卡片放在一行 -->
    <div class="cards-row">
      <!-- 资产配置比例卡片 -->
      <el-card class="asset-allocation-card">
        <div class="card-header">
          <div class="card-title">资产配置比例</div>
        </div>
        <div class="allocation-content">
          <div class="allocation-item">
            <div class="allocation-label">
              <span class="allocation-color non-monetary"></span>
              <span>权益类基金</span>
            </div>
            <div class="allocation-value">¥ {{ formatCurrency(nonMonetaryValue) }}</div>
            <div class="allocation-percentage">{{ formatNumber(nonMonetaryPercentage) }}%</div>
          </div>
          <div class="allocation-item">
            <div class="allocation-label">
              <span class="allocation-color monetary"></span>
              <span>货币类基金</span>
            </div>
            <div class="allocation-value">¥ {{ formatCurrency(monetaryValue) }}</div>
            <div class="allocation-percentage">{{ formatNumber(monetaryPercentage) }}%</div>
          </div>
          <div class="allocation-progress">
            <div class="non-monetary-progress" :style="{ width: `${nonMonetaryPercentage}%` }"></div>
            <div class="monetary-progress" :style="{ width: `${monetaryPercentage}%` }"></div>
          </div>
        </div>
      </el-card>
    </div>

    <div class="holdings-grid">
      <el-card v-for="holding in holdings" :key="holding.fund_code" class="holding-card"
        :class="{ 'monetary-fund-card': holding.fund_type && holding.fund_type.includes('货币') }"
        @click="holding.isExpanded = !holding.isExpanded">
        <div class="holding-header">
          <div class="fund-info">
            <div class="fund-basic-info">
              <div class="fund-title">
                <div class="fund-name">{{ holding.fund_name }}</div>
                <div class="fund-code">{{ holding.fund_code }}</div>
              </div>
            </div>

            <div class="position-progress">
              <div class="progress-bar">
                <div class="progress-fill" :style="{
                  width: `${Math.min(100, holding.actualPosition)}%`,
                  backgroundColor: getProgressColor(holding.actualPosition)
                }">
                </div>
                <span class="progress-text">
                  {{ formatNumber(holding.actualPosition) }}%
                  <span class="position-status">{{ getPositionStatus(holding.actualPosition) }}</span>
                </span>
              </div>
            </div>

            <div class="daily-growth" :class="getProfitClass(holding.daily_growth_rate)">
              {{ formatRateValue(holding.daily_growth_rate) }}
            </div>
          </div>
          <div class="holding-details">
            <div class="detail-item">
              <div class="label">持仓市值</div>
              <div class="value">¥ {{ formatCurrency(holding.market_value) }}</div>
            </div>
            <div class="detail-item">
              <div class="label">持有收益</div>
              <div class="value" :class="getProfitClass(holding.holding_profit)">
                ¥ {{ formatCurrency(holding.holding_profit) }}
              </div>
            </div>
            <div class="detail-item">
              <div class="label">持有收益率</div>
              <div class="value" :class="getProfitClass(holding.holding_profit_rate)">
                {{ formatNumber(holding.holding_profit_rate * 100) }}%
              </div>
            </div>

            <div class="detail-item">
              <div class="label">持仓成本</div>
              <div class="value">¥ {{ formatCurrency(holding.cost_amount) }}</div>
            </div>
            <div class="detail-item">
              <div class="label">累计收益</div>
              <div class="value" :class="getProfitClass(holding.total_profit)">
                ¥ {{ formatCurrency(holding.total_profit) }}
              </div>
            </div>
          </div>
        </div>

        <!-- 展开的详细信息 -->
        <div v-if="holding.isExpanded" class="expanded-details">
          <div class="detail-row">
            <div class="detail-item">
              <div class="label">持有份额</div>
              <div class="value">{{ formatCurrency(holding.total_shares) }}</div>
            </div>
            <div class="detail-item">
              <div class="label">持仓成本</div>
              <div class="value">¥ {{ formatCurrency(holding.cost_amount) }}</div>
            </div>
            <div class="detail-item">
              <div class="label">平均持仓净值</div>
              <div class="value">{{ formatNumber(holding.avg_cost_nav, 4) }}</div>
            </div>
            <div class="detail-item">
              <div class="label">最新净值</div>
              <div class="value">{{ formatNumber(holding.current_nav, 4) }}</div>
            </div>
            <div class="detail-item">
              <div class="label">累计收益</div>
              <div class="value" :class="getProfitClass(holding.total_profit)">
                ¥ {{ formatCurrency(holding.total_profit) }}
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'
import { fundApi } from '../services/api'

export default {
  name: 'FundHoldings',
  data() {
    return {
      holdings: [],
      updating: false,
      loading: false,
      lastUpdateTime: null,
      totalInvestment: 0,
      totalMarketValue: 0,
      totalHoldingProfit: 0,
      totalProfit: 0,
      monetaryValue: 0,
      nonMonetaryValue: 0,
      monetaryPercentage: 0,
      nonMonetaryPercentage: 0
    }
  },
  methods: {
    async loadHoldings() {
      this.loading = true
      try {
        const response = await fundApi.getHoldings()
        if (response.data.status === 'success') {
          // 先计算总市值和各类基金市值
          this.totalMarketValue = response.data.data.reduce((total, holding) => total + holding.market_value, 0)
          this.totalInvestment = response.data.data.reduce((total, holding) => total + holding.cost_amount, 0)
          this.totalHoldingProfit = response.data.data.reduce((total, holding) => total + holding.holding_profit, 0)
          this.totalProfit = response.data.data.reduce((total, holding) => total + holding.total_profit, 0)

          // 计算货币类和非货币类基金市值
          this.monetaryValue = response.data.data
            .filter(holding => holding.fund_type && holding.fund_type.includes('货币'))
            .reduce((total, holding) => total + holding.market_value, 0)

          this.nonMonetaryValue = this.totalMarketValue - this.monetaryValue

          // 计算百分比（相对于总市值）
          this.monetaryPercentage = this.totalMarketValue > 0
            ? (this.monetaryValue / this.totalMarketValue * 100)
            : 0

          this.nonMonetaryPercentage = this.totalMarketValue > 0
            ? (this.nonMonetaryValue / this.totalMarketValue * 100)
            : 0

          // 更新每个基金的实际仓位
          this.holdings = response.data.data.map(holding => {
            return {
              ...holding,
              updating: false,
              isExpanded: false,
              actualPosition: this.totalMarketValue > 0
                ? (holding.market_value / this.totalMarketValue * 100)
                : 0
            }
          }).sort((a, b) => b.market_value - a.market_value)

          this.lastUpdateTime = new Date()
        }
      } catch (error) {
        ElMessage.error('加载持仓信息失败')
        console.error('加载持仓信息失败:', error)
      } finally {
        this.loading = false
      }
    },

    async updateAllNavs() {
      this.updating = true
      try {
        const response = await fundApi.updateAllNavs()
        if (response.data.status === 'success') {
          await this.loadHoldings()
          ElMessage.success('更新成功')
          this.lastUpdateTime = new Date()
        }
      } catch (error) {
        ElMessage.error('更新净值失败')
        console.error('更新净值失败:', error)
      } finally {
        this.updating = false
      }
    },

    async updateSingleNav(fund) {
      fund.updating = true
      try {
        const response = await fundApi.getCurrentNav(fund.fund_code)
        if (response.data.status === 'success') {
          await this.loadHoldings()
          ElMessage.success(`${fund.fund_name} 净值更新成功`)
        }
      } catch (error) {
        ElMessage.error(`更新 ${fund.fund_name} 净值失败`)
        console.error('更新单个基金净值失败:', error)
      } finally {
        fund.updating = false
      }
    },

    formatRateValue(rate) {
      if (rate === null || rate === undefined) return '--'
      const formattedRate = (rate * 100).toFixed(2)
      return formattedRate > 0 ? `+${formattedRate}%` : `${formattedRate}%`
    },

    formatNumber(num, decimals = 2) {
      if (num === null || num === undefined) return '--'
      return Number(num).toFixed(decimals)
    },

    formatCurrency(num) {
      if (num === null || num === undefined) return '--'
      return Number(num).toLocaleString('zh-CN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })
    },

    formatDateTime(datetime) {
      if (!datetime) return ''
      const date = new Date(datetime)
      return date.toLocaleString()
    },

    getProfitClass(value) {
      return {
        'profit': value > 0,
        'loss': value < 0
      }
    },

    getProgressColor(percentage) {
      if (percentage < 1) return '#FFFFFF'  // 空仓 - 白色
      if (percentage < 10) return '#67C23A'  // 轻仓 - 绿色
      if (percentage < 30) return '#409EFF'  // 中性 - 蓝色
      return '#F56C6C'  // 重仓 - 红色
    },

    getPositionStatus(percentage) {
      if (percentage < 1) return '空仓'
      if (percentage < 10) return '轻仓'
      if (percentage < 30) return '中性'
      return '重仓'
    }
  },
  mounted() {
    this.loadHoldings()
  }
}
</script>

<style scoped>
.fund-holdings {
  background: transparent;
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  color: var(--text-color);
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.last-update-time {
  color: var(--text-color-secondary);
  font-size: 14px;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.summary-card {
  background-color: var(--card-bg);
  border-color: var(--border-color);
  transition: all 0.3s;
}

.summary-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.summary-title {
  font-size: 14px;
  color: var(--text-color-secondary);
  margin-bottom: 8px;
}

.summary-value {
  font-size: 24px;
  font-weight: bold;
  color: var(--text-color);
}

.cards-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
  margin-bottom: 30px;
}

.asset-allocation-card {
  margin-bottom: 0;
  /* 覆盖原来的下边距 */
  height: 100%;
  /* 确保两个卡片高度一致 */
  background-color: var(--card-bg);
  border-color: var(--border-color);
}

.card-header {
  margin-bottom: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: bold;
  color: var(--text-color);
}

.allocation-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.allocation-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px dashed var(--border-color, rgba(0, 0, 0, 0.06));
}

.allocation-item:last-child {
  border-bottom: none;
  margin-bottom: 8px;
}

.allocation-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-color);
  font-size: 14px;
}

.allocation-color {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.allocation-color.non-monetary {
  background-color: #409EFF;
}

.allocation-color.monetary {
  background-color: #67C23A;
}

.allocation-value {
  color: var(--text-color);
  font-size: 14px;
  font-weight: 500;
  flex: 1;
  text-align: right;
  padding-right: 16px;
}

.allocation-percentage {
  color: var(--text-color);
  font-weight: bold;
  font-size: 15px;
  width: 70px;
  text-align: right;
  background-color: var(--bg-color-light, rgba(0, 0, 0, 0.03));
  padding: 4px 8px;
  border-radius: 4px;
}

/* 添加暗色模式下的特定样式 */
.dark-theme .allocation-percentage {
  background-color: rgba(255, 255, 255, 0.1);
}

.allocation-progress {
  height: 8px;
  width: 100%;
  background-color: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  display: flex;
}

.non-monetary-progress {
  height: 100%;
  background-color: #409EFF;
}

.monetary-progress {
  height: 100%;
  background-color: #67C23A;
}

.holdings-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}

.holding-card {
  transition: all 0.3s;
  background-color: var(--card-bg);
  border-color: var(--border-color);
  width: 100%;
  cursor: pointer;
}

.holding-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.holding-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 16px 0;
}

.fund-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
}

.fund-basic-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.fund-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.fund-name {
  font-size: 18px;
  font-weight: bold;
  color: var(--text-color);
}

.fund-code {
  font-size: 14px;
  color: var(--text-color-secondary);
  padding: 2px 8px;
  background-color: var(--bg-color-light, rgba(0, 0, 0, 0.03));
  border-radius: 4px;
}

.position-progress {
  display: flex;
  width: 500px;
  /* 固定宽度 */
  margin-left: auto;
  /* 右对齐 */
  margin-right: 20px;
  /* 与日涨跌保持间距 */
}

.progress-bar {
  height: 18px;
  /* 增加高度使其更醒目 */
  background-color: var(--bg-color-light, rgba(0, 0, 0, 0.03));
  border-radius: 6px;
  overflow: hidden;
  width: 100%;
  position: relative;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease, background-color 0.3s ease;
  position: relative;
  z-index: 1;
  border: 1px solid rgba(0, 0, 0, 0.1);
  /* 添加边框以区分空仓状态 */
}

.progress-text {
  position: absolute;
  width: 100%;
  text-align: center;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-color);
  z-index: 2;
  text-shadow:
    -1px -1px 0 rgba(255, 255, 255, 0.7),
    1px -1px 0 rgba(255, 255, 255, 0.7),
    -1px 1px 0 rgba(255, 255, 255, 0.7),
    1px 1px 0 rgba(255, 255, 255, 0.7);
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.position-status {
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 3px;
  background-color: rgba(0, 0, 0, 0.1);
}

.dark-theme .position-status {
  background-color: rgba(255, 255, 255, 0.1);
}

.dark-theme .progress-text {
  color: #fff;
  text-shadow:
    -1px -1px 0 rgba(0, 0, 0, 0.7),
    1px -1px 0 rgba(0, 0, 0, 0.7),
    -1px 1px 0 rgba(0, 0, 0, 0.7),
    1px 1px 0 rgba(0, 0, 0, 0.7);
}

/* 暗色模式适配 */
.dark-theme .progress-bar {
  background-color: rgba(255, 255, 255, 0.1);
}

.daily-growth {
  font-size: 18px;
  font-weight: bold;
  padding: 4px 8px;
  border-radius: 4px;
  min-width: 80px;
  text-align: center;
  background-color: var(--bg-color-light);
}

.daily-growth.profit {
  color: #fff;
  background-color: #F56C6C;
}

.daily-growth.loss {
  color: #fff;
  background-color: #67C23A;
}

.dark-theme .fund-code {
  background-color: rgba(255, 255, 255, 0.05);
}

.holding-details {
  display: flex;
  gap: 32px;
  align-items: center;
  flex-wrap: wrap;
  padding-bottom: 12px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 120px;
}

.label {
  font-size: 14px;
  color: var(--text-color-secondary);
}

.value {
  font-size: 16px;
  color: var(--text-color);
  font-weight: 500;
  white-space: nowrap;
}

.profit {
  color: #F56C6C;
  /* 红色，表示正收益 */
}

.loss {
  color: #67C23A;
  /* 绿色，表示负收益 */
}

@media (max-width: 1200px) {
  .position-progress {
    width: 250px;
    /* 在较小屏幕上稍微减小宽度 */
  }

  .holding-details,
  .detail-row {
    gap: 24px;
  }

  .detail-item {
    min-width: calc(25% - 18px);
  }
}

@media (max-width: 768px) {
  .fund-info {
    flex-direction: column;
    align-items: flex-start;
  }

  .position-progress {
    width: 100%;
    /* 在移动端采用全宽 */
    margin: 12px 0;
  }

  .holding-details,
  .detail-row {
    gap: 16px;
  }

  .detail-item {
    min-width: calc(50% - 8px);
  }
}

.investment-plan-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.plan-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.plan-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background-color: var(--bg-color-light, rgba(0, 0, 0, 0.03));
  border-radius: 6px;
}

.dark-theme .plan-item {
  background-color: rgba(255, 255, 255, 0.05);
}

.plan-label {
  font-size: 14px;
  color: var(--text-color-secondary);
}

.plan-value {
  font-size: 18px;
  font-weight: bold;
  color: var(--text-color);
}

.progress-container {
  padding: 8px 0;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--text-color-secondary);
}

@media (max-width: 768px) {
  .plan-summary {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}

/* 展开的详细信息 */
.expanded-details {
  padding: 12px 16px 0;
}

.expanded-details .detail-row {
  padding: 16px 0 0;
  border-top: 1px solid var(--border-color);
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 32px;
  flex-wrap: wrap;
  padding-bottom: 12px;
}

.detail-row .label {
  font-size: 14px;
}

.detail-row .value {
  font-size: 16px;
}

@media (max-width: 1200px) {

  .holding-details,
  .detail-row {
    gap: 24px;
  }

  .detail-item {
    min-width: calc(25% - 18px);
  }
}

@media (max-width: 768px) {

  .holding-details,
  .detail-row {
    gap: 16px;
  }

  .detail-item {
    min-width: calc(50% - 8px);
  }
}

/* 货币型基金卡片样式 */
.monetary-fund-card {
  background-color: rgba(120, 82, 238, 0.05);
  /* 浅紫色背景 */
  border-left: 3px solid #7852ee;
  /* 紫色左边框 */
}

/* 暗色模式下的货币型基金卡片 */
.dark-theme .monetary-fund-card {
  background-color: rgba(120, 82, 238, 0.1);
  /* 暗色模式下稍微深一点的紫色 */
}
</style>
