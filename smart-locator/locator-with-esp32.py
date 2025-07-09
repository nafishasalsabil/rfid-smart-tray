import gradio as gr
import time
import threading
import requests

# Simulated Inventory
inventory = [
    {"sku": "KRT123", "size": "M", "rack": "Rack 1"},
    {"sku": "KRT123", "size": "L", "rack": "Rack 2"},
    {"sku": "KRT456", "size": "S", "rack": "Rack 3"},
    {"sku": "KRT789", "size": "M", "rack": "Rack 4"},
    {"sku": "KRT999", "size": "XL", "rack": "Rack 5"},
]

rack_ids = ["Rack 1", "Rack 2", "Rack 3", "Rack 4", "Rack 5"]
rack_status = {rack: False for rack in rack_ids}
lock = threading.Lock()

# Replace these with actual IPs of each ESP32 rack
rack_to_ip = {
    "Rack 1": "http://192.168.0.101/blink",
    "Rack 2": "http://192.168.0.102/blink",
    "Rack 3": "http://192.168.0.103/blink",
    "Rack 4": "http://192.168.0.104/blink",
    "Rack 5": "http://192.168.0.105/blink",
}

def locate_item(sku, size):
    rack_found = None
    for item in inventory:
        if item["sku"].lower() == sku.lower() and item["size"].lower() == size.lower():
            rack_found = item["rack"]
            break

    if not rack_found:
        return "❌ Item not found.", render_racks()

    # Blink on-screen + real hardware
    def blink():
        with lock:
            rack_status[rack_found] = True
        try:
            requests.get(rack_to_ip[rack_found], timeout=1)
        except:
            print(f"⚠️ Could not reach ESP32 for {rack_found}")
        time.sleep(3)
        with lock:
            rack_status[rack_found] = False

    threading.Thread(target=blink).start()
    return f"✅ Item found in {rack_found}", render_racks()

def render_racks():
    return [[rack, "🟢" if rack_status[rack] else "⚪"] for rack in rack_ids]

with gr.Blocks() as demo:
    gr.Markdown("## 🧥 RFID Smart Rack Locator Simulation")
    sku = gr.Textbox(label="Enter SKU", placeholder="e.g., KRT123")
    size = gr.Dropdown(choices=["S", "M", "L", "XL"], label="Select Size")
    locate = gr.Button("Locate Item")

    output = gr.Textbox(label="Result")
    table = gr.Dataframe(headers=["Rack", "Status"], datatype=["str", "str"], interactive=False)

    locate.click(fn=locate_item, inputs=[sku, size], outputs=[output, table])
    demo.load(fn=render_racks, inputs=None, outputs=table)

demo.launch()
