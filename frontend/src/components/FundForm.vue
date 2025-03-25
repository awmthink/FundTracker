<template>
  <div>
    <el-dialog title="添加基金交易" v-model="dialogVisible" width="600px" :close-on-click-modal="false"
      custom-class="fund-form-dialog">
      <el-form ref="formRef" :model="transaction" :rules="rules" label-width="120px" label-position="right">
        <!-- 基金代码 -->
        <el-form-item label="基金代码" prop="fund_code">
          <el-input v-model="transaction.fund_code" placeholder="请输入6位基金代码" maxlength="6" @blur="handleFundCodeChange">
            <template #append>
              <el-button :loading="loading" @click="handleFundCodeChange">
                获取信息
              </el-button>
            </template>
          </el-input>
        </el-form-item>

        <!-- 基金名称 -->
        <el-form-item label="基金名称" prop="fund_name">
          <el-input v-model="transaction.fund_name" disabled placeholder="基金名称将自动获取" />
        </el-form-item>

        <!-- 交易类型 -->
        <el-form-item label="交易类型" prop="transaction_type">
          <el-radio-group v-model="transaction.transaction_type" @change="calculateFee">
            <el-radio-button label="buy">申购</el-radio-button>
            <el-radio-button label="sell">赎回</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 交易日期 -->
        <el-form-item label="交易日期" prop="transaction_date">
          <el-date-picker v-model="transaction.transaction_date" type="date" style="width: 100%"
            value-format="YYYY-MM-DD" @change="fetchHistoricalNav" />
        </el-form-item>

        <!-- 交易金额/份额 -->
        <el-form-item :label="transaction.transaction_type === 'buy' ? '申购金额' : '赎回份额'" prop="amount">
          <el-input-number v-model="transaction.amount" :precision="2" :step="1" :min="0" style="width: 100%"
            @change="calculateFee" />
        </el-form-item>

        <!-- 基金净值 -->
        <el-form-item label="基金净值" prop="nav">
          <el-input-number v-model="transaction.nav" :precision="4" :step="0.0001" :min="0" style="width: 100%"
            disabled />
        </el-form-item>

        <!-- 手续费率 - 仅在申购时显示 -->
        <el-form-item label="手续费率 (%)" v-if="transaction.transaction_type === 'buy'">
          <el-input-number v-model="displayFeeRate" :precision="2" :step="0.01" :min="0" style="width: 100%" disabled />
        </el-form-item>

        <!-- 手续费 -->
        <el-form-item label="手续费" prop="fee" v-if="transaction.transaction_type === 'sell'">
          <el-input-number v-model="transaction.fee" :precision="2" :step="0.01" :min="0" style="width: 100%"
            @change="calculateAmount" />
        </el-form-item>

        <!-- 预计份额 - 仅在申购时显示 -->
        <el-form-item label="预计份额" v-if="transaction.transaction_type === 'buy'">
          <el-input-number v-model="transaction.shares" :precision="2" :step="0.01" :min="0" style="width: 100%"
            disabled />
        </el-form-item>

        <!-- 到账金额 -->
        <el-form-item label="到账金额" v-if="transaction.transaction_type === 'sell'">
          <el-input-number v-model="transaction.final_amount" :precision="2" disabled style="width: 100%" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm" :disabled="!isFormValid">
            提交
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { fundApi } from '../services/api'

