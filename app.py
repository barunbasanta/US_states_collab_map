
import io
import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ------------------------------------------------------------
# Page config
# ------------------------------------------------------------
st.set_page_config(
    page_title="US Collaboration Map Generator",
    page_icon="🗺️",
    layout="wide",
)


# ------------------------------------------------------------
# State constants
# ------------------------------------------------------------
STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
}
ABBR_STATE = {v: k for k, v in STATE_ABBR.items()}

# Approximate label locations chosen for readability, not geodesic centroids.
STATE_LABEL_POS = {
    "AL": (32.8, -86.8), "AK": (63.5, -152.0), "AZ": (34.2, -111.8),
    "AR": (34.8, -92.4), "CA": (36.2, -119.6), "CO": (39.0, -105.6),
    "CT": (41.6, -72.7), "DE": (39.0, -75.5), "FL": (28.0, -81.8),
    "GA": (32.8, -83.5), "HI": (20.9, -157.5), "ID": (44.2, -114.5),
    "IL": (40.0, -89.2), "IN": (40.0, -86.2), "IA": (42.0, -93.4),
    "KS": (38.5, -98.5), "KY": (37.8, -85.0), "LA": (30.9, -91.9),
    "ME": (45.2, -69.4), "MD": (39.0, -76.7), "MA": (42.2, -71.8),
    "MI": (43.3, -84.6), "MN": (46.0, -94.2), "MS": (32.7, -89.7),
    "MO": (38.5, -92.3), "MT": (46.8, -110.8), "NE": (41.6, -99.8),
    "NV": (39.2, -116.7), "NH": (43.8, -71.6), "NJ": (40.1, -74.5),
    "NM": (34.4, -106.1), "NY": (43.0, -75.6), "NC": (35.2, -79.5),
    "ND": (47.4, -100.4), "OH": (40.3, -82.8), "OK": (35.6, -97.4),
    "OR": (43.8, -120.6), "PA": (40.8, -77.9), "RI": (41.7, -71.5),
    "SC": (33.8, -80.9), "SD": (44.3, -100.2), "TN": (35.8, -86.1),
    "TX": (31.1, -99.3), "UT": (39.2, -111.8), "VT": (44.1, -72.7),
    "VA": (37.5, -78.4), "WA": (47.4, -120.5), "WV": (38.6, -80.6),
    "WI": (44.3, -89.7), "WY": (43.0, -107.6),
}

TINY_STATES = {"CT", "DE", "RI", "NJ", "MD", "VT", "NH", "MA"}
DEFAULT_FIXES = {
    "Texa": "Texas",
    "Massachussetts": "Massachusetts",
    "Massachusettes": "Massachusetts",
    "Newyork": "New York",
    "NorthCarolina": "North Carolina",
    "SouthCarolina": "South Carolina",
}


# ------------------------------------------------------------
# Data parsing
# ------------------------------------------------------------
def normalize_state_name(raw: str) -> str | None:
    if raw is None:
        return None

    s = str(raw).strip()
    if not s or s.lower() in {"nan", "none"}:
        return None

    s = re.sub(r"\s+", " ", s)
    s = DEFAULT_FIXES.get(s, s)

    # Already an abbreviation
    up = s.upper()
    if up in ABBR_STATE:
        return ABBR_STATE[up]

    # Exact title-case matching
    title = s.title()
    if title in STATE_ABBR:
        return title

    # Exact original matching
    if s in STATE_ABBR:
        return s

    return None


def split_states(cell_value) -> list[str]:
    if pd.isna(cell_value):
        return []
    raw = str(cell_value)
    parts = re.split(r"[,;/|]+", raw)
    out = []
    for p in parts:
        st_name = normalize_state_name(p)
        if st_name:
            out.append(st_name)
    # Deduplicate within one ID row so one item does not count the same state twice.
    return sorted(set(out))


