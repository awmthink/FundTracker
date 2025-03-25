import axios from 'axios';

// 使用相对路径，让 Vite 代理处理请求
const API_BASE_URL = '/api';

// 创建 axios 实例
const axiosInstance = axios.create({
    baseURL: API_BASE_URL,
    timeout: 5000,  // 设置超时时间
    headers: {
        'Content-Type': 'application/json'
    }
});

// 添加请求拦截器
axiosInstance.interceptors.request.use(
    config => {
        console.log('发送请求:', config.url, config.data);
        return config;
    },
    error => {
        console.error('请求错误:', error);
        return Promise.reject(error);
    }
);

// 添加响应拦截器
axiosInstance.interceptors.response.use(
    response => {
        console.log('收到响应:', response.data);
        return response;
    },
    error => {
        console.error('响应错误:', error);
        if (error.code === 'ERR_NETWORK') {
            console.error('网络错误，请确保后端服务器正在运行');
        }
        return Promise.reject(error);
    }
);

export const fundApi = {
    // 基金基本信息相关接口
    getFundInfo: async (fundCode) => {
        try {
            return await axiosInstance.get(`/fund/funds/${fundCode}`);
        } catch (error) {
            console.error('获取基金信息失败:', error);
            throw error;
        }
    },

    // 净值相关接口
    getCurrentNav: async (fundCode) => {
        try {
            return await axiosInstance.get(`/fund/nav/${fundCode}`);
        } catch (error) {
            console.error('获取当前净值失败:', error);
            throw error;
        }
    },

    getHistoricalNav: async (fundCode, date) => {
        try {
            return await axiosInstance.get(`/fund/nav/${fundCode}/history/${date}`);
        } catch (error) {
            console.error('获取历史净值失败:', error);
            throw error;
        }
    },

    updateNav: async (fundCode, data) => {
        try {
            return await axiosInstance.post(`/fund/nav/${fundCode}`, data);
        } catch (error) {
            console.error('更新净值失败:', error);
            throw error;
        }
    },

    updateAllNavs: async (fundCodes = null) => {
        try {
            const data = fundCodes ? { fund_codes: fundCodes } : {};
            return await axiosInstance.post('/fund/nav/batch/update', data);
        } catch (error) {
            console.error('批量更新净值失败:', error);
            throw error;
        }
    },

    // 交易相关接口
    getTransactions: async (filters) => {
        try {
            const params = new URLSearchParams(filters);
            return await axiosInstance.get(`/fund/transactions?${params}`);
        } catch (error) {
            console.error('获取交易记录失败:', error);
            throw error;
        }
    },

    addTransaction: async (data) => {
        try {
            return await axiosInstance.post('/fund/transactions', data);
        } catch (error) {
            console.error('添加交易失败:', error);
            throw error;
        }
    },

    updateTransaction: async (transactionId, data) => {
        try {
            const updateData = {
                fund_code: data.fund_code,
                fund_name: data.fund_name,
                transaction_type: data.transaction_type,
                amount: parseFloat(data.amount),
                nav: parseFloat(data.nav),
                transaction_date: data.transaction_date
            };
            return await axiosInstance.put(`/fund/transactions/${transactionId}`, updateData);
        } catch (error) {
            console.error('更新交易记录失败:', error);
            throw error;
        }
    },

    deleteTransaction: async (transactionId) => {
        try {
            return await axiosInstance.delete(`/fund/transactions/${transactionId}`);
        } catch (error) {
            console.error('删除交易记录失败:', error);
            throw error;
        }
    },

    // 基金设置相关接口
    getAllFundSettings: async () => {
        try {
            return await axiosInstance.get('/fund/settings');
        } catch (error) {
            console.error('获取所有基金设置失败:', error);
            throw error;
        }
    },

    getFundFees: async (fundCode) => {
        try {
            return await axiosInstance.get(`/fund/settings/${fundCode}`);
        } catch (error) {
            console.error('获取基金费率失败:', error);
            throw error;
        }
    },

    saveFundSettings: async (data) => {
        try {
            return await axiosInstance.post('/fund/settings', data);
        } catch (error) {
            console.error('保存基金设置失败:', error);
            throw error;
        }
    },

    deleteFundSettings: async (fundCode) => {
        try {
            return await axiosInstance.delete(`/fund/settings/${fundCode}`);
        } catch (error) {
            console.error('删除基金设置失败:', error);
            throw error;
        }
    },

    // 持仓相关接口
    getHoldings: async (cutoffDate = null) => {
        try {
            const params = cutoffDate ? new URLSearchParams({ cutoff_date: cutoffDate }) : '';
            const url = `/fund/holdings${params ? '?' + params : ''}`;
            return await axiosInstance.get(url);
        } catch (error) {
            console.error('获取持仓信息失败:', error);
            throw error;
        }
    }
};

export default fundApi;
