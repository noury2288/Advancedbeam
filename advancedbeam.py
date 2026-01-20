import streamlit as st
import pandas as pd
from indeterminatebeam import Beam, Support, PointLoadV, PointTorque, UDLV

"""A **minimal, single‑form** Streamlit wrapper for the *indeterminatebeam* package.

*Everything lives in one form*, so edits to the tables are committed only
when the user clicks **Analyse Beam** – no more half‑saved cells or multiple
reruns while typing.
"""

# ---------------------------------------------------------------------
# ─── CONSTANTS ────────────────────────────────────────────────────────
# ---------------------------------------------------------------------
DEFAULT_L = 6.0
DEFAULT_SUPPORTS = [  # two fixed ends as a starting point
    {"x": 0.0, "type": "Fixed"},
    {"x": DEFAULT_L, "type": "Fixed"},
]
DEFAULT_LOADS = [  # single downward point load at mid‑span
    {"kind": "Point Load", "magnitude": -10_000, "x": DEFAULT_L / 2, "x_end": None},
]

SUPPORT_MAP = {  # maps UI dropdown label → (Ux, Uy, Rz) tuple
    "Fixed": (1, 1, 1),
    "Pin": (1, 1, 0),
    "Roller": (0, 1, 0),
}

# ---------------------------------------------------------------------
# ─── PAGE CONFIG ──────────────────────────────────────────────────────
# ---------------------------------------------------------------------
st.set_page_config(page_title="Indeterminate Beam Calculator", layout="wide")

# ---------------------------------------------------------------------
# ─── SIDEBAR – SINGLE FORM ────────────────────────────────────────────
# ---------------------------------------------------------------------
with st.sidebar.form("beam_form"):
    st.header("Beam Definition")

    # 🔹 Geometry / material
    length = st.number_input("Span length L (m)", min_value=0.1, value=DEFAULT_L, step=0.1)
    E = st.number_input("Young's Modulus E (Pa)", value=200e9, step=1e9, format="%e")
    I = st.number_input("Second moment of area I (m⁴)", value=9.05e-6, step=1e-6, format="%e")

    st.markdown("---")

    # 🔹 Supports table
    st.subheader("Supports")
    supports_df = st.data_editor(
        pd.DataFrame(st.session_state.get("supports_df", DEFAULT_SUPPORTS)),
        num_rows="dynamic",
        column_config={
            "x": st.column_config.NumberColumn("x (m)", step=0.1),
            "type": st.column_config.SelectboxColumn("Type", options=list(SUPPORT_MAP)),
        },
        key="supports_editor",
    )

    st.subheader("Loads")
    loads_df = st.data_editor(
        pd.DataFrame(st.session_state.get("loads_df", DEFAULT_LOADS)),
        num_rows="dynamic",
        column_config={
            "kind": st.column_config.SelectboxColumn("Type", options=["Point Load", "UDL", "Torque"]),
            "magnitude": st.column_config.NumberColumn("Magnitude (N / N·m)", step=100),
            "x": st.column_config.NumberColumn("x start (m)", step=0.1),
            "x_end": st.column_config.NumberColumn("x end (m)", step=0.1),
        },
        key="loads_editor",
    )

    submitted = st.form_submit_button("Analyse Beam")

# ---------------------------------------------------------------------
# ─── MAIN AREA – RESULTS ──────────────────────────────────────────────
# ---------------------------------------------------------------------
st.title("Indeterminate Beam Results")

if submitted:
    # Cache the last good tables so they come back on the next rerun
    st.session_state["supports_df"] = supports_df
    st.session_state["loads_df"] = loads_df

    # 1️⃣ Build beam
    beam = Beam(length, E=E, I=I)

    # 2️⃣ Supports
    for _, row in supports_df.dropna().iterrows():
        beam.add_supports(Support(float(row["x"]), SUPPORT_MAP[row["type"]]))

    # 3️⃣ Loads
    for _, row in loads_df.dropna(subset=["kind", "magnitude", "x"]).iterrows():
        kind = row["kind"]
        mag = float(row["magnitude"])
        x0 = float(row["x"])
        if kind == "Point Load":
            beam.add_loads(PointLoadV(mag, x0))
        elif kind == "UDL":
            xe = float(row["x_end"]) if pd.notna(row["x_end"]) else x0
            beam.add_loads(UDLV(mag, (x0, xe)))
        elif kind == "Torque":
            beam.add_loads(PointTorque(mag, x0))

    # 4️⃣ Analyse & Plot
    beam.analyse()

    st.subheader("External Forces & Reactions")
    st.plotly_chart(beam.plot_beam_external(), use_container_width=True)

    st.subheader("Shear, Moment & Deflection")
    st.plotly_chart(beam.plot_beam_internal(), use_container_width=True)

    st.subheader("Reaction summary (N, N·m)")
    st.write({f"{round(s._position, 3)} m": beam.get_reaction(i) for i, s in enumerate(beam._supports)})

else:
    st.info("Fill in the sidebar, then hit **Analyse Beam** to see the diagrams.")
