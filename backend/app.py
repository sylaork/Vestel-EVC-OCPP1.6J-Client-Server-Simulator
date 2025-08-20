from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import logging
from flask_cors import CORS
import threading
import time
from flask import render_template
from backend.database import get_db_connection, init_database, DB_PATH
import random 
import os
# Flask
app = Flask(__name__, template_folder="../frontend/templates")
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OCPP_app")

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)


init_database()


# pages (main, logs)
@app.route("/")
def index(): 
    return render_template("index.html") 

@app.route("/logs")
def logs(): 
    return render_template("logs.html") 

@app.route("/evc-info")
def evc_info(): 
    return render_template("evc_info.html") 


# 12 different model
ALL_DEVICES = [
    {"cp_id":"VESTELEVC_101","vendor":"VendorA","model":"ModelX"},
    {"cp_id":"VESTELEVC_102","vendor":"VendorB","model":"ModelY"},
    {"cp_id":"VESTELEVC_103","vendor":"VendorC","model":"ModelZ"},
    {"cp_id":"VESTELEVC_104","vendor":"VendorD","model":"ModelA"},
    {"cp_id":"VESTELEVC_105","vendor":"VendorE","model":"ModelB"},
    {"cp_id":"VESTELEVC_106","vendor":"VendorF","model":"ModelG"},
    {"cp_id":"VESTELEVC_107","vendor":"VendorG","model":"ModelD"},
    {"cp_id":"VESTELEVC_108","vendor":"VendorH","model":"ModelE"},
    {"cp_id":"VESTELEVC_109","vendor":"VendorI","model":"ModelT"},
    {"cp_id":"VESTELEVC_110","vendor":"VendorJ","model":"ModelL"},
    {"cp_id":"VESTELEVC_111","vendor":"VendorK","model":"ModelS"},
    {"cp_id":"VESTELEVC_112","vendor":"VendorL","model":"ModelO"},
]

