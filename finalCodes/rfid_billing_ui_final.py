import gradio as gr
import json, os, pandas as pd
from datetime import datetime
import threading, serial, time

# --- Persistent Product DB ---
PRODUCT_DB_FILE = "../product_db.json"
if os.path.exists(PRODUCT_DB_FILE):
    with open(PRODUCT_DB_FILE, "r") as f:
        product_db = json.load(f)
else:
    product_db = {
        "EPC001": {"name": "Men's Tee",     "price": 1290},
        "EPC002": {"name": "Jeans",          "price": 1890},
        "EPC003": {"name": "Kurti",          "price": 1150},
        "EPC004": {"name": "Formal Shirt",   "price": 1490},
    }
    with open(PRODUCT_DB_FILE, "w") as f:
        json.dump(product_db, f, indent=2)

scanned_items = {}

SERIAL_PORT = "/dev/ttyUSB0"   # or "COM3" on Windows
BAUD_RATE   = 115200


def save_product_db():
    with open(PRODUCT_DB_FILE, "w") as f:
        json.dump(product_db, f, indent=2)

# --- Billing Logic ---
def get_bill_df():
    return pd.DataFrame(
        [
            {
                "EPC": epc,
                "Name": item["name"],
                "Price": item["price"],
                "Qty": item["qty"],
                "Total": item["price"] * item["qty"],
            }
            for epc, item in scanned_items.items()
        ],
        columns=["EPC", "Name", "Price", "Qty", "Total"])


def summary_text():
    df = get_bill_df()
    subtotal = df["Total"].sum() if not df.empty else 0
    return f"Subtotal: {subtotal:.0f} BDT\nDiscount: 0 BDT\nTotal: {subtotal:.0f} BDT"


def scan_epc(epc):
    epc = epc.strip().upper()
    if epc not in product_db:
        # tray-empty? keep buttons hidden
        hidden = True
        return (
            f"❌ EPC not found: {epc}",
            get_bill_df(), summary_text(),
            gr.update(choices=list(scanned_items), value=None),
            gr.update(value=""),
            *([gr.update(visible=not hidden)]*7)
        )
    # add/increment
    scanned_items.setdefault(epc, {**product_db[epc], "qty":0})["qty"] += 1

    hidden = False
    return (
        f"✅ Scanned: {product_db[epc]['name']}",
        get_bill_df(), summary_text(),
        gr.update(choices=list(scanned_items), value=None),
        gr.update(value=""),
        *([gr.update(visible=not hidden)]*7)
    )

def modify_qty(epc, action):
    if epc in scanned_items:
        if action=="inc":
            scanned_items[epc]["qty"] += 1
        elif action=="dec":
            scanned_items[epc]["qty"] = max(1, scanned_items[epc]["qty"]-1)
        elif action=="rem":
            del scanned_items[epc]
    hidden = (len(scanned_items)==0)
    new_val = epc if epc in scanned_items else None
    return (
        get_bill_df(), summary_text(),
        gr.update(choices=list(scanned_items), value=new_val),
        *([gr.update(visible=not hidden)]*7)
    )


def reset_tray():
    scanned_items.clear()
    hidden = True
    return (
        "🧹 Tray cleared",
        get_bill_df(), summary_text(),
        gr.update(choices=[], value=None),
        *([gr.update(visible=not hidden)]*7)
    )

def export_csv():
    df = get_bill_df()
    fname = f"bill_{datetime.now():%Y%m%d_%H%M%S}.csv"
    df.to_csv(fname, index=False)
    return fname


def export_pdf():
    df = get_bill_df()
    try:
        from fpdf import FPDF
    except ImportError:
        return "❌ Install fpdf"

    pdf = FPDF()
    pdf.add_page()

    # CORRECTED: pass style as empty string, size as integer
    pdf.set_font("Arial", "", 12)

    pdf.cell(200, 10, text="Smart Tray Bill", ln=True, align='C')
    pdf.ln(5)

    for _, row in df.iterrows():
        line = f"{row['Name']} x{row['Qty']} = {row['Total']} BDT"
        pdf.cell(200, 10, text=line, ln=True)

    pdf.ln(5)
    pdf.multi_cell(0, 10, text=summary_text())

    filename = f"bill_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    pdf.output(filename)
    return filename


def complete_bill():
    msg = summary_text()+"\n✅ Bill completed."
    scanned_items.clear()
    hidden = True
    return (
        msg,
        get_bill_df(), summary_text(),
        gr.update(choices=[], value=None),
        *([gr.update(visible=not hidden)]*7)
    )

