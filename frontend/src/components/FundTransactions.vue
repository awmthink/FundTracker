<template>
  <div class="fund-transactions">
    <div class="header">
      <h2>交易记录</h2>
      <div class="quick-filters">
        <el-radio-group v-model="quickDateRange" @change="handleQuickDateChange">
          <el-radio-button label="1">最近1个月</el-radio-button>
          <el-radio-button label="3">最近3个月</el-radio-button>
          <el-radio-button label="6">最近6个月</el-radio-button>
          <el-radio-button label="12">最近1年</el-radio-button>
          <el-radio-button label="custom">自定义</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- 搜索表单 -->
    <el-form 
      v-show="quickDateRange === 'custom'" 
      :inline="true" 
      :model="filters" 
      class="search-form"
    >
      <el-form-item label="基金代码">
        <el-input v-model="filters.fund_code" placeholder="请输入基金代码" />
      </el-form-item>
      <el-form-item label="基金名称">
        <el-input v-model="filters.fund_name" placeholder="请输入基金名称" />
      </el-form-item>
      <el-form-item label="交易类型">
        <el-select 
          v-model="filters.transaction_type" 
          placeholder="请选择"
          style="width: 180px"
        >
          <el-option label="全部" value="all" />
          <el-option label="买入" value="buy" />
          <el-option label="卖出" value="sell" />
        </el-select>
      </el-form-item>
      <el-form-item label="交易日期">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="searchTransactions">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 交易记录表格 -->
    <el-table
      :data="transactions"
      style="width: 100%"
      :header-cell-style="{ background: 'var(--card-bg)', color: 'var(--text-color)' }"
    >
      <el-table-column prop="fund_code" label="基金代码" width="100" />
      <el-table-column prop="fund_name" label="基金名称" width="200" />
      <el-table-column prop="transaction_type" label="交易类型" width="100">
        <template #default="scope">
          {{ scope.row.transaction_type === 'buy' ? '买入' : '卖出' }}
        </template>
      </el-table-column>
      <el-table-column prop="amount" label="交易金额" width="120">
        <template #default="scope">
          {{ formatNumber(scope.row.amount) }}
        </template>
      </el-table-column>
      <el-table-column prop="nav" label="净值" width="100">
        <template #default="scope">
          {{ formatNumber(scope.row.nav, 4) }}
        </template>
      </el-table-column>
      <el-table-column prop="fee" label="手续费" width="100">
        <template #default="scope">
          {{ formatNumber(scope.row.fee, 2) }}
        </template>
      </el-table-column>
      <el-table-column prop="shares" label="份额" width="120">
        <template #default="scope">
          {{ formatNumber(scope.row.shares, 2) }}
        </template>
      </el-table-column>
      <el-table-column prop="transaction_date" label="交易日期" width="120" />
      <el-table-column label="操作" width="200">
        <template #default="scope">
          <el-button
            size="small"
            type="primary"
            @click="handleEdit(scope.row)"
          >
            编辑
          </el-button>
          <el-button
            size="small"
            type="danger"
            @click="handleDelete(scope.row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加编辑对话框 -->
    <el-dialog
      title="编辑交易记录"
      v-model="editDialogVisible"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="基金代码">
          <el-input v-model="editForm.fund_code" disabled />
        </el-form-item>
        <el-form-item label="基金名称">
          <el-input v-model="editForm.fund_name" disabled />
        </el-form-item>
        <el-form-item label="交易类型">
          <el-select v-model="editForm.transaction_type" disabled>
            <el-option label="买入" value="buy" />
            <el-option label="卖出" value="sell" />
          </el-select>
        </el-form-item>
        <el-form-item label="交易金额">
          <el-input-number 
            v-model="editForm.amount" 
            :precision="2" 
            :step="100"
            :min="0"
          />
        </el-form-item>
        <el-form-item label="净值">
          <el-input-number 
            v-model="editForm.nav" 
            :precision="4" 
            :step="0.0001"
            :min="0"
          />
        </el-form-item>
        <el-form-item label="交易日期">
          <el-date-picker
            v-model="editForm.transaction_date"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleUpdate">确认</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fundApi } from '../services/api'

