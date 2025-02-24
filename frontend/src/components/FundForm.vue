<template>
  <div>
    <el-dialog
      title="添加基金交易"
      v-model="dialogVisible"
      width="500px"
    >
      <form @submit.prevent="submitTransaction">
        <div class="form-group">
          <label>基金代码</label>
          <div class="input-with-button">
            <input v-model="transaction.fund_code" required @blur="handleFundCodeChange">
            <el-button size="small" @click="handleFundCodeChange" :loading="loading">
              获取信息
            </el-button>
          </div>
        </div>
        <div class="form-group">
          <label>基金名称</label>
          <input v-model="transaction.fund_name" disabled>
        </div>
        <div class="form-group">
          <label>交易类型</label>
          <select v-model="transaction.transaction_type" @change="calculateFee">
            <option value="buy">买入</option>
            <option value="sell">卖出</option>
          </select>
        </div>
        <div class="form-group">
          <label>交易日期</label>
          <input type="date" v-model="transaction.transaction_date" required @change="fetchHistoricalNav">
        </div>
        <div class="form-group">
          <label>交易金额</label>
          <input type="number" step="0.01" v-model="transaction.amount" required @input="calculateFee">
        </div>
        <div class="form-group">
          <label>基金净值</label>
          <input type="number" step="0.0001" v-model="transaction.nav" disabled>
        </div>
        <div class="form-group">
          <label>手续费率 (%)</label>
          <input type="number" step="0.01" v-model="displayFeeRate" disabled>
        </div>
        <div class="form-group">
          <label>手续费</label>
          <input type="number" step="0.01" v-model="transaction.fee" disabled>
        </div>
        <div class="form-group">
          <label>预计份额</label>
          <input type="number" step="0.01" v-model="transaction.shares" disabled>
        </div>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" native-type="submit" :disabled="!isFormValid">提交</el-button>
        </div>
      </form>
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
      displayFeeRate: 0
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
.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 8px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

.input-with-button {
  display: flex;
  gap: 10px;
}

.input-with-button input {
  flex: 1;
}

.dialog-footer {
  margin-top: 20px;
  text-align: right;
}
</style>
