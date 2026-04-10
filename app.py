from flask import Flask, request, jsonify, send_from_directory
import os
import uuid
import time

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

data_store = {}

# 🔥 MAIN API (single call)
@app.route('/analyze', methods=['POST'])
def analyze():
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file"}), 400

    req_id = str(uuid.uuid4())
    filename = req_id + "_" + file.filename

    file.save(os.path.join(UPLOAD_FOLDER, filename))

    data_store[req_id] = {
        "filename": filename,
        "status": "pending",
        "result": None
    }

    # ⏳ wait max 3 min
    for _ in range(180):
        if data_store[req_id]["status"] == "done":
            return jsonify({
                "filename": filename,
                "result": data_store[req_id]["result"]
            })
        time.sleep(1)

    return jsonify({"error": "timeout"}), 408


# 📥 API for frontend
@app.route('/data')
def get_data():
    return jsonify([
        {"id": rid, "filename": item["filename"]}
        for rid, item in data_store.items()
        if item["status"] == "pending"
    ])


# 📤 review (no redirect used by JS)
@app.route('/review')
def review():
    rid = request.args.get("id")
    label = request.args.get("label")

    if rid in data_store:
        data_store[rid]["status"] = "done"
        data_store[rid]["result"] = label
        return "ok"

    return "not found"


# 🏠 UI (NO redirect system)
@app.route('/')
def home():
    return """
    <html>
    <body>

    <h2>📸 Review Panel</h2>
    <div id="container"></div>

    <script>
    async function loadData() {
        let res = await fetch("/data");
        let data = await res.json();

        let container = document.getElementById("container");
        container.innerHTML = "";

        if (data.length === 0) {
            container.innerHTML = "No pending files";
            return;
        }

        data.forEach(item => {
            let div = document.createElement("div");
            div.style.marginBottom = "20px";

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
    }

    async function review(id, label) {
        await fetch(`/review?id=${id}&label=${label}`);
        loadData();
    }

    setInterval(loadData, 2000); // auto refresh
    loadData();
    </script>

    </body>
    </html>
    """


# 📸 serve image
@app.route('/media/<filename>')
def media(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
