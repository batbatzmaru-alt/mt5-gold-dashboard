from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --- ตัวแปรตั้งค่าความปลอดภัยและความจำข้อมูลระบบ ---
system_config = {
    "pin": "000013"
}

ea_control_states = {
    "emergency_stop_all": False,
    "accounts": {},        # { "12345678": "RUNNING" หรือ "STOPPED" }
    "close_positions": {}  # { "12345678": True หรือ False }
}

global_data = {
    "combined": {
        "balance": 0.0,
        "equity": 0.0,
        "floating_profit": 0.0,
        "margin": 0.0,
        "currency": "USD",
        "deals": []
    },
    "accounts": {}
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/update', methods=['POST'])
def update_data():
    global global_data
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
    
    acc_id = str(data.get("account_id"))
    global_data["accounts"][acc_id] = data
    
    total_balance = sum(acc.get("balance", 0) for acc in global_data["accounts"].values())
    total_equity = sum(acc.get("equity", 0) for acc in global_data["accounts"].values())
    total_floating = sum(acc.get("floating_profit", 0) for acc in global_data["accounts"].values())
    
    all_deals = []
    for acc in global_data["accounts"].values():
        all_deals.extend(acc.get("deals", []))
        
    global_data["combined"] = {
        "balance": total_balance,
        "equity": total_equity,
        "floating_profit": total_floating,
        "margin": 0.0,
        "currency": "USD",
        "deals": all_deals
    }
    
    return jsonify({"status": "success"})

@app.route('/api/data', methods=['GET'])
def get_data():
    response_data = global_data.copy()
    response_data["ea_control"] = ea_control_states
    return jsonify(response_data)

@app.route('/api/ea/toggle/<account_id>', methods=['POST'])
def toggle_ea(account_id):
    data = request.get_json() or {}
    pin = data.get("pin", "")
    
    if pin != system_config["pin"]:
        return jsonify({"status": "error", "message": "❌ รหัส PIN ไม่ถูกต้อง!"}), 403

    if ea_control_states["emergency_stop_all"]:
        ea_control_states["emergency_stop_all"] = False

    if account_id not in ea_control_states["accounts"]:
        ea_control_states["accounts"][account_id] = "RUNNING"
    
    current = ea_control_states["accounts"][account_id]
    new_status = "STOPPED" if current == "RUNNING" else "RUNNING"
    ea_control_states["accounts"][account_id] = new_status
    
    return jsonify({
        "status": "success", 
        "account": account_id, 
        "ea_state": new_status, 
        "message": f"เปลี่ยนสถานะ EA พอร์ต {account_id} เป็น {new_status} เรียบร้อยแล้ว"
    })

@app.route('/api/ea/close_positions/<account_id>', methods=['POST'])
def trigger_close_positions(account_id):
    data = request.get_json() or {}
    pin = data.get("pin", "")

    if pin != system_config["pin"]:
        return jsonify({"status": "error", "message": "❌ รหัส PIN ไม่ถูกต้อง!"}), 403

    if account_id == "combined":
        for acc in list(global_data["accounts"].keys()):
            ea_control_states["close_positions"][acc] = True
        return jsonify({
            "status": "success",
            "message": "⚡ ส่งคำสั่ง Close All Position ไปยังทุกพอร์ตแล้ว!"
        })

    ea_control_states["close_positions"][account_id] = True
    return jsonify({
        "status": "success",
        "message": f"⚡ ส่งคำสั่ง Close All Position สำหรับพอร์ต {account_id} แล้ว!"
    })

@app.route('/api/ea/ack_close/<account_id>', methods=['POST'])
def ack_close_positions(account_id):
    ea_control_states["close_positions"][account_id] = False
    return jsonify({"status": "success"})

@app.route('/api/ea/stop_all', methods=['POST'])
def stop_all_ea():
    data = request.get_json() or {}
    pin = data.get("pin", "")
    
    if pin != system_config["pin"]:
        return jsonify({"status": "error", "message": "❌ รหัส PIN ไม่ถูกต้อง!"}), 403

    ea_control_states["emergency_stop_all"] = True
    for acc in ea_control_states["accounts"]:
        ea_control_states["accounts"][acc] = "STOPPED"
        
    return jsonify({
        "status": "success", 
        "message": "🚨 ส่งสัญญาณปิดฉุกเฉินทุกพอร์ตเรียบร้อยแล้ว!"
    })

@app.route('/api/ea/change_pin', methods=['POST'])
def change_pin():
    data = request.get_json() or {}
    old_pin = data.get("old_pin", "")
    new_pin = data.get("new_pin", "")
    
    if old_pin != system_config["pin"]:
        return jsonify({"status": "error", "message": "❌ รหัส PIN เดิมไม่ถูกต้อง!"}), 400
        
    if len(new_pin) != 6 or not new_pin.isdigit():
        return jsonify({"status": "error", "message": "❌ รหัส PIN ใหม่ต้องเป็นตัวเลข 6 หลักเท่านั้น!"}), 400
        
    system_config["pin"] = new_pin
    return jsonify({"status": "success", "message": "✅ เปลี่ยนรหัส PIN สำเร็จแล้ว!"})

@app.route('/api/ea/remove/<account_id>', methods=['POST'])
def remove_account(account_id):
    data = request.get_json() or {}
    pin = data.get("pin", "")
    
    if pin != system_config["pin"]:
        return jsonify({"status": "error", "message": "❌ รหัส PIN ไม่ถูกต้อง!"}), 403

    if account_id in global_data["accounts"]:
        del global_data["accounts"][account_id]
        
    if account_id in ea_control_states["accounts"]:
        del ea_control_states["accounts"][account_id]

    if account_id in ea_control_states["close_positions"]:
        del ea_control_states["close_positions"][account_id]
        
    total_balance = sum(acc.get("balance", 0) for acc in global_data["accounts"].values())
    total_equity = sum(acc.get("equity", 0) for acc in global_data["accounts"].values())
    total_floating = sum(acc.get("floating_profit", 0) for acc in global_data["accounts"].values())
    
    all_deals = []
    for acc in global_data["accounts"].values():
        all_deals.extend(acc.get("deals", []))
        
    global_data["combined"] = {
        "balance": total_balance,
        "equity": total_equity,
        "floating_profit": total_floating,
        "margin": 0.0,
        "currency": "USD",
        "deals": all_deals
    }
    
    return jsonify({"status": "success", "message": f"🗑️ ลบพอร์ต {account_id} ออกจากระบบเรียบร้อยแล้ว"})

@app.route('/api/ea/status/<account_id>', methods=['GET'])
def get_ea_status(account_id):
    state = "STOPPED" if ea_control_states["emergency_stop_all"] else ea_control_states["accounts"].get(account_id, "RUNNING")
    if account_id not in ea_control_states["accounts"] and not ea_control_states["emergency_stop_all"]:
        ea_control_states["accounts"][account_id] = "RUNNING"
    close_flag = bool(ea_control_states["close_positions"].get(account_id, False))
    return jsonify({"state": state, "close_positions": close_flag})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
