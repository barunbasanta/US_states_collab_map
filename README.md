# US Collaboration Map Generator

A Streamlit app that takes an Excel workbook of collaboration IDs and state names, then generates a high-quality US collaboration map.

## Excel input

Recommended sheets:

- `Publications` or `Papers`
- `Grants`
- `Clinical Trials` or `Trials`

Each sheet should have at least two columns:

| ID | States |
|---|---|
| P001 | California, Texas |
| P002 | New York |
| P003 | Florida, Georgia, North Carolina |

The app automatically finds the state/location column. Multiple states can be comma-separated.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Outputs

The app creates downloadable:

- high-quality PNG
- PDF
- SVG
- counts CSV

## Notes

- The primary state defaults to Massachusetts and is excluded from collaboration counts.
- The color-scale option `0–2 white` makes totals from 0 through 2 display as white.
- Alaska and Hawaii can be shown or hidden with a checkbox.
