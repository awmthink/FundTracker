<template>
  <div class="fund-holdings">
    <div class="header">
      <h2>基金持仓</h2>
      <div class="actions">
        <el-button 
          type="primary"
          :loading="updating"
          @click="updateAllNavs"
        >
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
            <div 
              class="non-monetary-progress" 
              :style="{ width: `${nonMonetaryPercentage}%` }"
            ></div>
            <div 
              class="monetary-progress" 
              :style="{ width: `${monetaryPercentage}%` }"
            ></div>
          </div>
        </div>
      </el-card>

      <!-- 投入计划完成情况卡片 -->
      <el-card class="investment-plan-card">
        <div class="card-header">
          <div class="card-title">投入计划完成情况</div>
        </div>
        <div class="investment-plan-content">
          <div class="progress-container">
            <el-progress 
              :percentage="investmentCompletionRate" 
              :format="() => ''" 
              :stroke-width="10"
              :color="getProgressColor(investmentCompletionRate)"
            />
          </div>
          <div class="plan-summary">
            <div class="plan-item">
              <div class="plan-label">总目标投入</div>
              <div class="plan-value">¥ {{ formatCurrency(totalTargetInvestment) }}</div>
            </div>
            <div class="plan-item">
              <div class="plan-label">已投入金额</div>
              <div class="plan-value">¥ {{ formatCurrency(totalInvestment) }}</div>
            </div>
            <div class="plan-item">
              <div class="plan-label">完成进度</div>
              <div class="plan-value">{{ formatNumber(investmentCompletionRate) }}%</div>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <div class="holdings-grid">
      <el-card v-for="holding in holdings" :key="holding.fund_code" class="holding-card">
        <div class="holding-header">
          <div class="fund-info">
            <div class="fund-name">{{ holding.fund_name }}</div>
            <div class="fund-code">{{ holding.fund_code }}</div>
          </div>
        </div>

        <div class="holding-details">

          <div class="detail-row">
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
          </div>
          
          <div class="detail-row">
            <div class="detail-item">
              <div class="label">持有份额</div>
              <div class="value">{{ formatCurrency(holding.total_shares) }}</div>
            </div>

            <div class="detail-item">
                <div class="label">持仓成本</div>
                <div class="value">¥ {{ formatCurrency(holding.cost_amount) }}</div>
            </div>
            
          </div>

          

          <div class="detail-row">
                <div class="detail-item">
                  <div class="label">平均持仓净值</div>
                  <div class="value">{{ formatNumber(holding.avg_cost_nav, 4) }}</div>
                </div>
                <div class="detail-item">
                  <div class="label">最新净值</div>
                  <div class="value">{{ formatNumber(holding.current_nav, 4) }}</div>
                </div>
              </div>

              <div class="detail-row">
                <div class="detail-item">
                  <div class="label">持有收益率</div>
                  <div class="value" :class="getProfitClass(holding.holding_profit_rate)">
                    {{ formatNumber(holding.holding_profit_rate * 100) }}%
                  </div>
                </div>
                <div class="detail-item">
                  <div class="label">累计收益</div>
                  <div class="value" :class="getProfitClass(holding.total_profit)">
                    ¥ {{ formatCurrency(holding.total_profit) }}
                  </div>
                </div>
              </div>

          <!-- 可折叠部分 -->
          <el-collapse>
            <el-collapse-item>
              <template #title>
                <div class="collapse-title">
                  <span>更多详情</span>
                </div>
              </template>
              
              <!-- 折叠内容 - 详细信息 -->

              <div class="detail-row">
                <div class="detail-item">
                  <div class="label">目标投入</div>
                  <div class="value">¥ {{ formatCurrency(holding.target_investment || 0) }}</div>
                </div>
                <div class="detail-item">
                  <div class="label">投入进度</div>
                  <div class="value">
                    {{ holding.target_investment ? formatNumber((holding.cost_amount / holding.target_investment) * 100) : '0' }}%
                  </div>
                </div>
              </div>
              
              <div class="detail-row">
                <div class="detail-item">
                  <div class="label">距上次买入涨幅</div>
                  <div class="value" :class="getProfitClass(holding.since_last_buy_rate)">
                    {{ formatRateValue(holding.since_last_buy_rate) }}
                  </div>
                </div>
                <div class="detail-item">
                  <div class="label">距上次卖出涨幅</div>
                  <div class="value" :class="getProfitClass(holding.since_last_sell_rate)">
                    {{ formatRateValue(holding.since_last_sell_rate) }}
                  </div>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
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
      nonMonetaryPercentage: 0,
      totalTargetInvestment: 0,
      investmentCompletionRate: 0
    }
  },
  methods: {
    async loadHoldings() {
      this.loading = true
      try {
        const response = await fundApi.getHoldings()
        if (response.data.status === 'success') {
          this.holdings = response.data.data
            .map(holding => ({
              ...holding,
              updating: false
            }))
            .sort((a, b) => b.market_value - a.market_value)
          this.lastUpdateTime = new Date()
          this.totalInvestment = response.data.data.reduce((total, holding) => total + holding.cost_amount, 0)
          this.totalMarketValue = response.data.data.reduce((total, holding) => total + holding.market_value, 0)
          this.totalHoldingProfit = response.data.data.reduce((total, holding) => total + holding.holding_profit, 0)
          this.totalProfit = response.data.data.reduce((total, holding) => total + holding.total_profit, 0)
          
          // 计算货币类和非货币类基金市值
          this.monetaryValue = response.data.data
            .filter(holding => holding.fund_type && holding.fund_type.includes('货币'))
            .reduce((total, holding) => total + holding.market_value, 0)
          
          this.nonMonetaryValue = this.totalMarketValue - this.monetaryValue
          
          // 计算百分比
          this.monetaryPercentage = this.totalMarketValue > 0 
            ? (this.monetaryValue / this.totalMarketValue * 100) 
            : 0
          
          this.nonMonetaryPercentage = this.totalMarketValue > 0 
            ? (this.nonMonetaryValue / this.totalMarketValue * 100) 
            : 0
          
          // 计算总目标投入和投入完成率
          this.totalTargetInvestment = response.data.data
            .reduce((total, holding) => total + (holding.target_investment || 0), 0)
          
          this.investmentCompletionRate = this.totalTargetInvestment > 0
            ? (this.totalInvestment / this.totalTargetInvestment * 100)
            : 0
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
      return `${(rate * 100).toFixed(2)}%`
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
      if (percentage < 30) return '#909399'  // 灰色
      if (percentage < 70) return '#409EFF'  // 蓝色
      if (percentage < 90) return '#E6A23C'  // 橙色
      return '#67C23A'  // 绿色
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
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 30px;
}

.asset-allocation-card, 
.investment-plan-card {
  margin-bottom: 0;  /* 覆盖原来的下边距 */
  height: 100%;      /* 确保两个卡片高度一致 */
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
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.holding-card {
  transition: all 0.3s;
  background-color: var(--card-bg);
  border-color: var(--border-color);
}

.holding-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.holding-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.fund-info {
  flex: 1;
}

.fund-name {
  font-size: 16px;
  font-weight: bold;
  color: var(--text-color);
}

.fund-code {
  font-size: 14px;
  color: var(--text-color-secondary);
  margin-top: 4px;
}

.holding-details {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.label {
  font-size: 13px;
  color: var(--text-color-secondary);
}

.value {
  font-size: 15px;
  color: var(--text-color);
  font-weight: 500;
}

.profit {
  color: #67C23A;
}

.loss {
  color: #F56C6C;
}

@media (max-width: 768px) {
  .cards-row {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  
  .asset-allocation-card,
  .investment-plan-card {
    margin-bottom: 0;
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

/* 折叠面板样式 - 完全重写 */
:deep(.el-collapse) {
  border: none !important;
}

:deep(.el-collapse-item__header) {
  border: none !important;
  height: auto !important;
  line-height: normal !important;
  padding: 8px !important;
  margin: 4px 0 !important;
  border-radius: 4px !important;
  color: var(--text-color-secondary) !important;
  background-color: transparent !important;
  transition: all 0.3s ease !important;
}

:deep(.el-collapse-item__content) {
  padding-bottom: 0 !important;
}

:deep(.el-collapse-item__wrap) {
  border: none !important;
  background-color: transparent !important;
}

/* 亮色模式悬浮效果 */
:deep(.el-collapse-item__header:hover) {
  background-color: rgba(0, 0, 0, 0.05) !important;
}

/* 暗色模式特定样式 */
.dark-theme :deep(.el-collapse-item__header) {
  background-color: rgba(30, 30, 30, 0.6) !important;
}

.dark-theme :deep(.el-collapse-item__header:hover) {
  background-color: rgba(255, 255, 255, 0.2) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5) !important;
}

/* 确保折叠标题在暗色模式下更加明显 */
.dark-theme .collapse-title {
  color: #e0e0e0 !important;
  font-weight: 500 !important;
}

/* 确保箭头在暗色模式下可见 */
.dark-theme :deep(.el-collapse-item__arrow) {
  color: #e0e0e0 !important;
  font-size: 16px !important;
}
</style>