@app.route("/api/charge_points")
def get_charge_points():
    conn = get_db_connection()
    cps = conn.execute("SELECT * FROM charge_points ORDER BY cp_id").fetchall()

    # random 3 evc FROM DEVICES
    if not cps:  # if empty
        selected_devices = random.sample(ALL_DEVICES, 3)
        for dev in selected_devices:
            now = datetime.now()
            conn.execute(
                "INSERT INTO charge_points (cp_id,vendor,model,status,last_seen,busy,last_heartbeat) VALUES (?,?,?,?,?,?,?)",
                (dev["cp_id"], dev["vendor"], dev["model"], "Available", now.isoformat(), 0, now.isoformat())
            )
            conn.execute(
                "INSERT INTO boot_notifications (cp_id,vendor,model,timestamp) VALUES (?,?,?,?)",
                (dev["cp_id"], dev["vendor"], dev["model"], now.isoformat())
            )
        conn.commit()
        cps = conn.execute("SELECT * FROM charge_points ORDER BY cp_id").fetchall()

    # model info
    result = []
    for cp in cps:
        boot = conn.execute(
            "SELECT timestamp FROM boot_notifications WHERE cp_id=? ORDER BY timestamp DESC LIMIT 1",
            (cp["cp_id"],)
        ).fetchone()
        cp_dict = dict(cp)
        cp_dict["boot_timestamp"] = boot["timestamp"] if boot else None
        result.append(cp_dict)

    conn.close()
    return jsonify(result)

    '''
    
    #just 3 clients as a demo with different models 
    vendors = ["DemoVendorA", "DemoVendorB", "DemoVendorC"]
    models = ["ModelX", "ModelY", "ModelZ"]

    def generate_demo_cp():
        cp_id = "EVC_" + str(random.randint(1000, 9999))
        vendor = random.choice(vendors)
        model = random.choice(models)
        status = random.choice(["Available", "Charging", "SuspendedEVSE"])
        busy = 1 if status == "Charging" else 0
        last_seen = datetime.now() - timedelta(seconds=random.randint(0, 300))
        last_heartbeat = last_seen - timedelta(seconds=random.randint(5, 60))
        boot_timestamp = last_seen - timedelta(seconds=random.randint(10, 120))
        return {
            "cp_id": cp_id,
            "vendor": vendor,
            "model": model,
            "status": status,
            "busy": busy,
            "last_seen": last_seen,
            "last_heartbeat": last_heartbeat,
            "boot_timestamp": boot_timestamp
        }
    # generate 6 clients randomly 
    if not cps:
        demo_clients = [generate_demo_cp() for _ in range(6)]
        for cp in demo_clients:
            # insert it to boot table
            conn.execute(
                "INSERT INTO boot_notifications (cp_id, vendor, model, timestamp) VALUES (?,?,?,?)",
                (cp["cp_id"], cp["vendor"], cp["model"], cp["boot_timestamp"].isoformat())
            )
            # charge_points tablosuna ekle
            conn.execute(
                "INSERT OR REPLACE INTO charge_points (cp_id,vendor,model,status,last_seen,busy,last_heartbeat) VALUES (?,?,?,?,?,?,?)",
                (cp["cp_id"], cp["vendor"], cp["model"], cp["status"], cp["last_seen"].isoformat(), cp["busy"], cp["last_heartbeat"].isoformat())
            )
        conn.commit()
        cps = conn.execute("SELECT * FROM charge_points ORDER BY cp_id").fetchall()

    
    #info
    result = []
    for cp in cps:
        boot = conn.execute(
            "SELECT timestamp FROM boot_notifications WHERE cp_id=? ORDER BY timestamp DESC LIMIT 1",
            (cp["cp_id"],)
        ).fetchone()
        cp_dict = dict(cp)
        cp_dict["boot_timestamp"] = boot["timestamp"] if boot else None
        result.append(cp_dict)

    conn.close()
    return jsonify(result)
    
     
 # if you want to use just 3 clients as a demo
@app.route("/api/charge_points") #HTTP katmani @app.route
def get_charge_points(): #GET
    conn = get_db_connection() #charge_points tablossundaki bütün aletleri cek
    cps = conn.execute("SELECT * FROM charge_points ORDER BY cp_id").fetchall()

    if not cps:  # hiç kayıt yoksa 3 demo ekle
        demo_clients = [
            ("EVC_1","Demo","Model","Available"),
            ("EVC_2","Demo","Model","Available"),
            ("EVC_3","Demo","Model","Available")
        ] #amaç dashoard acildiginda bos gozukmesin
        for cp in demo_clients:
            conn.execute(
                "INSERT OR REPLACE INTO charge_points (cp_id,vendor,model,status,last_seen,busy,last_heartbeat) VALUES (?,?,?,?,?,?,?)",
                (cp[0], cp[1], cp[2], cp[3], datetime.now(), 0, None)
            )
        conn.commit()
        cps = conn.execute("SELECT * FROM charge_points ORDER BY cp_id").fetchall()

    conn.close()
    return jsonify([dict(cp) for cp in cps]) #dict cevir json gonder

'''
#sending command
@app.route("/api/send_command/<cp_id>", methods=["POST"]) #sending command with calling api
def send_command(cp_id): #which evc this command is going to
    cmd = request.json.get("command")
    status_map = {"start":"Charging","suspend":"SuspendedEVC","finish":"Available"}
    new_status = status_map.get(cmd,"Available")
    busy = 1 if cmd=="start" else 0

    conn = get_db_connection()
    conn.execute("UPDATE charge_points SET status=?, busy=?, last_seen=? WHERE cp_id=?",
                 (new_status, busy, datetime.now(), cp_id))
    conn.execute(
        "INSERT INTO status_notifications (cp_id,status,timestamp) VALUES (?,?,?)",
        (cp_id,new_status,datetime.now().isoformat())
    )
    conn.commit(); conn.close() #for updating the last thing

    logger.info(f"{cp_id} -> {cmd} -> {new_status} (busy={busy})")
    return jsonify({"status":"ok","new_status":new_status,"busy":busy})

@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    data = request.json or {}
    cp_id = data.get("cpId")

    if not cp_id:
        return jsonify({"error": "cpId missing"}), 400

    conn = get_db_connection()
    # update changes in the charge_points table for heartbeat
    conn.execute(
        "UPDATE charge_points SET last_heartbeat=?, last_seen=? WHERE cp_id=?",
        (datetime.now().isoformat(), datetime.now().isoformat(), cp_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "heartbeat received", "cpId": cp_id}), 200

