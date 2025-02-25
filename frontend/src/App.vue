<template>
  <el-container class="app-container" :class="{ 'dark-theme': isDarkTheme }">
    <el-header>
      <div class="header-content">
        <h1>FundTracker</h1>
        <el-switch
          v-model="isDarkTheme"
          class="theme-switch"
          active-text="暗色"
          inactive-text="亮色"
        />
      </div>
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
  data() {
    return {
      isDarkTheme: false
    }
  },
  watch: {
    isDarkTheme(newValue) {
      localStorage.setItem('theme', newValue ? 'dark' : 'light')
      document.documentElement.setAttribute('data-theme', newValue ? 'dark' : 'light')
    }
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
    },
    initTheme() {
      const savedTheme = localStorage.getItem('theme')
      this.isDarkTheme = savedTheme === 'dark'
      document.documentElement.setAttribute('data-theme', savedTheme || 'light')
    }
  },
  mounted() {
    this.initTheme()
  }
}
</script>

<style>
:root {
  --bg-color: #f5f7fa;
  --text-color: #303133;
  --text-color-secondary: #606266;
  --border-color: #dcdfe6;
  --header-bg: #fff;
  --card-bg: #fff;
  --hover-bg: #f5f7fa;
}

:root[data-theme='dark'] {
  --bg-color: #1a1a1a;
  --text-color: #e5e5e5;
  --text-color-secondary: #a3a3a3;
  --border-color: #4c4c4c;
  --header-bg: #2a2a2a;
  --card-bg: #2a2a2a;
  --hover-bg: #363636;
}

body {
  margin: 0;
  padding: 0;
  background-color: var(--bg-color);
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  color: var(--text-color);
}

.app-container {
  min-height: 100vh;
  background-color: var(--bg-color);
}

.el-header {
  background-color: var(--header-bg);
  color: var(--text-color);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.12);
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  padding: 0 20px;
}

.el-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 500;
}

.theme-switch {
  margin-left: 20px;
}

/* Dark theme overrides for Element Plus components */
.dark-theme {
  --el-bg-color: var(--card-bg);
  --el-text-color-primary: var(--text-color);
  --el-text-color-regular: var(--text-color-secondary);
  --el-border-color: var(--border-color);
}

.dark-theme .el-card,
.dark-theme .el-dialog,
.dark-theme .el-table {
  background-color: var(--card-bg);
  border-color: var(--border-color);
}

.dark-theme .el-table th,
.dark-theme .el-table tr {
  background-color: var(--card-bg);
  color: var(--text-color);
}

.dark-theme .el-table--border {
  border-color: var(--border-color);
}

.dark-theme .el-table td,
.dark-theme .el-table th.is-leaf {
  border-bottom: 1px solid var(--border-color);
}

.dark-theme .el-input__inner,
.dark-theme .el-textarea__inner {
  background-color: var(--bg-color);
  border-color: var(--border-color);
  color: var(--text-color);
}

.dark-theme .el-button {
  border-color: var(--border-color);
  color: var(--text-color);
}

.dark-theme .el-button--primary {
  color: #fff;
}

.dark-theme .el-dialog__title {
  color: var(--text-color);
}

