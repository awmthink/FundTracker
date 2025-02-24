<template>
  <div class="fund-holdings">
    <div class="header">
      <h2>基金持仓</h2>
      <div class="header-actions">
        <span class="last-update-time" v-if="lastUpdateTime">
          最后更新时间: {{ formatDateTime(lastUpdateTime) }}
        </span>
        <el-button 
          type="primary" 
          size="small" 
          @click="updateAllNavs" 
          :loading="updating"
        >
          更新最新净值
        </el-button>
      </div>
    </div>
    
    <div class="table-container">
      <el-table :data="holdings" border style="width: 100%">
        <el-table-column prop="fund_code" label="基金代码" width="120" />
        <el-table-column prop="fund_name" label="基金名称" width="200" />
        <el-table-column prop="total_shares" label="持有份额" width="120">
          <template #default="scope">
            {{ formatNumber(scope.row.total_shares, 2) }}
          </template>
        </el-table-column>
        <el-table-column prop="total_cost" label="投入成本" width="120">
          <template #default="scope">
            {{ formatNumber(scope.row.total_cost, 2) }}
          </template>
        </el-table-column>
        <el-table-column label="当前净值" width="120">
          <template #default="scope">
            <div class="nav-cell">
              {{ formatNumber(scope.row.current_nav, 4) }}
              <el-button
                type="text"
                size="small"
                @click="updateSingleNav(scope.row)"
                :loading="scope.row.updating"
              >
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="current_value" label="当前市值" width="120">
          <template #default="scope">
            {{ formatNumber(scope.row.current_value, 2) }}
          </template>
        </el-table-column>
        <el-table-column prop="profit" label="收益金额" width="120">
          <template #default="scope">
            <span :class="{ 'profit': scope.row.profit > 0, 'loss': scope.row.profit < 0 }">
              {{ formatNumber(scope.row.profit, 2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="profit_rate" label="收益率" width="120">
          <template #default="scope">
            <span :class="{ 'profit': scope.row.profit_rate > 0, 'loss': scope.row.profit_rate < 0 }">
              {{ formatNumber(scope.row.profit_rate, 2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="last_update_time" label="更新时间" width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.last_update_time) }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script>
import { fundApi } from '../services/api'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'

export default {
  components: {
    Refresh
  },
  data() {
    return {
      holdings: [],
      updating: false,
      lastUpdateTime: null
    }
  },
  methods: {
    async loadHoldings() {
      try {
        const response = await fundApi.getHoldings();
        if (response.data.status === 'success') {
          this.holdings = response.data.data.map(holding => ({
            ...holding,
            updating: false
          }));
          this.lastUpdateTime = new Date();
        }
      } catch (error) {
        ElMessage.error('加载持仓信息失败');
        console.error('加载持仓信息失败:', error);
      }
    },

    async updateAllNavs() {
      this.updating = true;
      try {
        const response = await fundApi.updateAllNavs();
        if (response.data.status === 'success') {
          await this.loadHoldings();
          ElMessage.success('更新成功');
          this.lastUpdateTime = new Date();
        }
      } catch (error) {
        ElMessage.error('更新净值失败');
        console.error('更新净值失败:', error);
      } finally {
        this.updating = false;
      }
    },

    async updateSingleNav(fund) {
      fund.updating = true;
      try {
        const response = await fundApi.getCurrentNav(fund.fund_code);
        if (response.data.status === 'success') {
          await this.loadHoldings();
          ElMessage.success(`${fund.fund_name} 净值更新成功`);
        }
      } catch (error) {
        ElMessage.error(`更新 ${fund.fund_name} 净值失败`);
        console.error('更新单个基金净值失败:', error);
      } finally {
        fund.updating = false;
      }
    },

    formatNumber(num, decimals = 2) {
      if (num === null || num === undefined) return '--';
      return Number(num).toFixed(decimals);
    },

    formatDateTime(datetime) {
      if (!datetime) return '';
      const date = new Date(datetime);
      return date.toLocaleString();
    }
  },
  mounted() {
    this.loadHoldings();
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.last-update-time {
  color: #909399;
  font-size: 14px;
}

.nav-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.profit {
  color: #f56c6c;
}

.loss {
  color: #67c23a;
}

:deep(.el-table) {
  margin-top: 20px;
}
</style>
