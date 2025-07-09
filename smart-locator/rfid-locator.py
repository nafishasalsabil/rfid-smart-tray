import gradio as gr
import time
import threading

# Mock inventory of products and rack locations
inventory = [
    {"sku": "KRT123", "size": "M", "rack": "Rack 1"},
    {"sku": "KRT123", "size": "L", "rack": "Rack 2"},
    {"sku": "KRT456", "size": "S", "rack": "Rack 3"},
    {"sku": "KRT789", "size": "M", "rack": "Rack 4"},
    {"sku": "KRT999", "size": "XL", "rack": "Rack 5"},
]

# Track which rack is "blinking"
rack_ids = ["Rack 1", "Rack 2", "Rack 3", "Rack 4", "Rack 5"]
rack_status = {rack: False for rack in rack_ids}
lock = threading.Lock()

def locate_item(sku, size):
    rack_found = None
    for item in inventory:
        if item["sku"].lower() == sku.lower() and item["size"].lower() == size.lower():
            rack_found = item["rack"]
            break

    if not rack_found:
        return "❌ Item not found.", render_racks()

    # Trigger blinking status
    def blink():
        with lock:
            rack_status[rack_found] = True
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
