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
    addTransaction: async (data) => {
        try {
            return await axiosInstance.post('/fund/transaction', data);
        } catch (error) {
            console.error('添加交易失败:', error);
            throw error;
        }
    },
    getHoldings: async () => {
        try {
            return await axiosInstance.get('/fund/holdings');
        } catch (error) {
            console.error('获取持仓失败:', error);
            throw error;
        }
    },
    updateNav: async (data) => {
        try {
            return await axiosInstance.post('/fund/update-nav', data);
        } catch (error) {
            console.error('更新净值失败:', error);
            throw error;
        }
    },
    getFundNav: async (fundCode) => {
        try {
            console.log('Requesting fund info for:', fundCode);
            const response = await axiosInstance.get(`/fund/nav/${fundCode}`);
            console.log('Fund info response:', response);
            return response;
        } catch (error) {
            console.error('获取基金信息失败:', error.response || error);
            throw error;
        }
    },

    getFundSettings: async () => {
        try {
            return await axiosInstance.get('/fund/settings');
        } catch (error) {
            console.error('获取基金设置失败:', error);
            throw error;
        }
    },

    getAllFundSettings: async () => {
        try {
            const response = await axiosInstance.get('/fund/settings');
            console.log('API Response:', response);
            return response;
        } catch (error) {
            console.error('获取基金设置失败:', error);
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

    getHistoricalNav: async (fundCode, date) => {
        try {
            return await axiosInstance.get(`/fund/historical-nav/${fundCode}/${date}`);
        } catch (error) {
            console.error('获取历史净值失败:', error);
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

    // 获取最新净值
    getCurrentNav: async (fundCode) => {
        try {
            return await axiosInstance.get(`/fund/current-nav/${fundCode}`);
        } catch (error) {
            console.error('获取最新净值失败:', error);
            throw error;
        }
    },
    
    // 更新所有基金的最新净值
    updateAllNavs: async () => {
        try {
            return await axiosInstance.post('/fund/update-all-navs');
        } catch (error) {
            console.error('更新所有净值失败:', error);
            throw error;
        }
    }
};