.dark-theme .el-form-item__label {
  color: var(--text-color);
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

.dark-theme .el-dialog {
  background-color: var(--card-bg);
}

.dark-theme .el-input-number__decrease,
.dark-theme .el-input-number__increase {
  background-color: var(--bg-color);
  border-color: var(--border-color);
  color: var(--text-color);
}

.dark-theme .el-input.is-disabled .el-input__inner {
  background-color: var(--hover-bg);
  border-color: var(--border-color);
  color: var(--text-color-secondary);
}

.dark-theme .el-table--striped .el-table__body tr.el-table__row--striped td {
  background-color: var(--hover-bg);
}

.dark-theme .el-table__body tr:hover > td {
  background-color: var(--hover-bg) !important;
}

.dark-theme .el-select-dropdown {
  background-color: var(--card-bg);
  border-color: var(--border-color);
}

.dark-theme .el-select-dropdown__item {
  color: var(--text-color);
}

.dark-theme .el-select-dropdown__item.hover,
.dark-theme .el-select-dropdown__item:hover {
  background-color: var(--hover-bg);
}

/* 输入框相关样式 */
.dark-theme .el-input__wrapper,
.dark-theme .el-textarea__wrapper {
  background-color: var(--bg-color);
  box-shadow: 0 0 0 1px var(--border-color) inset !important;
}

.dark-theme .el-input__wrapper:hover,
.dark-theme .el-textarea__wrapper:hover {
  box-shadow: 0 0 0 1px var(--el-color-primary) inset !important;
}

.dark-theme .el-input__wrapper.is-focus,
.dark-theme .el-textarea__wrapper.is-focus {
  box-shadow: 0 0 0 1px var(--el-color-primary) inset !important;
}

/* 按钮相关样式 */
.dark-theme .el-button {
  background-color: var(--card-bg);
  border-color: var(--border-color);
  color: var(--text-color);
}

.dark-theme .el-button:hover {
  background-color: var(--hover-bg);
  border-color: var(--el-color-primary-light-7);
  color: var(--el-color-primary);
}

.dark-theme .el-button--default:not(:disabled):hover {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary-light-7);
  background-color: var(--hover-bg);
}

/* 日期选择器相关样式 */
.dark-theme .el-date-editor .el-range__icon,
.dark-theme .el-date-editor .el-range-separator {
  color: var(--text-color-secondary);
}

.dark-theme .el-date-editor .el-range-input {
  background-color: transparent;
  color: var(--text-color);
}

.dark-theme .el-picker__popper {
  background-color: var(--card-bg);
  border-color: var(--border-color);
}

.dark-theme .el-date-table th,
.dark-theme .el-date-table td {
  color: var(--text-color);
}

.dark-theme .el-date-table td.next-month,
.dark-theme .el-date-table td.prev-month {
  color: var(--text-color-secondary);
}

.dark-theme .el-date-picker__header-label {
  color: var(--text-color);
}

.dark-theme .el-picker-panel__content {
  background-color: var(--card-bg);
}

.dark-theme .el-date-picker__header-label:hover {
  color: var(--el-color-primary);
}

/* 下拉菜单相关样式 */
.dark-theme .el-select-dropdown {
  background-color: var(--card-bg);
  border-color: var(--border-color);
}

.dark-theme .el-select-dropdown__item {
  color: var(--text-color);
}

.dark-theme .el-select-dropdown__item.hover,
.dark-theme .el-select-dropdown__item:hover {
  background-color: var(--hover-bg);
}

/* 弹出框相关样式 */
.dark-theme .el-dialog {
  background-color: var(--card-bg);
}

.dark-theme .el-dialog__title {
  color: var(--text-color);
}

.dark-theme .el-dialog__body {
  color: var(--text-color);
}

/* 表单相关样式 */
.dark-theme .el-form-item__label {
  color: var(--text-color);
}

/* 禁用状态的输入框 */
.dark-theme .el-input.is-disabled .el-input__wrapper {
  background-color: var(--hover-bg);
  box-shadow: 0 0 0 1px var(--border-color) inset !important;
}

.dark-theme .el-input.is-disabled .el-input__inner {
  color: var(--text-color-secondary);
}

/* 主要按钮样式保持醒目 */
.dark-theme .el-button--primary {
  background-color: var(--el-color-primary);
  border-color: var(--el-color-primary);
  color: #fff;
}

.dark-theme .el-button--primary:hover {
  background-color: var(--el-color-primary-light-2);
  border-color: var(--el-color-primary-light-2);
  color: #fff;
}

/* 单选按钮组样式 */
.dark-theme .el-radio-button__inner {
  background-color: var(--card-bg);
  color: var(--text-color);
  border-color: var(--border-color);
}

.dark-theme .el-radio-button:first-child .el-radio-button__inner {
  border-left-color: var(--border-color);
}

.dark-theme .el-radio-button__orig-radio:checked + .el-radio-button__inner {
  background-color: var(--el-color-primary);
  border-color: var(--el-color-primary);
  color: #fff;
  box-shadow: -1px 0 0 0 var(--el-color-primary);
}

/* 分割线样式 */
.dark-theme .el-divider {
  background-color: var(--border-color);
}

.dark-theme .el-divider__text {
  background-color: var(--card-bg);
  color: var(--text-color-secondary);
}
</style>
