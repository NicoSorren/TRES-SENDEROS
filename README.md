# Tres Senderos Invoice Records

The app writes generated remitos to a worksheet named **Remitos** in the
main Google spreadsheet. The sheet contains the following columns in order:

1. **Number** – Remito or invoice number.
2. **Date** – Date of issuance (`YYYY-MM-DD`).
3. **Customer name** – Name of the client.
4. **Subtotal** – Sum of line item subtotals.
5. **Discount** – Amount discounted from the subtotal.
6. **Total final** – `Subtotal - Discount`.

Each time a remito is generated, these values are appended as a new row. You
can analyse revenue directly in Google Sheets or with pandas.

## Google Sheets totals

To compute the total revenue for a month use a formula such as:

```none
=SUMIFS('Remitos'!F:F, 'Remitos'!B:B, ">=2024-04-01", 'Remitos'!B:B, "<=2024-04-30")
```

Replace the dates with the desired range. Column **F** corresponds to
`Total final`.

## Using pandas

```python
import pandas as pd
from sheet_connector import SheetConnector

connector = SheetConnector(SPREADSHEET_URL)
df = connector.client.open_by_url(SPREADSHEET_URL).worksheet("Remitos").get_all_records()
df = pd.DataFrame(df)
monthly_total = (
    df.assign(Date=pd.to_datetime(df["Date"]))
      .query("Date.dt.month == 4 and Date.dt.year == 2024")
      ["Total final"].sum()
)
```

This will give the total for April 2024.

## Bulk invoice generation

To create several invoices at once and keep an Excel summary you can loop over your invoice data and call the `InvoiceManager` for each entry.

```python
import pandas as pd
from invoice_manager import InvoiceManager

manager = InvoiceManager(api_key="YOUR_API_KEY")

april_invoices = [
    {
        "number": "R-101",
        "date": "2024-04-05",
        "to": "Customer A",
        "items[0][name]": "Producto A",
        "items[0][quantity]": 1,
        "items[0][unit_cost]": 200,
    },
    # ... more invoices ...
]

records = []
for data in april_invoices:
    pdf = manager.generate_invoice_pdf(data)
    with open(f"{data['number']}.pdf", "wb") as f:
        f.write(pdf.getbuffer())

    subtotal = data["items[0][quantity]"] * data["items[0][unit_cost]"]
    discount = data.get("discount", 0)
    records.append({
        "Number": data["number"],
        "Date": data["date"],
        "Customer name": data["to"],
        "Subtotal": subtotal,
        "Discount": discount,
        "Total final": subtotal - discount,
    })

pd.DataFrame(records).to_excel("invoices_april_2024.xlsx", index=False)
```

Running this example will produce one PDF per invoice and an
`invoices_april_2024.xlsx` file summarising them.
