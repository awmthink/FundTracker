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

    <div class="holdings-grid">
      <el-card v-for="holding in holdings" :key="holding.fund_code" class="holding-card">
        <div class="holding-header">
          <div class="fund-info">
            <div class="fund-code">{{ holding.fund_code }}</div>
            <div class="fund-name">{{ holding.fund_name }}</div>
          </div>
          <el-button
            size="small"
            type="primary"
            :loading="holding.updating"
            @click="updateSingleNav(holding)"
          >
            更新净值
          </el-button>
        </div>

        <div class="holding-details">
          <div class="detail-row">
            <div class="detail-item">
              <div class="label">持有份额</div>
              <div class="value">{{ formatNumber(holding.total_shares) }}</div>
            </div>
            <div class="detail-item">
              <div class="label">最新净值</div>
              <div class="value">{{ formatNumber(holding.current_nav, 4) }}</div>
            </div>
          </div>

          <div class="detail-row">
            <div class="detail-item">
              <div class="label">平均持仓净值</div>
              <div class="value">{{ formatNumber(holding.avg_cost_nav, 4) }}</div>
            </div>
            <div class="detail-item">
              <div class="label">持仓成本</div>
              <div class="value">{{ formatNumber(holding.cost_amount) }}</div>
            </div>
          </div>

          <div class="detail-row">
            <div class="detail-item">
              <div class="label">持仓市值</div>
              <div class="value">{{ formatNumber(holding.market_value) }}</div>
            </div>
            <div class="detail-item">
              <div class="label">持有收益</div>
              <div class="value" :class="getProfitClass(holding.holding_profit)">
                {{ formatNumber(holding.holding_profit) }}
              </div>
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
                {{ formatNumber(holding.total_profit) }}
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
      lastUpdateTime: null
    }
  },
  methods: {
    async loadHoldings() {
      this.loading = true
      try {
        const response = await fundApi.getHoldings()
        if (response.data.status === 'success') {
          this.holdings = response.data.data.map(holding => ({
            ...holding,
            updating: false
          }))
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

    formatNumber(num, decimals = 2) {
      if (num === null || num === undefined) return '--'
      return Number(num).toFixed(decimals)
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
  color: #303133;
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.last-update-time {
  color: #909399;
  font-size: 14px;
}

.holdings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.holding-card {
  transition: all 0.3s;
}

.holding-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
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

.fund-code {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.fund-name {
  font-size: 14px;
  color: #606266;
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
  color: #909399;
}

.value {
  font-size: 15px;
  color: #303133;
  font-weight: 500;
}

.profit {
  color: #67C23A;
}

.loss {
  color: #F56C6C;
}

@media (max-width: 768px) {
  .holdings-grid {
    grid-template-columns: 1fr;
  }
  
  .header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>