export default {
  name: 'FundTransactions',
  data() {
    return {
      transactions: [],
      filters: {
        fund_code: '',
        fund_name: '',
        transaction_type: 'all',
        start_date: '',
        end_date: ''
      },
      dateRange: [],
      editDialogVisible: false,
      editForm: {
        transaction_id: null,
        fund_code: '',
        fund_name: '',
        transaction_type: '',
        amount: 0,
        nav: 0,
        transaction_date: ''
      },
      quickDateRange: '1', // Default to 1 month
    }
  },
  methods: {
    async loadTransactions() {
      try {
        let filters = {}
        
        if (this.quickDateRange === 'custom') {
          // 自定义模式：使用所有筛选条件
          filters = { ...this.filters }
          if (this.dateRange && this.dateRange.length === 2) {
            filters.start_date = this.dateRange[0]
            filters.end_date = this.dateRange[1]
          }
        } else {
          // 快捷查询模式：只使用日期条件
          if (this.dateRange && this.dateRange.length === 2) {
            filters = {
              start_date: this.dateRange[0],
              end_date: this.dateRange[1]
            }
          }
        }
        
        const response = await fundApi.getTransactions(filters)
        if (response.data.status === 'success') {
          this.transactions = response.data.data
        }
      } catch (error) {
        ElMessage.error('加载交易记录失败')
      }
    },
    
    searchTransactions() {
      this.loadTransactions()
    },
    
    resetFilters() {
      this.filters = {
        fund_code: '',
        fund_name: '',
        transaction_type: 'all',
        start_date: '',
        end_date: ''
      }
      this.dateRange = []
      this.quickDateRange = '1'
      this.handleQuickDateChange('1') // 重置为最近1个月的数据
    },
    
    handleEdit(transaction) {
      this.editForm = {
        transaction_id: transaction.transaction_id,
        fund_code: transaction.fund_code,
        fund_name: transaction.fund_name,
        transaction_type: transaction.transaction_type,
        amount: transaction.amount,
        nav: transaction.nav,
        transaction_date: transaction.transaction_date
      }
      this.editDialogVisible = true
    },
    
    async handleUpdate() {
      try {
        const response = await fundApi.updateTransaction(
          this.editForm.transaction_id,
          this.editForm
        )
        
        if (response.data.status === 'success') {
          ElMessage.success('更新成功')
          this.editDialogVisible = false
          this.loadTransactions()
          this.$emit('transaction-deleted') // 触发持仓更新
        }
      } catch (error) {
        ElMessage.error('更新失败')
      }
    },
    
    async handleDelete(transaction) {
      try {
        await ElMessageBox.confirm(
          '确认要删除这条交易记录吗？此操作不可恢复。',
          '警告',
          {
            confirmButtonText: '确认',
            cancelButtonText: '取消',
            type: 'warning',
          }
        )
        
        const response = await fundApi.deleteTransaction(transaction.transaction_id)
        if (response.data.status === 'success') {
          ElMessage.success('删除成功')
          this.loadTransactions()
          this.$emit('transaction-deleted')
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除失败')
        }
      }
    },
    
    formatNumber(num, decimals = 2) {
      if (num === null || num === undefined) return '--'
      return Number(num).toFixed(decimals)
    },
    handleQuickDateChange(value) {
      if (value === 'custom') {
        // 切换到自定义模式时，保持当前日期范围
        return;
      }
      
      // 快捷查询模式：重置其他筛选条件，只设置日期
      const months = parseInt(value);
      const endDate = new Date();
      const startDate = new Date();
      startDate.setMonth(endDate.getMonth() - months);
      
      this.dateRange = [
        startDate.toISOString().split('T')[0],
        endDate.toISOString().split('T')[0]
      ];
      
      // 清空其他筛选条件
      if (value !== 'custom') {
        this.filters = {
          fund_code: '',
          fund_name: '',
          transaction_type: 'all',
          start_date: '',
          end_date: ''
        }
      }
      
      this.loadTransactions();
    },
  },
  mounted() {
    // When component mounts, show last month's transactions by default
    this.handleQuickDateChange('1');
  }
}
</script>

<style scoped>
.fund-transactions {
  background-color: var(--card-bg);
  border-radius: 8px;
  padding: 20px;
  margin-top: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
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

.quick-filters {
  margin-bottom: 20px;
}

.search-form {
  margin-bottom: 20px;
  padding: 20px;
  background-color: var(--bg-color);
  border-radius: 4px;
}

:deep(.el-table) {
  background-color: var(--card-bg);
  color: var(--text-color);
}

:deep(.el-table__header-wrapper) {
  background-color: var(--card-bg);
}

:deep(.el-table th) {
  background-color: var(--card-bg);
  color: var(--text-color);
  border-bottom-color: var(--border-color);
}

:deep(.el-table td) {
  background-color: var(--card-bg);
  color: var(--text-color);
  border-bottom-color: var(--border-color);
}

:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) {
  background-color: var(--hover-bg);
}

:deep(.el-radio-button__inner) {
  background-color: var(--card-bg);
  color: var(--text-color);
  border-color: var(--border-color);
}

:deep(.el-radio-button__orig-radio:checked + .el-radio-button__inner) {
  color: #fff;
}

:deep(.el-form-item__label) {
  color: var(--text-color);
}

:deep(.el-input__inner),
:deep(.el-select .el-input__inner),
:deep(.el-date-editor.el-input__inner) {
  background-color: var(--bg-color);
  border-color: var(--border-color);
  color: var(--text-color);
}

:deep(.el-table__empty-block) {
  background-color: var(--card-bg);
}

:deep(.el-table__empty-text) {
  color: var(--text-color-secondary);
}

/* 确保分页器也适配暗色主题 */
:deep(.el-pagination) {
  color: var(--text-color);
  background-color: var(--card-bg);
}

:deep(.el-pagination button) {
  background-color: var(--card-bg);
  color: var(--text-color);
}

:deep(.el-pagination .el-select .el-input .el-input__inner) {
  background-color: var(--card-bg);
  color: var(--text-color);
}

:deep(.el-pagination .el-pager li) {
  background-color: var(--card-bg);
  color: var(--text-color);
}

:deep(.el-pagination .el-pager li.active) {
  color: var(--el-color-primary);
}

.el-input,
.el-select {
  width: 180px !important;
}

.el-date-picker {
  width: 240px !important;  /* 日期选择器需要更宽一些 */
}

/* 修改收益颜色样式 */
:deep(.profit) {
  color: #F56C6C !important;  /* 红色，表示正收益 */
}

:deep(.loss) {
  color: #67C23A !important;  /* 绿色，表示负收益 */
}
</style> 