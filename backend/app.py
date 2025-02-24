from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)

# 启用调试模式
app.debug = True

# 简化 CORS 配置
CORS(app, resources={r"/*": {"origins": "*"}})

# 注册路由
from routes.fund import fund_bp
app.register_blueprint(fund_bp, url_prefix='/api/fund')

# 测试路由
@app.route('/')
def index():
    return jsonify({
        'status': 'success',
        'message': 'Flask server is running'
    })

if __name__ == '__main__':
    # 修改端口为 5001
    app.run(host='0.0.0.0', port=5001, debug=True)