#added new endpoint for evc info page 
@app.route("/api/evc_details")
def get_evc_details():
    conn = get_db_connection()
    cps = conn.execute("SELECT * FROM charge_points ORDER BY cp_id").fetchall()
    
    result = []
    for cp in cps:
        # Son heartbeat zamanını al
        last_heartbeat = conn.execute(
            "SELECT timestamp FROM heartbeats WHERE cp_id=? ORDER BY timestamp DESC LIMIT 1",
            (cp["cp_id"],)
        ).fetchone()
        
        # Son status değişikliğini al
        last_status = conn.execute(
            "SELECT timestamp, status FROM status_notifications WHERE cp_id=? ORDER BY timestamp DESC LIMIT 1",
            (cp["cp_id"],)
        ).fetchone()
        
        cp_dict = dict(cp)
        cp_dict["last_heartbeat_time"] = last_heartbeat["timestamp"] if last_heartbeat else None
        cp_dict["last_status_time"] = last_status["timestamp"] if last_status else None
        cp_dict["last_status_value"] = last_status["status"] if last_status else "Unknown"
        result.append(cp_dict)
    
    conn.close()
    return jsonify(result)

@app.route("/bootnotification", methods=["POST"])
def boot_notification():
    data = request.json or {}
    cp_id = data.get("cpId")
    vendor = data.get("chargePointVendor", "Unknown")
    model = data.get("chargePointModel", "Unknown")

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO boot_notifications (cp_id, vendor, model, timestamp) VALUES (?,?,?,?)",
        (cp_id, vendor, model, datetime.now().isoformat())
    )
    conn.execute(
        "INSERT OR REPLACE INTO charge_points (cp_id, vendor, model, status, last_seen, busy, last_heartbeat) VALUES (?,?,?,?,?,?,?)",
        (cp_id, vendor, model, "Available", datetime.now(), 0, None)
    )
    conn.commit(); conn.close()

    return jsonify({"status": "BootNotification stored"}), 200

@app.route("/statusnotification", methods=["POST"])
def status_notification():
    data = request.json
    cp_id = data.get("cpId")
    status = data.get("status", "Unknown")

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO status_notifications (cp_id, status, timestamp) VALUES (?,?,?)",
        (cp_id, status, datetime.now().isoformat())
    )
    conn.execute(
        "UPDATE charge_points SET status=?, last_seen=? WHERE cp_id=?",
        (status, datetime.now(), cp_id)
    )
    conn.commit(); conn.close()

    return jsonify({"status": "StatusNotification stored"}), 200


@app.route("/api/logs") #get all the info from message tables 
def get_logs():
    conn = get_db_connection()
    logs = []
    for row in conn.execute("SELECT cp_id,vendor||' '||model as message,timestamp FROM boot_notifications"):
        logs.append({"type":"BootNotification","cp_id":row["cp_id"],"message":row["message"],"timestamp":row["timestamp"]})
    for row in conn.execute("SELECT cp_id,'Heartbeat received' as message,timestamp FROM heartbeats"):
        logs.append({"type":"Heartbeat","cp_id":row["cp_id"],"message":row["message"],"timestamp":row["timestamp"]})
    for row in conn.execute("SELECT cp_id,'Status: '||status as message,timestamp FROM status_notifications"):
        logs.append({"type":"StatusNotification","cp_id":row["cp_id"],"message":row["message"],"timestamp":row["timestamp"]})
    conn.close()
    logs.sort(key=lambda x:x["timestamp"],reverse=True) #json--> first one goes to end
    return jsonify(logs)


def heartbeat_loop(): #which evc is active (avaliable)
    while True:
        try:
            conn = get_db_connection()
            now = datetime.now()
            clients = conn.execute("SELECT cp_id,busy,last_heartbeat FROM charge_points").fetchall()
            for c in clients:
                last_hb = c["last_heartbeat"]
                if c["busy"]==0 and (last_hb is None or datetime.fromisoformat(last_hb) + timedelta(seconds=60) <= now):
                    conn.execute("INSERT INTO heartbeats (cp_id,timestamp) VALUES (?,?)",
                                 (c["cp_id"], now.isoformat()))
                    conn.execute("UPDATE charge_points SET last_heartbeat=? WHERE cp_id=?",
                                 (now.isoformat(), c["cp_id"]))
                    logger.info(f"Heartbeat sent for {c['cp_id']}")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")
        time.sleep(10)  # control

threading.Thread(target=heartbeat_loop, daemon=True).start()
