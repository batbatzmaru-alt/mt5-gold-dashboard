# --- ตัวแปรตั้งค่าระบบและความปลอดภัย ---
system_config = {
    "pin": "000013"  # รหัส PIN เริ่มต้น (สามารถเปลี่ยนผ่านหน้าเว็บได้)
}

ea_control_states = {
    "emergency_stop_all": False,
    "accounts": {}  # เก็บสถานะแต่ละพอร์ต เช่น { "12345678": "RUNNING" หรือ "STOPPED" }
}

# 1. API สำหรับสลับสถานะ EA (เปิด/ปิด) แยกตามพอร์ต
@app.route('/api/ea/toggle/<account_id>', methods=['POST'])
def toggle_ea(account_id):
    data = request.get_json() or {}
    pin = data.get("pin", "")
    
    if pin != system_config["pin"]:
        return jsonify({"status": "error", "message": "❌ รหัส PIN ไม่ถูกต้อง! ไม่อนุญาตให้ดำเนินการ"}), 403

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

# 2. API สำหรับสั่งปิด EA ทุกพอร์ตฉุกเฉินพร้อมกัน
@app.route('/api/ea/stop_all', methods=['POST'])
def stop_all_ea():
    data = request.get_json() or {}
    pin = data.get("pin", "")
    
    if pin != system_config["pin"]:
        return jsonify({"status": "error", "message": "❌ รหัส PIN ไม่ถูกต้อง! ไม่อนุญาตให้ดำเนินการ"}), 403

    ea_control_states["emergency_stop_all"] = True
    for acc in ea_control_states["accounts"]:
        ea_control_states["accounts"][acc] = "STOPPED"
        
    return jsonify({
        "status": "success", 
        "message": "🚨 ส่งสัญญาณปิดฉุกเฉิน (Emergency Stop) ทุกพอร์ตเรียบร้อยแล้ว!"
    })

# 3. API สำหรับเปลี่ยนรหัส PIN ผ่านหน้าเว็บ
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

# 4. API ให้ EA ใน MT5 วิ่งเข้ามาเช็คสถานะทุกรอบ
@app.route('/api/ea/status/<account_id>', methods=['GET'])
def get_ea_status(account_id):
    if ea_control_states["emergency_stop_all"]:
        return jsonify({"state": "STOPPED"})
    
    if account_id not in ea_control_states["accounts"]:
        ea_control_states["accounts"][account_id] = "RUNNING"
        
    return jsonify({"state": ea_control_states["accounts"][account_id]})
