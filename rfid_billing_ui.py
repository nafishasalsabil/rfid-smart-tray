import gradio as gr
import pandas as pd
import threading
import serial
import time

# -----------------------------
# Config
# -----------------------------
SERIAL_PORT = "/dev/ttyUSB0"  # For Windows use "COM3" or similar
BAUD_RATE = 9600

product_db = {
    "EPC001": {"name": "Men's Tee", "price": 1290},
    "EPC002": {"name": "Jeans", "price": 1890},
    "EPC003": {"name": "Kurti", "price": 1150},
    "EPC004": {"name": "Formal Shirt", "price": 1490},
}
scanned_items = {}
discount = 0
refresh_flag = False

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

def get_ui_elements():
    elements = []
    for epc, item in scanned_items.items():
        with gr.Row() as row:
            elements.extend([
                gr.Textbox(value=epc, interactive=False, show_label=False),
                gr.Textbox(value=item["name"], interactive=False, show_label=False),
                gr.Textbox(value=item["price"], interactive=False, show_label=False),
                gr.Textbox(value=item["qty"], interactive=False, show_label=False),
                gr.Button("+", elem_id=f"inc-{epc}", scale=0.5),
                gr.Button("-", elem_id=f"dec-{epc}", scale=0.5),
                gr.Button("x", elem_id=f"rem-{epc}", scale=0.5),
            ])
    return elements

# -----------------------------
# Action Functions
# -----------------------------
def scan_epc(epc):
    global refresh_flag
    epc = epc.strip().upper()
    if not epc or epc not in product_db:
        return "⚠️ Invalid EPC tag"
    if epc in scanned_items:
        return f"⚠️ Already in tray: {product_db[epc]['name']}"
    scanned_items[epc] = {"name": product_db[epc]["name"], "price": product_db[epc]["price"], "qty": 1}
    refresh_flag = True
    return f"✅ Scanned: {product_db[epc]['name']}"

def reset_tray():
    scanned_items.clear()
    return "🧹 Tray cleared!"

def set_discount(p):
    global discount
    discount = p
    return update_summary()

def action_handler(action_epc):
    action, epc = action_epc.split(":")
    if epc not in scanned_items:
        return
    if action == "inc":
        scanned_items[epc]["qty"] += 1
    elif action == "dec":
        if scanned_items[epc]["qty"] > 1:
            scanned_items[epc]["qty"] -= 1
        else:
            del scanned_items[epc]
    elif action == "rem":
        del scanned_items[epc]

# -----------------------------
# Serial Reader
# -----------------------------
def serial_reader():
    global refresh_flag
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
        print(f"✅ Connected to {SERIAL_PORT}")
        while True:
            if ser.in_waiting:
                epc = ser.readline().decode("utf-8").strip()
                print(f"🔍 Tag detected: {epc}")
                scan_epc(epc)
                refresh_flag = True
            time.sleep(0.5)
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
    summary = gr.Textbox(label="Bill Summary")
    discount_slider = gr.Slider(0, 50, step=5, label="Discount (%)")
    reset_btn = gr.Button("Reset Tray")

    scan_btn.click(fn=scan_epc, inputs=epc_input, outputs=status)
    reset_btn.click(fn=reset_tray, outputs=status)
    discount_slider.change(fn=set_discount, inputs=discount_slider, outputs=summary)

    def refresh_ui():
        global refresh_flag
        if refresh_flag:
            refresh_flag = False
            return get_ui_elements(), update_summary()
        return gr.update(), gr.update()

    gr.Timer(1.0, fn=refresh_ui, outputs=[item_list, summary], show_progress=False)


if __name__ == "__main__":
    demo.launch()