def find_state_column(df: pd.DataFrame) -> str:
    candidates = []
    for c in df.columns:
        lc = str(c).strip().lower()
        if lc in {"state", "states", "trial locations", "locations", "collaborating states", "collaborator states"}:
            candidates.append(c)
        elif "state" in lc or "location" in lc:
            candidates.append(c)

    if candidates:
        return candidates[0]

    if len(df.columns) >= 2:
        return df.columns[1]

    return df.columns[0]


def count_sheet(
    excel_file,
    sheet_name: str,
    primary_state: str,
    count_col_name: str,
) -> pd.DataFrame:
    df = pd.read_excel(excel_file, sheet_name=sheet_name)
    if df.empty:
        return pd.DataFrame({"State": list(STATE_ABBR.keys()), count_col_name: 0})

    state_col = find_state_column(df)
    counts = {s: 0 for s in STATE_ABBR.keys()}

    primary_norm = normalize_state_name(primary_state)

    for val in df[state_col]:
        for st_name in split_states(val):
            if primary_norm and st_name == primary_norm:
                continue
            counts[st_name] += 1

    return pd.DataFrame({"State": list(counts.keys()), count_col_name: list(counts.values())})


def build_counts(uploaded_file, primary_state, pub_sheet, grant_sheet, trial_sheet):
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names

    def safe_count(sheet, col_name):
        if sheet and sheet in sheet_names:
            return count_sheet(uploaded_file, sheet, primary_state, col_name)
        return pd.DataFrame({"State": list(STATE_ABBR.keys()), col_name: 0})

    pubs = safe_count(pub_sheet, "P")
    grants = safe_count(grant_sheet, "G")
    trials = safe_count(trial_sheet, "T")

    merged = pubs.merge(grants, on="State", how="outer").merge(trials, on="State", how="outer").fillna(0)
    for col in ["P", "G", "T"]:
        merged[col] = merged[col].astype(int)

    merged["Total"] = merged["P"] + merged["G"] + merged["T"]
    merged["Abbr"] = merged["State"].map(STATE_ABBR)
    return merged.sort_values(["Total", "State"], ascending=[False, True]).reset_index(drop=True)


# ------------------------------------------------------------
# Plotly map
# ------------------------------------------------------------
def color_scale_for_mode(mode: str):
    if mode == "0–2 white":
        return [
            [0.00, "#FFFFFF"],
            [0.02, "#FFFFFF"],
            [0.03, "#FFD07A"],
            [0.45, "#FFD07A"],
            [0.46, "#F89C3D"],
            [0.72, "#F89C3D"],
            [0.73, "#D62828"],
            [1.00, "#D62828"],
        ]
    return [
        [0.00, "#FFFFFF"],
        [0.01, "#FFF4D6"],
        [0.25, "#FFD07A"],
        [0.60, "#F89C3D"],
        [1.00, "#D62828"],
    ]


def category_value(total: int, mode: str) -> int:
    if mode == "0–2 white":
        if total <= 2:
            return 0
        if total <= 10:
            return 1
        if total <= 20:
            return 2
        return 3
    if total == 0:
        return 0
    if total <= 4:
        return 1
    if total <= 10:
        return 2
    if total <= 20:
        return 3
    return 4


