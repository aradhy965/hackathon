# from flask import Flask, request, jsonify, send_from_directory
# import os
# import uuid
# import time

# app = Flask(__name__)

# UPLOAD_FOLDER = "uploads"
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# data_store = {}

# @app.route('/analyze', methods=['POST'])
# def analyze():
#     try:
#         # ✅ get file
#         file = request.files.get('file')

#         if not file:
#             return jsonify({"error": "No file provided"}), 400

#         if file.filename.strip() == "":
#             return jsonify({"error": "Empty filename"}), 400

#         # ✅ create unique file
#         req_id = str(uuid.uuid4())
#         filename = req_id + "_" + file.filename

#         filepath = os.path.join(os.getcwd(), UPLOAD_FOLDER, filename)

#         # ✅ save file safely
#         try:
#             file.save(filepath)
#         except Exception as e:
#             return jsonify({"error": "File save failed", "details": str(e)}), 500

#         # ✅ store data
#         data_store[req_id] = {
#             "filename": filename,
#             "status": "pending",
#             "result": None
#         }

#         # ⏳ wait max 25 sec (Render safe)
#         for _ in range(25):
#             if data_store[req_id]["status"] == "done":
#                 return jsonify({
#                     "filename": filename,
#                     "result": data_store[req_id]["result"]
#                 })
#             time.sleep(1)

#         # ⏱️ not completed
#         return jsonify({
#             "filename": filename,
#             "status": "pending",
#             "message": "User did not respond in time"
#         })

#     except Exception as e:
#         print("🔥 SERVER ERROR:", str(e))
#         return jsonify({
#             "error": "Internal Server Error",
#             "details": str(e)
#         }), 500


# # 📥 pending items for UI
# @app.route('/data')
# def get_data():
#     try:
#         return jsonify([
#             {"id": rid, "filename": item["filename"]}
#             for rid, item in data_store.items()
#             if item["status"] == "pending"
#         ])
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# # 📤 review API
# @app.route('/review')
# def review():
#     try:
#         rid = request.args.get("id")
#         label = request.args.get("label")

#         if not rid or not label:
#             return "missing params"

#         if rid in data_store:
#             data_store[rid]["status"] = "done"
#             data_store[rid]["result"] = label
#             return "ok"

#         return "not found"

#     except Exception as e:
#         return f"error: {str(e)}"


# # 🏠 simple UI
# @app.route('/')
# def home():
#     return """
#     <html>
#     <body>

#     <h2>📸 Review Panel</h2>
#     <div id="container"></div>

#     <script>
#     async function loadData() {
#         try {
#             let res = await fetch("/data");
#             let data = await res.json();

#             let container = document.getElementById("container");
#             container.innerHTML = "";

#             if (data.length === 0) {
#                 container.innerHTML = "No pending files";
#                 return;
#             }

#             data.forEach(item => {
#                 let div = document.createElement("div");

#                 div.innerHTML = `
#                     <img src="/media/${item.filename}" width="300"><br>

#                     <button onclick="review('${item.id}', 'deepfake')">
#                         Deepfake
#                     </button>

#                     <button onclick="review('${item.id}', 'not_deepfake')">
#                         Not Deepfake
#                     </button>

#                     <hr>
#                 `;

#                 container.appendChild(div);
#             });

#         } catch (err) {
#             console.log("Error loading data", err);
#         }
#     }

#     async function review(id, label) {
#         try {
#             await fetch(`/review?id=${id}&label=${label}`);
#             loadData();
#         } catch (err) {
#             console.log("Review error", err);
#         }
#     }

#     setInterval(loadData, 2000);
#     loadData();
#     </script>

#     </body>
#     </html>
#     """


# # 📸 serve uploaded images
# @app.route('/media/<filename>')
# def media(filename):
#     try:
#         return send_from_directory(UPLOAD_FOLDER, filename)
#     except Exception as e:
#         return jsonify({"error": str(e)}), 404
# # 🚀 run
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)



from flask import Flask, request, jsonify, send_from_directory
import os
import uuid
import time
import threading

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

data_store = {}

# 🔥 background timeout handler
def wait_for_result(req_id):
    for _ in range(25):
        if data_store[req_id]["status"] == "done":
            return
        time.sleep(1)
    data_store[req_id]["status"] = "timeout"


# 🔥 MAIN API (single call feel)
@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        file = request.files.get('file')

        if not file:
            return jsonify({"error": "No file"}), 400

        if file.filename.strip() == "":
            return jsonify({"error": "Empty filename"}), 400

        req_id = str(uuid.uuid4())
        filename = req_id + "_" + file.filename

        filepath = os.path.join(os.getcwd(), UPLOAD_FOLDER, filename)
        file.save(filepath)

        data_store[req_id] = {
            "filename": filename,
            "status": "pending",
            "result": None
        }

        # 🔥 background thread → UI free rahegi
        threading.Thread(target=wait_for_result, args=(req_id,)).start()

        # 🔥 WAIT (max 20 sec → user ko single call feel)
        start = time.time()
        while time.time() - start < 20:
            if data_store[req_id]["status"] == "done":
                return jsonify({
                    "filename": filename,
                    "result": data_store[req_id]["result"]
                })
            time.sleep(1)

        # 🔥 agar user late hai
        return jsonify({
            "filename": filename,
            "result": "not_reviewed_in_time"
        })

    except Exception as e:
        print("🔥 ERROR:", str(e))
        return jsonify({"error": str(e)}), 500


# 📥 UI ke liye pending data
@app.route('/data')
def get_data():
    return jsonify([
        {"id": rid, "filename": item["filename"]}
        for rid, item in data_store.items()
        if item["status"] == "pending"
    ])


# 📤 review API
@app.route('/review')
def review():
    rid = request.args.get("id")
    label = request.args.get("label")

    if rid in data_store:
        data_store[rid]["status"] = "done"
        data_store[rid]["result"] = label
        return "ok"

    return "not found"


# 🏠 UI (REAL-TIME AUTO UPDATE 🔥)
@app.route('/')
def home():
    return """
    <html>
    <body>

    <h2>📸 Review Panel</h2>
    <div id="container"></div>

    <script>
    async function loadData() {
        try {
            let res = await fetch("/data");
            let data = await res.json();

            let container = document.getElementById("container");
            container.innerHTML = "";

            if (data.length === 0) {
                container.innerHTML = "<h3>No pending files</h3>";
                return;
            }

            data.forEach(item => {
                let div = document.createElement("div");

                div.innerHTML = `
                    <img src="/media/${item.filename}" width="300"><br>

                    <button onclick="review('${item.id}', 'deepfake')">
                        Deepfake
                    </button>

                    <button onclick="review('${item.id}', 'not_deepfake')">
                        Not Deepfake
                    </button>

                    <hr>
                `;

                container.appendChild(div);
            });

        } catch (err) {
            console.log("Error:", err);
        }
    }

    async function review(id, label) {
        await fetch(`/review?id=${id}&label=${label}`);
    }

    // 🔥 FAST AUTO REFRESH (1 sec)
    setInterval(loadData, 1000);

    loadData();
    </script>

    </body>
    </html>
    """


# 📸 serve uploaded images
@app.route('/media/<filename>')
def media(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# 🚀 run
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
