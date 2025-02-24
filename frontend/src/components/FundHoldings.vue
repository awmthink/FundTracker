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

    <div class="table-container">
      <el-table 
        :data="holdings" 
        border 
        style="width: 100%"
        v-loading="loading"
        element-loading-text="正在加载持仓信息..."
      >
        <el-table-column prop="fund_code" label="基金代码" width="100" />
        <el-table-column prop="fund_name" label="基金名称" width="220" />
        <el-table-column label="持仓份额" width="120">
          <template #default="scope">
            {{ formatNumber(scope.row.total_shares) }}
          </template>
        </el-table-column>
        <el-table-column label="最新净值" width="100">
          <template #default="scope">
            {{ formatNumber(scope.row.current_nav, 4) }}
          </template>
        </el-table-column>
        <el-table-column label="持仓成本" width="120">
          <template #default="scope">
            {{ formatNumber(scope.row.cost_amount) }}
          </template>
        </el-table-column>
        <el-table-column label="持仓市值" width="120">
          <template #default="scope">
            {{ formatNumber(scope.row.market_value) }}
          </template>
        </el-table-column>
        <el-table-column label="浮动盈亏" width="120">
          <template #default="scope">
            {{ formatNumber(scope.row.profit_loss) }}
          </template>
        </el-table-column>
        <el-table-column label="收益率" width="100">
          <template #default="scope">
            <span :class="{'profit': scope.row.profit_rate > 0, 'loss': scope.row.profit_rate < 0}">
              {{ formatNumber(scope.row.profit_rate * 100) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="scope">
            <el-button
              size="small"
              type="primary"
              :loading="scope.row.updating"
              @click="updateSingleNav(scope.row)"
            >
              更新净值
            </el-button>
          </template>
        </el-table-column>
      </el-table>
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
    }
  },
  mounted() {
    this.loadHoldings()
  }
}
</script>

<style scoped>
.fund-holdings {
  background: #fff;
  padding: 20px;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
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

.profit {
  color: #67C23A;
}

.loss {
  color: #F56C6C;
}

/* 表格内按钮样式优化 */
.el-table .el-button {
  padding: 6px 12px;
}

/* 确保按钮之间有合适的间距 */
.el-button + .el-button {
  margin-left: 8px;
}

:deep(.el-table) {
  margin-top: 20px;
}
</style>