export default {
  name: 'FundForm',
  data() {
    return {
      dialogVisible: false,
      loading: false,
      transaction: this.getEmptyTransaction(),
      fundSettings: null,
      displayFeeRate: 0,
      rules: {
        fund_code: [
          { required: true, message: '请输入基金代码', trigger: 'blur' },
          { pattern: /^\d{6}$/, message: '请输入6位数字的基金代码', trigger: 'blur' }
        ],
        fund_name: [
          { required: true, message: '基金名称不能为空', trigger: 'blur' }
        ],
        transaction_type: [
          { required: true, message: '请选择交易类型', trigger: 'change' }
        ],
        transaction_date: [
          { required: true, message: '请选择交易日期', trigger: 'change' }
        ],
        amount: [
          { required: true, message: '请输入交易金额', trigger: 'blur' },
          { type: 'number', min: 0, message: '交易金额必须大于0', trigger: 'blur' }
        ],
        nav: [
          { required: true, message: '基金净值不能为空', trigger: 'blur' },
          { type: 'number', min: 0, message: '基金净值必须大于0', trigger: 'blur' }
        ]
      }
    }
  },
  computed: {
    isFormValid() {
      return this.transaction.fund_code &&
        this.transaction.fund_name &&
        this.transaction.amount > 0 &&
        this.transaction.nav > 0 &&
        this.transaction.transaction_date
    }
  },
  methods: {
    getEmptyTransaction() {
      // 获取昨天的日期
      const yesterday = new Date()
      yesterday.setDate(yesterday.getDate() - 1)

      return {
        fund_code: '',
        fund_name: '',
        transaction_type: 'buy',
        amount: 0,
        nav: 0,
        fee: 0,
        shares: 0,
        final_amount: 0,
        transaction_date: yesterday.toISOString().split('T')[0]
      }
    },
    showDialog() {
      this.dialogVisible = true
    },
    async handleFundCodeChange() {
      if (!this.transaction.fund_code) return

      this.loading = true
      try {
        // 先获取所有基金设置
        const settingsResponse = await fundApi.getAllFundSettings()
        if (settingsResponse.data.status === 'success') {
          const fundList = settingsResponse.data.data
          const fundSetting = fundList.find(fund => fund.fund_code === this.transaction.fund_code)

          if (!fundSetting) {
            this.$message.warning('该基金未在系统中设置，请先在基金设置中添加基金信息')
            this.transaction.fund_name = ''
            this.fundSettings = null
            return
          }

          // 使用已保存的基金信息
          this.transaction.fund_name = fundSetting.fund_name
          this.fundSettings = {
            buy_fee: fundSetting.buy_fee
          }
          this.displayFeeRate = (fundSetting.buy_fee * 100).toFixed(2)

          // 获取历史净值
          await this.fetchHistoricalNav()
        }
      } catch (error) {
        console.error('获取基金信息失败:', error)
        this.$message.error('获取基金信息失败')
      } finally {
        this.loading = false
      }
    },
    async fetchHistoricalNav() {
      if (!this.transaction.fund_code || !this.transaction.transaction_date) return

      // 检查是否为当天交易
      const today = new Date().toISOString().split('T')[0]
      if (this.transaction.transaction_date === today) {
        this.$message.warning('不支持添加当天的交易记录，因为净值数据可能不准确')
        this.transaction.nav = 0
        return
      }

      try {
        const response = await fundApi.getHistoricalNav(
          this.transaction.fund_code,
          this.transaction.transaction_date
        )

        if (response.data.status === 'success') {
          this.transaction.nav = response.data.data.nav
          this.calculateFee()
        }
      } catch (error) {
        this.$message.error('获取历史净值失败')
      }
    },
    calculateFee() {
      if (!this.fundSettings || !this.transaction.amount) return

      if (this.transaction.transaction_type === 'buy') {
        const amount = parseFloat(this.transaction.amount)
        const feeRate = this.fundSettings.buy_fee
        this.displayFeeRate = (feeRate * 100).toFixed(2)
        this.transaction.fee = amount * feeRate

        if (this.transaction.nav > 0) {
          // 买入份额 = (金额 - 手续费) / 净值
          this.transaction.shares = (amount - this.transaction.fee) / this.transaction.nav
          this.transaction.shares = parseFloat(this.transaction.shares.toFixed(2))
        }
      } else {
        // 卖出时，amount代表份额
        if (this.transaction.nav > 0) {
          // 计算卖出总金额
          const totalAmount = this.transaction.amount * this.transaction.nav
          // 计算到账金额
          this.transaction.final_amount = totalAmount - this.transaction.fee
        }
      }
    },
    calculateAmount() {
      if (this.transaction.transaction_type === 'sell' && this.transaction.nav > 0) {
        // 计算卖出总金额
        const totalAmount = this.transaction.amount * this.transaction.nav
        // 计算到账金额
        this.transaction.final_amount = totalAmount - this.transaction.fee
      }
    },
    async submitForm() {
      // 检查是否为当天交易
      const today = new Date().toISOString().split('T')[0]
      if (this.transaction.transaction_date === today) {
        this.$message.warning('不支持添加当天的交易记录，因为净值数据可能不准确')
        return
      }

      try {
        const formData = {
          fund_code: this.transaction.fund_code,
          fund_name: this.transaction.fund_name,
          transaction_type: this.transaction.transaction_type,
          nav: this.transaction.nav,
          transaction_date: this.transaction.transaction_date,
          // 买入时提交申购金额，卖出时提交赎回份额
          amount: this.transaction.amount,
          // 买入时计算的手续费，卖出时用户输入的手续费
          fee: this.transaction.fee,
          // 买入时计算的份额，卖出时就是赎回份额
          shares: this.transaction.transaction_type === 'buy'
            ? this.transaction.shares
            : this.transaction.amount
        }

        const response = await fundApi.addTransaction(formData)
        if (response.data.status === 'success') {
          this.$message.success('交易添加成功')
          this.dialogVisible = false
          this.$emit('transaction-added')
          this.resetForm()
        }
      } catch (error) {
        this.$message.error('添加交易失败')
      }
    },
    resetForm() {
      this.transaction = this.getEmptyTransaction()
    }
  }
}
</script>

<style scoped>
.fund-form-dialog {
  --section-padding: 20px;
}

:deep(.el-form-item) {
  margin-bottom: 18px;
}

:deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

:deep(.el-input.is-disabled .el-input__inner) {
  color: var(--text-color);
  -webkit-text-fill-color: var(--text-color);
}

:deep(.el-radio-button__inner) {
  background-color: var(--bg-color);
  color: var(--text-color);
  border-color: var(--border-color);
}

:deep(.el-radio-button__orig-radio:checked + .el-radio-button__inner) {
  color: #fff;
}

:deep(.el-input-number.is-disabled .el-input__inner) {
  color: var(--text-color);
  -webkit-text-fill-color: var(--text-color);
}

/* 优化获取信息按钮样式 */
:deep(.el-input-group__append) {
  background-color: var(--el-button-bg-color);
  border-color: var(--el-border-color);
}

:deep(.el-input-group__append .el-button) {
  border: none;
  margin: 0;
  background: transparent;
  color: var(--el-text-color-regular);
}

:deep(.el-input-group__append .el-button:hover) {
  color: var(--el-color-primary);
  background: transparent;
}

:deep(.el-input-group__append .el-button.is-loading) {
  background: transparent;
}

.dialog-footer {
  text-align: right;
  margin-top: 20px;
}

/* 添加收益颜色样式，保持一致性 */
.profit {
  color: #F56C6C;
  /* 红色，表示正收益 */
}

.loss {
  color: #67C23A;
  /* 绿色，表示负收益 */
}
</style>
