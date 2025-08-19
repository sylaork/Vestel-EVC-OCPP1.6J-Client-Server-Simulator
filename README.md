
![IMG_8563](https://github.com/user-attachments/assets/0b3bf6af-47cb-401c-8f19-85343a0675e3)


# 🚗⚡VESTEL EVC OCPP 1.6-J Client Server Simulation  

**Vestel – Application Software Design Team | Internship Project**  

This project was developed during my internship at **Vestel**, within the **Application Software Design Team**, focusing on **EVC (Electric Vehicle Charger) technologies**.  

The main goal is to simulate the **end-to-end communication of OCPP 1.6-J protocol messages** between clients (EV chargers), a server, a backend API, and a Flask-based web dashboard.  

---

## 🎯 Project Goal  
Implementing and simulating the three core OCPP 1.6 messages:  

- **BootNotification** → Charger introduces itself to the system  
- **Heartbeat** → Charger sends a periodic alive signal  
- **StatusNotification** → Charger updates its charging status  

---

## 🧩 Project Components  

### 1️⃣ OCPP Client (`ocpp_client.py`) – *Python (asyncio, websockets, aiohttp)*  
- Establishes a **WebSocket connection** with the server  
- Sends **BootNotification** with charger info (vendor, model, firmware, etc.)  
- Sends **Heartbeat** automatically **every 60 seconds when idle**  
- Sends **StatusNotification** to simulate charging states (`Available`, `Charging`, `SuspendedEV`)  
- Dynamically updates heartbeat interval based on server response  
- Supports **multiple clients** (`EVC_101`, `EVC_102`, `EVC_103`) simultaneously  

---

### 2️⃣ OCPP Server (`ocpp_server.py`) – *Python (asyncio, websockets, aiohttp)*  
- Accepts **incoming WebSocket connections** from clients  
- Parses OCPP messages and logs them  
- Returns OCPP-compliant confirmations (`.conf` responses)  
- Forwards all messages asynchronously to the **REST API**  
- Supports **SSL/TLS secure WebSocket connections**  

➡️ Example response to BootNotification:  
```json
{
  "status": "Accepted",
  "currentTime": "2025-08-19T10:00:00Z",
  "interval": 60
}
```  

---

### 3️⃣ Backend API & Database (`app.py`) – *Python (Flask, SQLite)*  
- Developed with **Flask** as a lightweight REST API  
- Stores **BootNotification, Heartbeat, StatusNotification** logs in **SQLite**  
- Provides endpoints for the dashboard:  
  - `/api/charge_points` → list all connected chargers  
  - `/api/logs` → return all combined logs  
  - `/api/send_command/<cp_id>` → send remote commands (`start`, `suspend`, `finish`)  

📌 Additional Features:  
- **12 demo charger models** (with unique vendor & model info) are created at startup  
- If no chargers exist, the system **generates random IDs** and adds demo clients  
- Heartbeat messages are **only sent when charger is idle (busy=0)**  

---

### 4️⃣ Web Dashboard – *Flask + HTML *  
- Built with **Flask** and **HTML templates** 
- Displays connected chargers and their current state (status, last seen, last heartbeat)  
- Shows latest **BootNotification, Heartbeat, StatusNotification** timestamps  
- Logs every action performed in the interface (real-time integration with database)  
- Allows sending commands (Start/Stop Charging, Suspend) to each device  

---

## 🔄 Message Flow  

```
[Client] ---> BootNotification ---> [Server] ---> BootNotification.conf ---> [Backend]
[Client] ---> Heartbeat (every 60s if idle) ---> [Server] ---> Heartbeat.conf ---> [Backend]
[Client] ---> StatusNotification ---> [Server] ---> StatusNotification.conf ---> [Backend]
```

> 🔹 Heartbeat is only sent when the charger is idle.  
> 🔹 Demo system includes **12 different charger models**, and random IDs can be assigned if needed.  

---

## 🚀 Installation & Run  

To run the project, first clone the repository and install the required Python dependencies with `pip install -r requirements.txt`. Then, start the **OCPP Server** (`ocpp_server.py`) which listens for WebSocket connections, launch the **Backend API** (`app.py`) powered by Flask to handle REST endpoints and database operations, and finally run the **OCPP Clients** (`ocpp_client.py`) to simulate multiple EV chargers connecting to the system. Once all services are up, you can open the **Flask-based web dashboard** in your browser at `http://localhost:3000` to monitor connected chargers, view logs, and send commands.  

---

## 📊 Key Features  
✔ Multiple clients support (EVC_101, EVC_102, EVC_103 + random demo chargers)  
✔ **12 charger models with vendor & model info** preconfigured  
✔ **Heartbeat automatically sent every 60s only when idle**  
✔ Secure WebSocket via **SSL/TLS**  
✔ REST API built with **Flask** for data transfer  
✔ **SQLite**-based logging  
✔ Dashboard built with **Flask + HTML templates**  
✔ Every UI action is logged in the backend  
✔ Command support (start/suspend/finish charging)  

---

## 🛠️ Technologies Used  
- **Python** → asyncio, websockets, aiohttp  
- **Flask** → REST API + Web Dashboard  
- **SQLite** → lightweight database for logs  
- **HTML** → dashboard UI  
- **SSL/TLS** → secure WebSocket communication  

---

## 📌 Notes  
This project was developed during my internship at **Vestel** within the **Application Software Design Team**.  
The main focus was to:  
- Learn the **OCPP 1.6-J protocol**,  
- Implement an **end-to-end simulation** of its core messages,  
- Integrate clients, server, backend API, and a Flask-based web dashboard.  