def make_map(
    counts_df: pd.DataFrame,
    title: str,
    color_mode: str,
    show_labels: bool,
    label_zero_states: bool,
    hide_tiny_state_labels: bool,
    show_ak_hi: bool,
    width: int,
    height: int,
):
    df = counts_df.copy()

    if not show_ak_hi:
        df = df[~df["Abbr"].isin(["AK", "HI"])].copy()

    df["ColorValue"] = df["Total"].apply(lambda x: category_value(int(x), color_mode))

    if color_mode == "0–2 white":
        zmax = 3
        tickvals = [0, 1, 2, 3]
        ticktext = ["0–2", "3–10", "11–20", "21+"]
    else:
        zmax = 4
        tickvals = [0, 1, 2, 3, 4]
        ticktext = ["0", "1–4", "5–10", "11–20", "21+"]

    fig = go.Figure()

    fig.add_trace(
        go.Choropleth(
            locations=df["Abbr"],
            z=df["ColorValue"],
            locationmode="USA-states",
            colorscale=color_scale_for_mode(color_mode),
            zmin=0,
            zmax=zmax,
            marker_line_color="#A0A0A0",
            marker_line_width=0.95,
            colorbar=dict(
                title=dict(text="Total<br>Collaborations", side="top", font=dict(size=13)),
                tickmode="array",
                tickvals=tickvals,
                ticktext=ticktext,
                len=0.55,
                thickness=18,
                x=0.98,
                y=0.48,
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Publications: %{customdata[1]}<br>"
                "Grants: %{customdata[2]}<br>"
                "Clinical Trials: %{customdata[3]}<br>"
                "Total: %{customdata[4]}<extra></extra>"
            ),
            customdata=df[["State", "P", "G", "T", "Total"]].values,
        )
    )

    if show_labels:
        label_df = df.copy()
        if not label_zero_states:
            label_df = label_df[label_df["Total"] > 0]
        if hide_tiny_state_labels:
            label_df = label_df[~label_df["Abbr"].isin(TINY_STATES)]

        lats, lons, texts = [], [], []
        for _, row in label_df.iterrows():
            pos = STATE_LABEL_POS.get(row["Abbr"])
            if not pos:
                continue
            lat, lon = pos
            lats.append(lat)
            lons.append(lon)
            texts.append(
                f"<b>{row['State']}</b><br>"
                f"<b>{row['Total']}</b><br>"
                f"<span style='color:#0057E7'><b>{row['P']}</b></span>"
                f" / "
                f"<span style='color:#14833B'><b>{row['G']}</b></span>"
                f" / "
                f"<span style='color:#8B4513'><b>{row['T']}</b></span>"
            )

        fig.add_trace(
            go.Scattergeo(
                lon=lons,
                lat=lats,
                text=texts,
                mode="text",
                textfont=dict(size=10, color="black", family="Arial"),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    # Custom compact legend annotation.
    fig.add_annotation(
        x=0.66,
        y=0.13,
        xref="paper",
        yref="paper",

        text=(
            "<b><span style='color:#0057E7'>P = Publications</span></b><br>"
            "<b><span style='color:#14833B'>G = Grants</span></b><br>"
            "<b><span style='color:#8B4513'>T = Clinical Trials</span></b><br>"
            "<b>Total = P + G + T</b>"
        ),

        showarrow=False,
        align="left",

        bgcolor="rgba(255,255,255,0.96)",
        bordercolor="#D0D0D0",
        borderwidth=1.2,
        borderpad=9,

        font=dict(
            size=12,
            color="black"
        )
    )

    if title:
        fig.update_layout(
            title=dict(text=title, x=0.5, xanchor="center", font=dict(size=24, family="Arial Black")),
        )

    scope = "usa" if show_ak_hi else "north america"

    fig.update_geos(
        scope="usa",
        projection_type="albers usa",
        showland=True,
        landcolor="white",
        bgcolor="white",
        showlakes=True,
        lakecolor="white",
        showcountries=False,
        showsubunits=True,
        subunitcolor="#A0A0A0",
    )

    fig.update_layout(
        width=width,
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=60 if title else 10, b=10),
        font=dict(family="Arial"),
    )

    return fig


def export_figure(fig, fmt: str, scale: int = 4):
    # Requires kaleido in requirements.txt
    return fig.to_image(format=fmt, scale=scale)


# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
st.title("US Collaboration Map Generator")
st.caption("Upload an Excel workbook and export a high-quality PNG, PDF, or SVG map.")

with st.sidebar:
    uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx", "xls"])

    if uploaded_file:
        xls = pd.ExcelFile(uploaded_file)
        sheets = xls.sheet_names
        st.success(f"Loaded sheets: {', '.join(sheets)}")

        options = ["None"] + sheets

        def default_sheet_index(preferred_names, fallback_index=0):
            for name in preferred_names:
                if name in options:
                    return options.index(name)
            return min(fallback_index, len(options) - 1)

        pub_sheet = st.selectbox(
            "Publications sheet",
            options=options,
            index=default_sheet_index(["Publications", "Papers"], 1),
        )

        grant_sheet = st.selectbox(
            "Grants sheet",
            options=options,
            index=default_sheet_index(["Grants"], 0),
        )

        trial_sheet = st.selectbox(
            "Clinical Trials sheet",
            options=options,
            index=default_sheet_index(["Clinical Trials", "Trials"], 0),
        )

        pub_sheet = None if pub_sheet == "None" else pub_sheet
        grant_sheet = None if grant_sheet == "None" else grant_sheet
        trial_sheet = None if trial_sheet == "None" else trial_sheet

        primary_state = st.text_input("Primary state to exclude", value="Massachusetts")

        st.divider()
        title = st.text_input("Map title", value="")
        color_mode = st.selectbox("Color scale", ["0–2 white", "0 white"])
        show_labels = st.checkbox("Show internal labels", value=True)
        label_zero_states = st.checkbox("Label zero-count states where space permits", value=True)
        hide_tiny_state_labels = st.checkbox("Hide tiny Northeast labels", value=True)
        show_ak_hi = st.checkbox("Show Alaska and Hawaii", value=False)

        st.divider()
        width = st.number_input("Export width", min_value=900, max_value=5000, value=2200, step=100)
        height = st.number_input("Export height", min_value=600, max_value=3500, value=1350, step=50)
        export_scale = st.slider("Export scale", min_value=1, max_value=6, value=4)

    else:
        pub_sheet = None
        grant_sheet = None
        trial_sheet = None
        primary_state = "Massachusetts"
        title = ""
        color_mode = "0–2 white"
        show_labels = True
        label_zero_states = True
        hide_tiny_state_labels = True
        show_ak_hi = False
        width = 2200
        height = 1350
        export_scale = 4


if uploaded_file:
    counts_df = build_counts(uploaded_file, primary_state, pub_sheet, grant_sheet, trial_sheet)

    fig = make_map(
        counts_df,
        title=title,
        color_mode=color_mode,
        show_labels=show_labels,
        label_zero_states=label_zero_states,
        hide_tiny_state_labels=hide_tiny_state_labels,
        show_ak_hi=show_ak_hi,
        width=int(width),
        height=int(height),
    )

    left, right = st.columns([3, 1])

    with left:
        st.plotly_chart(fig, width='stretch')

    with right:
        st.subheader("Downloads")

        st.download_button(
            "Download counts CSV",
            data=counts_df.to_csv(index=False).encode("utf-8"),
            file_name="collaboration_counts.csv",
            mime="text/csv",
        )

        try:
            png_bytes = export_figure(fig, "png", export_scale)
            st.download_button(
                "Download high-quality PNG",
                data=png_bytes,
                file_name="collaboration_map.png",
                mime="image/png",
            )

            pdf_bytes = export_figure(fig, "pdf", export_scale)
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name="collaboration_map.pdf",
                mime="application/pdf",
            )

            svg_bytes = export_figure(fig, "svg", export_scale)
            st.download_button(
                "Download SVG",
                data=svg_bytes,
                file_name="collaboration_map.svg",
                mime="image/svg+xml",
            )
        except Exception as e:
            st.error(
                "Export failed. Make sure `kaleido` is installed. "
                "Run: pip install -r requirements.txt"
            )
            st.exception(e)

    st.subheader("Counts table")
    st.dataframe(counts_df, width='stretch', hide_index=True)

else:
    st.info("Upload an Excel file to begin.")

    st.markdown(
        """
        ### Expected Excel format

        Use one sheet for each data type. Recommended sheet names:

        - `Publications` or `Papers`
        - `Grants`
        - `Clinical Trials` or `Trials`

        Each sheet should have at least two columns:

        | ID | States |
        |---|---|
        | P001 | California, Texas |
        | P002 | New York |
        | P003 | Florida, Georgia, North Carolina |

        The state column can be named `State`, `States`, `Trial Locations`, or similar.
        Multiple states should be separated by commas.
        """
    )
