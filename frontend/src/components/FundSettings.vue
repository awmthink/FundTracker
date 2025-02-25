<template>
  <div>
    <el-dialog
      title="基金设置"
      v-model="dialogVisible"
      width="800px"
      :close-on-click-modal="false"
      :destroy-on-close="true"
    >
      <div class="fund-settings">
        <!-- 基金列表表格 -->
        <el-table 
          :data="funds" 
          style="width: 100%; margin-bottom: 20px"
          max-height="400px"
          border
        >
          <el-table-column 
            prop="fund_code" 
            label="基金代码" 
            width="120" 
            align="center"
          />
          <el-table-column 
            prop="fund_name" 
            label="基金名称" 
            min-width="250" 
            align="center"
          />
          <el-table-column 
            label="买入费率(%)" 
            width="120" 
            align="center"
          >
            <template #default="scope">
              {{ scope.row.buy_fee }}
            </template>
          </el-table-column>
          <el-table-column 
            label="操作" 
            width="150" 
            align="center"
          >
            <template #default="scope">
              <el-button size="small" type="primary" @click="editFund(scope.row)">
                编辑
              </el-button>
              <el-button size="small" type="danger" @click="handleDelete(scope.row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 添加/编辑基金表单 -->
        <el-form
          ref="fundForm"
          :model="currentFund"
          :rules="rules"
          label-width="120px"
          style="max-width: 500px; margin: 0 auto;"
        >
          <el-form-item label="基金代码" prop="fund_code">
            <el-input 
              v-model="currentFund.fund_code" 
              style="width: 180px"
              @blur="handleFundCodeBlur"
            />
          </el-form-item>
          
          <el-form-item label="基金名称" prop="fund_name">
            <el-input 
              v-model="currentFund.fund_name" 
              style="width: 300px"
              disabled
              placeholder="基金名称将自动获取"
            >
              <template #append>
                <el-button 
                  v-if="currentFund.fund_code && !currentFund.fund_name"
                  @click="handleFundCodeBlur"
                  :loading="loadingFundInfo"
                >
                  重新获取
                </el-button>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item label="买入费率(%)" prop="buy_fee">
            <el-input-number
              v-model="currentFund.buy_fee"
              :precision="4"
              :step="0.0001"
              :min="0"
              :max="5"
              style="width: 180px"
            />
          </el-form-item>
        </el-form>

        <div class="dialog-footer" style="text-align: center; margin-top: 20px;">
          <el-button @click="handleCancel">取消</el-button>
          <el-button type="primary" @click="saveFundSettings">保存</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { fundApi } from '../services/api'

export default {
  name: 'FundSettings',
  data() {
    return {
      dialogVisible: false,
      funds: [],
      currentFund: {
        fund_code: '',
        fund_name: '',
        buy_fee: 0,
      },
      isEditing: false,
      rules: {
        fund_code: [
          { required: true, message: '请输入基金代码', trigger: 'blur' },
          { pattern: /^\d{6}$/, message: '请输入6位数字的基金代码', trigger: 'blur' }
        ],
        fund_name: [
          { required: true, message: '基金名称不能为空', trigger: 'blur' }
        ],
        buy_fee: [
          { required: true, message: '请输入买入费率', trigger: 'blur' }
        ],
      },
      loading: false,
      loadingFundInfo: false,
    }
  },
  methods: {
    async loadFundSettings() {
      this.loading = true;
      try {
        const response = await fundApi.getAllFundSettings();
        if (response.data.status === 'success') {
          // 转换费率为百分比，只获取需要的字段
          this.funds = response.data.data.map(fund => ({
            fund_code: fund.fund_code,
            fund_name: fund.fund_name,
            buy_fee: (fund.buy_fee * 100).toFixed(4)
          }));
        } else {
          throw new Error(response.data.message || '未知错误');
        }
      } catch (error) {
        console.error('加载基金设置失败:', error);
        this.$message.error(`加载基金设置失败: ${error.message}`);
      } finally {
        this.loading = false;
      }
    },
    showDialog() {
      this.dialogVisible = true;
      this.loadFundSettings(); // 打开对话框时加载数据
    },
    async fetchFundInfo() {
      if (!this.currentFund.fund_code) return
      
      try {
        const response = await fundApi.getFundNav(this.currentFund.fund_code)
        if (response.data.status === 'success') {
          this.currentFund.fund_name = response.data.data.name
        }
      } catch (error) {
        this.$message.error('获取基金信息失败')
      }
    },
    editFund(fund) {
      this.isEditing = true
      this.currentFund = {
        fund_code: fund.fund_code,
        fund_name: fund.fund_name,
        buy_fee: parseFloat(fund.buy_fee)
      };
    },
    async handleDelete(fund) {
      try {
        await this.$confirm('确认删除该基金设置吗？')
        await fundApi.deleteFundSettings(fund.fund_code)
        this.$message.success('删除成功')
        this.loadFundSettings()
      } catch (error) {
        if (error !== 'cancel') {
          this.$message.error('删除失败')
        }
      }
    },
    async saveFundSettings() {
      try {
        if (!this.currentFund.fund_name) {
          this.$message.error('请先获取基金信息');
          return;
        }

        const fundData = {
          ...this.currentFund,
          buy_fee: this.currentFund.buy_fee / 100
        };
        
        const response = await fundApi.saveFundSettings(fundData);
        if (response.data.status === 'success') {
          this.$message.success('保存成功');
          await this.loadFundSettings();
          this.resetForm();
          this.dialogVisible = false;
        } else {
          throw new Error(response.data.message || '未知错误');
        }
      } catch (error) {
        console.error('保存基金设置失败:', error);
        this.$message.error(`保存失败: ${error.message}`);
      }
    },
    resetForm() {
      this.currentFund = {
        fund_code: '',
        fund_name: '',
        buy_fee: 0,
      };
      if (this.$refs.fundForm) {
        this.$refs.fundForm.resetFields();
      }
    },
    async handleFundCodeBlur() {
      const fundCode = this.currentFund.fund_code.trim();
      if (!fundCode) return;
      
      // 检查基金代码格式
      if (!/^\d{6}$/.test(fundCode)) {
        this.$message.warning('请输入6位数字的基金代码');
        return;
      }

      this.loadingFundInfo = true;
      try {
        const response = await fundApi.getFundNav(fundCode);
        if (response.data.status === 'success') {
          this.currentFund.fund_name = response.data.data.name;
        } else {
          this.$message.warning('未找到该基金信息');
          this.currentFund.fund_name = '';
        }
      } catch (error) {
        console.error('获取基金信息失败:', error);
        this.$message.error('获取基金信息失败');
        this.currentFund.fund_name = '';
      } finally {
        this.loadingFundInfo = false;
      }
    },
    handleCancel() {
      this.resetForm();
      this.dialogVisible = false;
    },
  },
  mounted() {
    // 组件挂载时不自动加载数据，而是等待对话框打开时加载
  }
}
</script>

<style scoped>
.fund-settings {
  padding: 20px;
}

.el-form {
  margin-top: 30px;
  border-top: 1px solid #eee;
  padding-top: 30px;
}

:deep(.el-dialog__body) {
  padding: 0;
}

:deep(.el-table) {
  margin-bottom: 30px;
}

:deep(.el-form-item) {
  margin-bottom: 22px;
}

:deep(.el-input.is-disabled .el-input__inner) {
  color: #606266;  /* 让禁用状态的输入框文字颜色更清晰 */
}
</style> 