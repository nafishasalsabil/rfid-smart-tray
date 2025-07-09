import gradio as gr
import pandas as pd

# Sample product database
product_db = {
    "EPC001": {"name": "Men's Tee", "price": 1290},
    "EPC002": {"name": "Jeans", "price": 1890},
    "EPC003": {"name": "Kurti", "price": 1150},
    "EPC004": {"name": "Formal Shirt", "price": 1490},
}


def get_bill_df(scanned_items):
    rows = []
    for epc, item in scanned_items.items():
        total = item["price"] * item["qty"]
        rows.append([epc, item["name"], item["price"], item["qty"], total])
    return pd.DataFrame(rows, columns=["EPC", "Name", "Price", "Qty", "Total"])


def update_summary(scanned_items, discount):
    df = get_bill_df(scanned_items)
    if df.empty:
        return "Subtotal: 0 BDT\nDiscount: 0 BDT\nTotal: 0 BDT"
    subtotal = df["Total"].sum()
    discount_amt = subtotal * (discount / 100)
    total = subtotal - discount_amt
    return f"Subtotal: {subtotal:.0f} BDT\nDiscount: {discount_amt:.0f} BDT\nTotal: {total:.0f} BDT"


def scan_epc(epc, scanned_items, discount):
    if not epc or epc not in product_db:
        return "⚠️ Invalid EPC", scanned_items, pd.DataFrame(), update_summary(scanned_items, discount)
    if epc in scanned_items:
        return f"⚠️ Already scanned: {epc}", scanned_items, get_bill_df(scanned_items), update_summary(scanned_items,
                                                                                                       discount)
    scanned_items[epc] = {
        "name": product_db[epc]["name"],
        "price": product_db[epc]["price"],
        "qty": 1
    }
    return f"✅ Scanned: {product_db[epc]['name']}", scanned_items, get_bill_df(scanned_items), update_summary(
        scanned_items, discount)


def change_qty(epc, action, scanned_items, discount):
    if epc in scanned_items:
        if action == "inc":
            scanned_items[epc]["qty"] += 1
        elif action == "dec" and scanned_items[epc]["qty"] > 1:
            scanned_items[epc]["qty"] -= 1
        elif action == "rem":
            scanned_items.pop(epc)
    return scanned_items, get_bill_df(scanned_items), update_summary(scanned_items, discount)


def set_discount(value, scanned_items):
    return update_summary(scanned_items, value)


def reset_tray():
    return {}, "🧹 Tray cleared", pd.DataFrame(), "Subtotal: 0 BDT\nDiscount: 0 BDT\nTotal: 0 BDT"


with gr.Blocks() as demo:
    gr.Markdown("## 🛒 RFID Smart Tray with Quantity Control")

    scanned_items = gr.State({})
    discount_value = gr.State(0)

    with gr.Row():
        epc_input = gr.Dropdown(choices=list(product_db.keys()), label="Simulate Tag")
        scan_btn = gr.Button("Scan")

    status = gr.Textbox(label="Status", interactive=False)
    bill_table = gr.Dataframe(headers=["EPC", "Name", "Price", "Qty", "Total"], interactive=False)
    summary = gr.Textbox(label="Summary", interactive=False)

    with gr.Row():
        qty_epc = gr.Dropdown(choices=list(product_db.keys()), label="Select EPC for Qty Action")
        with gr.Column():
            inc_btn = gr.Button("➕ Increase")
            dec_btn = gr.Button("➖ Decrease")
            rem_btn = gr.Button("❌ Remove")

    discount_slider = gr.Slider(0, 50, step=5, label="Discount (%)")
    reset_btn = gr.Button("Reset Tray")

    scan_btn.click(fn=scan_epc, inputs=[epc_input, scanned_items, discount_value],
                   outputs=[status, scanned_items, bill_table, summary])

    inc_btn.click(fn=change_qty, inputs=[qty_epc, gr.State("inc"), scanned_items, discount_value],
                  outputs=[scanned_items, bill_table, summary])
    dec_btn.click(fn=change_qty, inputs=[qty_epc, gr.State("dec"), scanned_items, discount_value],
                  outputs=[scanned_items, bill_table, summary])
    rem_btn.click(fn=change_qty, inputs=[qty_epc, gr.State("rem"), scanned_items, discount_value],
                  outputs=[scanned_items, bill_table, summary])

    discount_slider.change(fn=set_discount, inputs=[discount_slider, scanned_items], outputs=summary)

    reset_btn.click(fn=reset_tray, inputs=[], outputs=[scanned_items, status, bill_table, summary])

demo.launch()
