
import gradio as gr
import pandas as pd
import threading
import serial
import time

# -----------------------------
# Config
# -----------------------------
SERIAL_PORT = "/dev/ttyUSB0"  # Update for your OS
BAUD_RATE = 9600

product_db = {
    "EPC001": {"name": "Men's Tee", "price": 1290},
    "EPC002": {"name": "Jeans", "price": 1890},
    "EPC003": {"name": "Kurti", "price": 1150},
    "EPC004": {"name": "Formal Shirt", "price": 1490},
}

scanned_items = {}
discount = 0

# -----------------------------
# Core Functions
# -----------------------------

def get_bill_df():
    rows = []
    for epc, item in scanned_items.items():
        total = item["price"] * item["qty"]
        rows.append([epc, item["name"], item["price"], item["qty"], total])
    return pd.DataFrame(rows, columns=["EPC", "Name", "Price", "Qty", "Total"])

def render_table():
    df = get_bill_df()
    return df.to_markdown(index=False) if not df.empty else "No items in tray."

def update_summary():
    df = get_bill_df()
    if df.empty:
        return "Subtotal: 0 BDT\nDiscount: 0 BDT\nTotal: 0 BDT"
    subtotal = df["Total"].sum()
    discount_amt = subtotal * (discount / 100)
    total = subtotal - discount_amt
    return f"Subtotal: {subtotal} BDT\nDiscount: {discount_amt:.0f} BDT\nTotal: {total:.0f} BDT"

def scan_epc(epc):
    epc = epc.strip().upper()
    if not epc or epc not in product_db:
        return "⚠️ Invalid EPC tag", render_table(), update_summary()
    if epc in scanned_items:
        return f"⚠️ Already scanned: {product_db[epc]['name']}", render_table(), update_summary()
    scanned_items[epc] = {
        "name": product_db[epc]["name"],
        "price": product_db[epc]["price"],
        "qty": 1
    }
    return f"✅ Scanned: {product_db[epc]['name']}", render_table(), update_summary()

def adjust_qty(epc, action):
    if epc not in scanned_items:
        return render_table(), update_summary()
    if action == "inc":
        scanned_items[epc]["qty"] += 1
    elif action == "dec":
        if scanned_items[epc]["qty"] > 1:
            scanned_items[epc]["qty"] -= 1
        else:
            del scanned_items[epc]
    elif action == "rem":
        del scanned_items[epc]
    return render_table(), update_summary()

def reset_tray():
    scanned_items.clear()
    return "🧹 Tray cleared!", render_table(), update_summary()

def set_discount(p):
    global discount
    discount = p
    return update_summary()

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

threading.Thread(target=serial_reader, daemon=True).start()

# -----------------------------
# UI
# -----------------------------
with gr.Blocks() as demo:
    gr.Markdown("# 🛒 RFID Smart Tray Billing (Gradio 4.x Stable)")

    with gr.Row():
        epc_dropdown = gr.Dropdown(choices=list(product_db.keys()), label="EPC Tag")
        scan_btn = gr.Button("Scan")

    msg = gr.Textbox(label="Status")
    table = gr.Textbox(label="Items", lines=10)
    summary = gr.Textbox(label="Summary", lines=3)

    with gr.Row():
        epc_edit = gr.Dropdown(choices=list(product_db.keys()), label="Select EPC to Adjust")
        inc_btn = gr.Button("➕")
        dec_btn = gr.Button("➖")
        rem_btn = gr.Button("❌")

    discount_slider = gr.Slider(0, 50, step=5, label="Discount (%)")
    reset_btn = gr.Button("Reset Tray")

    scan_btn.click(fn=scan_epc, inputs=epc_dropdown, outputs=[msg, table, summary])
    reset_btn.click(fn=reset_tray, outputs=[msg, table, summary])
    discount_slider.change(fn=set_discount, inputs=discount_slider, outputs=summary)

    inc_btn.click(fn=lambda epc: adjust_qty(epc, "inc"), inputs=epc_edit, outputs=[table, summary])
    dec_btn.click(fn=lambda epc: adjust_qty(epc, "dec"), inputs=epc_edit, outputs=[table, summary])
    rem_btn.click(fn=lambda epc: adjust_qty(epc, "rem"), inputs=epc_edit, outputs=[table, summary])

if __name__ == "__main__":
    demo.launch()
