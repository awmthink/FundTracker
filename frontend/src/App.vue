<template>
  <el-container class="app-container">
    <el-header>
      <h1>个人基金管理</h1>
    </el-header>
    <el-main>
      <el-row :gutter="20">
        <el-col :span="24">
          <div class="action-bar">
            <el-button 
              type="primary" 
              @click="showAddTransactionDialog"
            >
              添加基金交易
            </el-button>
            <el-button 
              @click="showFundSettingsDialog"
            >
              基金设置
            </el-button>
          </div>
          <FundHoldings ref="holdings" />
          <FundTransactions ref="transactions" @transaction-deleted="refreshHoldings" />
        </el-col>
      </el-row>
      <FundForm ref="fundForm" @transaction-added="refreshHoldings" />
      <FundSettings ref="fundSettings" />
    </el-main>
  </el-container>
</template>

<script>
import FundForm from './components/FundForm.vue'
import FundHoldings from './components/FundHoldings.vue'
import FundSettings from './components/FundSettings.vue'
import FundTransactions from './components/FundTransactions.vue'

export default {
  name: 'App',
  components: {
    FundForm,
    FundHoldings,
    FundSettings,
    FundTransactions
  },
  methods: {
    showAddTransactionDialog() {
      this.$refs.fundForm.showDialog()
    },
    showFundSettingsDialog() {
      this.$refs.fundSettings.showDialog()
    },
    refreshHoldings() {
      this.$refs.holdings.loadHoldings()
    }
  }
}
</script>

<style>
body {
  margin: 0;
  padding: 0;
  background-color: #f5f7fa;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
}

.app-container {
  min-height: 100vh;
}

.el-header {
  background-color: #fff;
  color: #333;
  text-align: center;
  line-height: 60px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.12);
  margin-bottom: 20px;
}

.el-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 500;
}

.el-main {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.action-bar {
  margin-bottom: 20px;
  text-align: right;
}

.action-bar .el-button + .el-button {
  margin-left: 12px;
}
</style>
