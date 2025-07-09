import gradio as gr
import json, os, pandas as pd
import threading, time, random
import tempfile
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import serial  # Make sure pyserial is installed
import serial.tools.list_ports



# ── PRODUCT DATABASE ───────────────────────────────────────────────────────────
product_db = {
    "E2000017221101441890ABCD": {"name": "T-Shirt", "price": 750},
    "E2000017221101441890XYZ1": {"name": "Jeans", "price": 1200},
    "E2000017221101441890LMN2": {"name": "Kurti", "price": 950},
    "E2000017221101441890QWER": {"name": "Formal Shirt", "price": 1450},
    "E2000017221101441890TYUI": {"name": "Denim Jacket", "price": 2200},
    "E2000017221101441890ZXCV": {"name": "Joggers", "price": 1050},
    "E2000017221101441890ASDF": {"name": "Saree", "price": 1850},
    "E2000017221101441890GHJK": {"name": "Polo Shirt", "price": 800},
    "E2000017221101441890BNMQ": {"name": "Hoodie", "price": 1650},
    "E2000017221101441890VCXZ": {"name": "Chinos", "price": 1350}
}

scanned_items = {}
TEST_EPCS = list(product_db.keys())

# ── BILLING LOGIC ──────────────────────────────────────────────────────────────
def get_bill_df():
    return pd.DataFrame([
        {"EPC": epc, "Name": item["name"], "Price": item["price"],
         "Qty": item["qty"], "Total": item["price"] * item["qty"]}
        for epc, item in scanned_items.items()
    ], columns=["EPC", "Name", "Price", "Qty", "Total"])

def summary_text():
    df = get_bill_df()
    total = df["Total"].sum() if not df.empty else 0
    return f"Subtotal: {total:.0f} BDT\nDiscount: 0 BDT\nTotal: {total:.0f} BDT"

def scan_epc(epc):
    epc = epc.strip().upper()
    if epc not in product_db:
        return
    if epc in scanned_items:
        scanned_items[epc]["qty"] += 1
    else:
        scanned_items[epc] = {
            "name": product_db[epc]["name"],
            "price": product_db[epc]["price"],
            "qty": 1
        }

def export_csv():
    df = get_bill_df()
    print(df)
    if df.empty:
        return None
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    df.to_csv(temp_file.name, index=False)
    return temp_file.name

def export_pdf():
    df = get_bill_df()
    if df.empty:
        return None

    # Build PDF
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(temp_file.name, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("🧾 Smart Tray Invoice", styles["Title"]))
    elements.append(Spacer(1, 12))

    # Build table
    data = [["EPC", "Name", "Price", "Qty", "Total"]]
    for _, row in df.iterrows():
        data.append([row["EPC"], row["Name"], f"{row['Price']}", f"{row['Qty']}", f"{row['Total']}"])
    total = df["Total"].sum()
    data.append(["", "", "", "Grand Total", f"{total:.0f} BDT"])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)
    return temp_file.name

import serial

def serial_reader():
    try:
        with serial.Serial("COM5", 9600, timeout=1) as ser:  # Replace with actual COM port
            while True:
                line = ser.readline().decode().strip()
                if line:
                    print(f"🔄 Scanned: {line}")
                    scan_epc(line)
    except Exception as e:
        print("Error:", e)


# ── GRADIO UI ──────────────────────────────────────────────────────────────────
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("## 🚀 Auto‐Scan Smart Tray Demo")

    with gr.Row():
        manual_in = gr.Textbox(placeholder="Type EPC…", label="Manual EPC")
        scan_btn = gr.Button("Scan")
        status = gr.Textbox(interactive=False, label="Status")


    bill_tbl = gr.Dataframe(
        value=get_bill_df(),
        label="Tray Items",
        interactive=False
    )
    summary = gr.Textbox(
        value=summary_text(),
        label="Summary",
        lines=3,
        interactive=False
    )
    reset_btn = gr.Button("Reset Tray")
    with gr.Row():
        export_csv_btn = gr.Button("📥 Export CSV")
        export_pdf_btn = gr.Button("📄 Export PDF")


    def handle_csv_export():
        file_path = export_csv()
        return (file_path, gr.update(visible=True)) if file_path else (None, gr.update(visible=False))


    def handle_pdf_export():
        file_path = export_pdf()
        return (file_path, gr.update(visible=True)) if file_path else (None, gr.update(visible=False))


    export_file = gr.File(label="Download", visible=False)

    export_csv_btn.click(fn=handle_csv_export, outputs=[export_file, export_file])
    export_pdf_btn.click(fn=handle_pdf_export, outputs=[export_file, export_file])


    def manual_scan(epc):
        scan_epc(epc)
        return f"✅ Scanned: {epc}", get_bill_df(), summary_text()

    def manual_reset():
        scanned_items.clear()
        return "🧹 Tray cleared", get_bill_df(), summary_text()

    scan_btn.click(manual_scan, inputs=[manual_in], outputs=[status, bill_tbl, summary])
    reset_btn.click(manual_reset, outputs=[status, bill_tbl, summary])

    # ⏱️ Regular UI update every second
    def refresh_ui():
        return get_bill_df(), summary_text()

    demo.load(refresh_ui, None, [bill_tbl, summary], every=1)

    # 🎯 Background auto scan thread
    def background_scanner():
        while True:
            scan_epc(random.choice(TEST_EPCS))
            time.sleep(1)

    def start_thread():
        threading.Thread(target=background_scanner, daemon=True).start()


    # def start_thread():
    #     threading.Thread(target=serial_reader, daemon=True).start()


    demo.load(start_thread)

demo.launch()
