
import gradio as gr
import pandas as pd
import threading
import serial
import time

# -----------------------------
# Config
# -----------------------------
SERIAL_PORT = "/dev/ttyUSB0"  # Change to "COM3" for Windows
BAUD_RATE = 9600

product_db = {
    "EPC001": {"name": "Men's Tee", "price": 1290},
    "EPC002": {"name": "Jeans", "price": 1890},
    "EPC003": {"name": "Kurti", "price": 1150},
    "EPC004": {"name": "Formal Shirt", "price": 1490}
}

scanned_items = {}
discount = 0

# -----------------------------
# Billing Functions
# -----------------------------
def get_bill_df():
    rows = []
    for epc, item in scanned_items.items():
        total = item["price"] * item["qty"]
        rows.append([epc, item["name"], item["price"], item["qty"], total])
    return pd.DataFrame(rows, columns=["EPC", "Name", "Price", "Qty", "Total"])

def update_summary():
    df = get_bill_df()
    if df.empty:
        return "Subtotal: 0 BDT\nDiscount: 0 BDT\nTotal: 0 BDT"
    subtotal = df["Total"].sum()
    discount_amt = subtotal * (discount / 100)
    total = subtotal - discount_amt
    return f"Subtotal: {subtotal} BDT\nDiscount: {discount_amt:.0f} BDT\nTotal: {total:.0f} BDT"

def refresh_ui():
    return render_items(), update_summary()

def render_items():
    rows = []
    for epc, item in scanned_items.items():
        with gr.Row() as row:
            gr.Textbox(value=item['name'], label="Item", interactive=False)
            gr.Textbox(value=str(item['qty']), label="Qty", interactive=False)
            with gr.Row():
                gr.Button(value="➕", elem_id=f"inc-{epc}")
                gr.Button(value="➖", elem_id=f"dec-{epc}")
                gr.Button(value="❌", elem_id=f"rem-{epc}")
        rows.append(row)
    return gr.Group(rows)

# -----------------------------
# Action Functions
# -----------------------------
def scan_epc(epc):
    epc = epc.strip().upper()
    if not epc or epc not in product_db:
        return "⚠️ Invalid EPC tag", refresh_ui()
    if epc in scanned_items:
        return f"⚠️ Already in tray: {product_db[epc]['name']}", refresh_ui()
    scanned_items[epc] = {
        "name": product_db[epc]["name"],
        "price": product_db[epc]["price"],
        "qty": 1
    }
    return f"✅ Scanned: {product_db[epc]['name']}", refresh_ui()

def reset_tray():
    scanned_items.clear()
    return "🧹 Tray cleared!", refresh_ui()

def set_discount(p):
    global discount
    discount = p
    return update_summary()

# -----------------------------
# Serial Reader (Simulated)
# -----------------------------
def serial_reader():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
        print(f"✅ Connected to {SERIAL_PORT}")
        while True:
            if ser.in_waiting:
                epc = ser.readline().decode("utf-8").strip()
                print(f"🔍 Tag detected: {epc}")
                scan_epc(epc)
    except Exception as e:
        print(f"⚠️ Serial error: {e}")

# threading.Thread(target=serial_reader, daemon=True).start()

# -----------------------------
# Gradio UI
# -----------------------------
with gr.Blocks() as demo:
    gr.Markdown("# 🛒 RFID Smart Tray Billing")

    with gr.Row():
        epc_input = gr.Dropdown(choices=list(product_db.keys()), label="Scan Tag")
        scan_btn = gr.Button("Scan")

    status = gr.Textbox(label="Status")
    item_list = gr.Group()
    summary = gr.Textbox(label="Bill Summary", interactive=False)
    discount_slider = gr.Slider(0, 50, step=5, label="Discount (%)")
    reset_btn = gr.Button("Reset Tray")

    scan_btn.click(fn=scan_epc, inputs=epc_input, outputs=[status, item_list, summary])
    reset_btn.click(fn=reset_tray, outputs=[status, item_list, summary])
    discount_slider.change(fn=set_discount, inputs=discount_slider, outputs=summary)

    demo.load(fn=refresh_ui, outputs=[item_list, summary])

if __name__ == "__main__":
    demo.launch()
