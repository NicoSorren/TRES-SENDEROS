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
