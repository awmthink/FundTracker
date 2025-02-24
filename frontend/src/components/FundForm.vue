<template>
  <div>
    <el-dialog
      title="添加基金交易"
      v-model="dialogVisible"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form 
        ref="formRef"
        :model="transaction"
        :rules="rules"
        label-width="120px"
        label-position="right"
      >
        <!-- 基金代码 -->
        <el-form-item label="基金代码" prop="fund_code">
          <el-input 
            v-model="transaction.fund_code"
            placeholder="请输入6位基金代码"
            maxlength="6"
            @blur="handleFundCodeChange"
          >
            <template #append>
              <el-button 
                :loading="loading"
                @click="handleFundCodeChange"
              >
                获取信息
              </el-button>
            </template>
          </el-input>
        </el-form-item>

        <!-- 基金名称 -->
        <el-form-item label="基金名称" prop="fund_name">
          <el-input 
            v-model="transaction.fund_name"
            disabled
            placeholder="基金名称将自动获取"
          />
        </el-form-item>

        <!-- 交易类型 -->
        <el-form-item label="交易类型" prop="transaction_type">
          <el-select 
            v-model="transaction.transaction_type"
            style="width: 100%"
            @change="calculateFee"
          >
            <el-option label="买入" value="buy" />
            <el-option label="卖出" value="sell" />
          </el-select>
        </el-form-item>

        <!-- 交易日期 -->
        <el-form-item label="交易日期" prop="transaction_date">
          <el-date-picker
            v-model="transaction.transaction_date"
            type="date"
            style="width: 100%"
            value-format="YYYY-MM-DD"
            @change="fetchHistoricalNav"
          />
        </el-form-item>

        <!-- 交易金额 -->
        <el-form-item label="交易金额" prop="amount">
          <el-input-number
            v-model="transaction.amount"
            :precision="2"
            :step="100"
            :min="0"
            style="width: 100%"
            @change="calculateFee"
          />
        </el-form-item>

        <!-- 基金净值 -->
        <el-form-item label="基金净值" prop="nav">
          <el-input-number
            v-model="transaction.nav"
            :precision="4"
            :step="0.0001"
            :min="0"
            style="width: 100%"
            disabled
          />
        </el-form-item>

        <!-- 手续费率 -->
        <el-form-item label="手续费率 (%)">
          <el-input-number
            v-model="displayFeeRate"
            :precision="2"
            :step="0.01"
            :min="0"
            style="width: 100%"
            disabled
          />
        </el-form-item>

        <!-- 手续费 -->
        <el-form-item label="手续费">
          <el-input-number
            v-model="transaction.fee"
            :precision="2"
            :step="0.01"
            :min="0"
            style="width: 100%"
            disabled
          />
        </el-form-item>

        <!-- 预计份额 -->
        <el-form-item label="预计份额">
          <el-input-number
            v-model="transaction.shares"
            :precision="2"
            :step="0.01"
            :min="0"
            style="width: 100%"
            disabled
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button 
            type="primary" 
            @click="submitTransaction"
            :disabled="!isFormValid"
          >
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
      return {
        fund_code: '',
        fund_name: '',
        transaction_type: 'buy',
        amount: 0,
        nav: 0,
        fee: 0,
        shares: 0,
        transaction_date: new Date().toISOString().split('T')[0]
      }
    },
    showDialog() {
      this.dialogVisible = true
    },
    async handleFundCodeChange() {
      if (!this.transaction.fund_code) return
      
      this.loading = true
      try {
        // 获取基金信息
        const navResponse = await fundApi.getFundNav(this.transaction.fund_code)
        if (navResponse.data.status === 'success') {
          this.transaction.fund_name = navResponse.data.data.name
        }

        // 获取基金费率设置
        const settingsResponse = await fundApi.getFundFees(this.transaction.fund_code)
        if (settingsResponse.data.status === 'success') {
          this.fundSettings = settingsResponse.data.data
        } else {
          this.$message.warning('未找到该基金的费率设置，请先在基金设置中配置')
        }

        // 获取历史净值
        await this.fetchHistoricalNav()
      } catch (error) {
        this.$message.error('获取基金信息失败')
      } finally {
        this.loading = false
      }
    },
    async fetchHistoricalNav() {
      if (!this.transaction.fund_code || !this.transaction.transaction_date) return
      
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

      const amount = parseFloat(this.transaction.amount)
      let feeRate = 0

      if (this.transaction.transaction_type === 'buy') {
        feeRate = this.fundSettings.buy_fee
      } else {
        // 这里可以根据实际需求判断是使用短期还是长期费率
        feeRate = this.fundSettings.sell_fee_short
      }

      this.displayFeeRate = (feeRate * 100).toFixed(2)
      this.transaction.fee = amount * feeRate

      if (this.transaction.nav > 0) {
        if (this.transaction.transaction_type === 'buy') {
          // 买入份额 = (金额 - 手续费) / 净值
          this.transaction.shares = (amount - this.transaction.fee) / this.transaction.nav
        } else {
          // 卖出份额 = 金额 / 净值
          this.transaction.shares = amount / this.transaction.nav
        }
        // 保留小数点后两位
        this.transaction.shares = parseFloat(this.transaction.shares.toFixed(2))
      }
    },
    async submitTransaction() {
      if (!this.isFormValid) return

      try {
        await fundApi.addTransaction(this.transaction)
        this.$message.success('交易添加成功')
        this.dialogVisible = false
        this.$emit('transaction-added')
        this.transaction = this.getEmptyTransaction()
      } catch (error) {
        this.$message.error('添加交易失败')
      }
    }
  }
}
</script>

<style scoped>
.el-dialog {
  border-radius: 8px;
}

.el-form {
  padding: 20px;
}

.dialog-footer {
  text-align: right;
  padding: 0 20px 20px;
}

:deep(.el-input-number) {
  width: 100%;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

:deep(.el-input.is-disabled .el-input__inner) {
  color: #606266;
  background-color: #f5f7fa;
}
</style>