# --- Admin Logic ---
def save_product(epc, name, price):
    product_db[epc] = {"name": name, "price": float(price)}
    save_product_db()
    return f"✅ Saved {name} ({epc})"

def delete_product(epc):
    if epc in product_db:
        del product_db[epc]
        save_product_db()
        return f"🗑 Deleted {epc}"
    return f"❌ EPC not found"


def serial_reader():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"✅ Listening on {SERIAL_PORT} @ {BAUD_RATE} baud")
        while True:
            line = ser.readline().decode("utf-8").strip()
            if line:
                print(f"🔍 Tag read: {line}")
                # feed into your billing logic exactly as if you’d clicked “Scan”
                scan_epc(line)
            time.sleep(0.05)
    except Exception as e:
        print(f"⚠️ Serial error: {e}")

# --- UI ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    with gr.Tab("🧾 Billing"):
        with gr.Row():
            epc_in = gr.Textbox(label="Simulate EPC Scan")
            scan_btn = gr.Button("Scan")
            status = gr.Textbox(label="Status", interactive=False)

        bill_df = gr.Dataframe(get_bill_df(), label="Tray Items", interactive=False)
        summary = gr.Textbox(summary_text(), label="Summary", lines=3, interactive=False)

        with gr.Row():
            sel_epc = gr.Dropdown(choices=[], label="Select EPC", allow_custom_value=True)
            btn_inc = gr.Button("+1 Qty", visible=False)
            btn_dec = gr.Button("–1 Qty", visible=False)
            btn_rem = gr.Button("Remove", visible=False)

        with gr.Row():
            btn_reset = gr.Button("Reset Tray", visible=False)
            btn_complete = gr.Button("Complete Bill", visible=False)
            btn_csv = gr.Button("Export CSV", visible=False)
            btn_pdf = gr.Button("Export PDF", visible=False)

        scan_btn.click(
            scan_epc,
            inputs=[epc_in],
            outputs=[
                status, bill_df, summary,
                sel_epc, epc_in,
                btn_inc, btn_dec, btn_rem,
                btn_reset, btn_complete,
                btn_csv, btn_pdf
            ]
        )
        btn_inc.click(
            lambda e: modify_qty(e, "inc"),
            inputs=[sel_epc],
            outputs=[
                bill_df, summary, sel_epc,
                btn_inc, btn_dec, btn_rem,
                btn_reset, btn_complete,
                btn_csv, btn_pdf
            ]
        )
        btn_dec.click(
            lambda e: modify_qty(e, "dec"),
            inputs=[sel_epc],
            outputs=[
                bill_df, summary, sel_epc,
                btn_inc, btn_dec, btn_rem,
                btn_reset, btn_complete,
                btn_csv, btn_pdf
            ]
        )
        btn_rem.click(
            lambda e: modify_qty(e, "rem"),
            inputs=[sel_epc],
            outputs=[
                bill_df, summary, sel_epc,
                btn_inc, btn_dec, btn_rem,
                btn_reset, btn_complete,
                btn_csv, btn_pdf
            ]
        )
        btn_reset.click(
            reset_tray,
            outputs=[
                status, bill_df, summary,
                sel_epc,
                btn_inc, btn_dec, btn_rem,
                btn_reset, btn_complete,
                btn_csv, btn_pdf
            ]
        )
        btn_complete.click(
            complete_bill,
            outputs=[
                status, bill_df, summary,
                sel_epc,
                btn_inc, btn_dec, btn_rem,
                btn_reset, btn_complete,
                btn_csv, btn_pdf
            ]
        )
        btn_csv.click(lambda: export_csv(), outputs=gr.File())
        btn_pdf.click(lambda: export_pdf(), outputs=gr.File())

    with gr.Tab("🛠️ Admin"):
        epc_admin  = gr.Textbox(label="EPC")
        name_admin = gr.Textbox(label="Product Name")
        price_admin= gr.Textbox(label="Price")
        admin_msg  = gr.Textbox(label="Admin Status", interactive=False)
        btn_save   = gr.Button("Save/Update")
        btn_del    = gr.Button("Delete")

        btn_save.click(save_product,
                       inputs=[epc_admin, name_admin, price_admin],
                       outputs=[admin_msg])
        btn_del.click(delete_product,
                      inputs=[epc_admin],
                      outputs=[admin_msg])

threading.Thread(target=serial_reader, daemon=True).start()
demo.launch()
