from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --- ตัวแปรตั้งค่าความปลอดภัยและความจำข้อมูลระบบ ---
system_config = {
    "pin": "000013"  # รหัส PIN เริ่มต้น 6 หลัก
}

ea_control_states = {
    "emergency_stop_all": False,
    "accounts": {}  # เก็บสถานะแต่ละพอร์ต เช่น { "12345678": "RUNNING" หรือ "STOPPED" }
}

# ตัวแปรเก็บข้อมูลพอร์ตจาก MT5 สำหรับแสดงผลบนหน้า Dashboard
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

# 1. หน้าแรก Dashboard
@app.route('/')
def index():
    return render_template('index.html')

# 2. API รับข้อมูลจาก EA ใน MT5 (ส่งเข้ามาทุกๆ 3 วินาที)
@app.route('/api/update', methods=['POST'])
def update_data():
    global global_data
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
    
    acc_id = str(data.get("account_id"))
    global_data["accounts"][acc_id] = data
    
    # คำนวณรวมทุกพอร์ต (Combined) อัตโนมัติ
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

# 3. API ส่งข้อมูลให้หน้าเว็บ Dashboard ดึงไปแสดงผล
@app.route('/api/data', methods=['GET'])
def get_data():
    response_data = global_data.copy()
    response_data["ea_control"] = ea_control_states
    return jsonify(response_data)

# 4. API สลับสถานะ EA แยกตามพอร์ต (แก้ไขให้ปลดล็อก emergency_stop_all อัตโนมัติ)
@app.route('/api/ea/toggle/<account_id>', methods=['POST'])
def toggle_ea(account_id):
    data = request.get_json() or {}
    pin = data.get("pin", "")
    
    if pin != system_config["pin"]:
        return jsonify({"status": "error", "message": "❌ รหัส PIN ไม่ถูกต้อง!"}), 403

    # หากเคยถูกล็อกด้วยปุ่ม "ปิดทั้งหมด" ให้ปลดล็อกออกเมื่อมีการกดใช้งานรายพอร์ต
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

# 5. API สั่งปิด EA ทุกพอร์ตฉุกเฉิน พร้อมตรวจสอบ PIN
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

# 6. API เปลี่ยนรหัส PIN ผ่านหน้าเว็บ
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

# 7. API ให้ EA ใน MT5 วิ่งเข้ามาเช็คสถานะทุกรอบ
@app.route('/api/ea/status/<account_id>', methods=['GET'])
def get_ea_status(account_id):
    if ea_control_states["emergency_stop_all"]:
        return jsonify({"state": "STOPPED"})
    
    if account_id not in ea_control_states["accounts"]:
        ea_control_states["accounts"][account_id] = "RUNNING"
        
    return jsonify({"state": ea_control_states["accounts"][account_id]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
