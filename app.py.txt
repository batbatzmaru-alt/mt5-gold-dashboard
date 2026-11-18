from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
accounts_data = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/update', methods=['POST'])
def update_data():
    global accounts_data
    content = request.json
    if content and 'account_id' in content:
        acc_id = str(content['account_id'])
        accounts_data[acc_id] = content
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error"}), 400

@app.route('/api/data', methods=['GET'])
def get_data():
    combined_balance = sum(acc.get("balance", 0) for acc in accounts_data.values())
    combined_equity = sum(acc.get("equity", 0) for acc in accounts_data.values())
    combined_floating = sum(acc.get("floating_profit", 0) for acc in accounts_data.values())
    combined_margin = sum(acc.get("margin", 0) for acc in accounts_data.values())

    combined_deals = []
    for acc in accounts_data.values():
        combined_deals.extend(acc.get("deals", []))

    combined_summary = {
        "balance": combined_balance,
        "equity": combined_equity,
        "floating_profit": combined_floating,
        "margin": combined_margin,
        "currency": "USD",
        "deals": combined_deals
    }
    return jsonify({"combined": combined_summary, "accounts": accounts_data})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)