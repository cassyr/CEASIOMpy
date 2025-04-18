"""
CEASIOMpy: Conceptual Aircraft Design Software

Developed for CFS ENGINEERING, 1015 Lausanne, Switzerland

Streamlit page to change settings of a CEASIOMpy workflow

Python version: >=3.8

| Author : Aidan Jungo
| Creation: 2022-09-16

TODO:

"""

from collections import OrderedDict
from pathlib import Path
from cpacspy.cpacsfunctions import create_branch

from tixi3 import tixi3wrapper
from cpacspy.cpacsfunctions import open_tixi

import pandas as pd
import streamlit as st
from ceasiompy.utils.moduleinterfaces import get_specs_for_module, get_toolinput_file_path
from cpacspy.cpacsfunctions import (
    add_string_vector,
    add_value,
    get_string_vector,
    get_value_or_default,
)
from cpacspy.cpacspy import CPACS
from streamlitutils import create_sidebar
from ceasiompy.utils.commonxpath import SU2MESH_XPATH

import os

how_to_text = (
    "### How to use Settings?\n"
    "1. With *Edit aeromap* you can create or modify aeromap\n"
    "1. Then, you can go though each tab and modify the settings of each module\n"
    "1. Click the *Save* button\n"
    "1. Go to the *Run Workflow* page\n"
)

create_sidebar(how_to_text)

# Custom CSS
st.markdown(
    """
    <style>
    .css-1awtkze {
        border-radius:3px;
        background-color: #9e9e93;
        padding: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def update_value(xpath, key):
    if key in st.session_state:
        value = st.session_state[key]

        if isinstance(value, list):
            if value:
                add_string_vector(st.session_state.cpacs.tixi, xpath, value)
                return
            else:
                value = ""

        add_value(st.session_state.cpacs.tixi, xpath, value)


def update_all_modified_value():
    for xpath, key in st.session_state.xpath_to_update.items():
        update_value(xpath, key)


def save_cpacs_file():
    update_all_modified_value()
    saved_cpacs_file = Path(st.session_state.workflow.working_dir, "CPACS_selected_from_GUI.xml")
    st.session_state.cpacs.save_cpacs(saved_cpacs_file, overwrite=True)
    st.session_state.workflow.cpacs_in = saved_cpacs_file
    st.session_state.cpacs = CPACS(saved_cpacs_file)


# def upload_and_save_file(file_uploader, save_dir):

#     file = file_uploader("Select a file", type=["cgns", "su2"], key="file_uploader_key")

#     if file is not None:
#         file_name = file.name

#         # Crea la cartella di salvataggio se non esiste
#         os.makedirs(save_dir, exist_ok=True)

#         # Salva il file nella directory specificata
#         file_path = os.path.join(save_dir, file_name)
#         with open(file_path, "wb") as f:
#             f.write(file.getbuffer())

#         # Visualizza il percorso completo del file locale
#         st.success(f"File saved to: {file_path}")

#         return file_path

#     return None


def section_edit_aeromap():
    st.markdown("#### Available aeromaps")

    aeromap_uid_list = st.session_state.cpacs.get_aeromap_uid_list()

    for i, aeromap in enumerate(aeromap_uid_list):
        col1, col2, col3, _ = st.columns([6, 1, 1, 5])

        with col1:
            st.markdown(f"**{aeromap}**")

        with col2:
            if st.button("⬆️", key=f"export{i}", help="Export aeromap") and i != 0:
                csv_file_name = aeromap.replace(" ", "_") + ".csv"
                st.session_state.cpacs.get_aeromap_by_uid(aeromap).export_csv(csv_file_name)
                with open(csv_file_name) as f:
                    st.download_button("Download", f, file_name=csv_file_name)

        with col3:
            if st.button("❌", key=f"del{i}", help="Delete this aeromap"):
                st.session_state.cpacs.delete_aeromap(aeromap)
                st.experimental_rerun()

    st.markdown("#### Add a point")

    selected_aeromap = st.selectbox(
        "in", aeromap_uid_list, help="Choose in which aeromap you want to add the point"
    )

    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])

    with col1:
        alt = st.number_input("Alt", value=1000, min_value=0, step=100)
    with col2:
        mach = st.number_input("Mach", value=0.3, min_value=0.0, step=0.1)
    with col3:
        aos = st.number_input("AoS", value=0.0, min_value=-90.0, max_value=90.0, step=0.1)
    with col4:
        aoa = st.number_input("AoA", value=0.0, min_value=-90.0, max_value=90.0, step=0.1)
    with col5:
        st.session_state.point_exist = False
        st.markdown("")
        st.markdown("")
        if st.button("➕"):
            aeromap = st.session_state.cpacs.get_aeromap_by_uid(selected_aeromap)

            try:
                aeromap.add_row(mach=mach, alt=alt, aos=aos, aoa=aoa)
            except ValueError:
                st.session_state.point_exist = True

            if not st.session_state.point_exist:
                aeromap.save()
                save_cpacs_file()

    if st.session_state.point_exist:
        st.error("This point already exist in this aeromap")

    if selected_aeromap:
        st.dataframe(st.session_state.cpacs.get_aeromap_by_uid(selected_aeromap).df)

    st.markdown("#### Create new aeromap")

    form = st.form("create_new_aeromap_form")

    help_aeromap_uid = "The aeromap will contain 1 point corresponding to the value above, then \
                        you can add more point to it."
    new_aeromap_uid = form.text_input(
        "Aeromap uid",
        help=help_aeromap_uid,
    )
    default_description = "Created with CEASIOMpy Graphical user interface"
    new_aeromap_description = form.text_input(
        "Aeromap description", value=default_description, help="optional"
    )

    if form.form_submit_button("Create new"):
        if new_aeromap_uid not in aeromap_uid_list:
            new_aeromap = st.session_state.cpacs.create_aeromap(new_aeromap_uid)
            new_aeromap.description = new_aeromap_description
            new_aeromap.add_row(mach=mach, alt=alt, aos=aos, aoa=aoa)
            new_aeromap.save()
            st.experimental_rerun()
        else:
            st.error("There is already an aeromap with this name!")

    st.markdown("#### Import aeromap from CSV")

    uploaded_csv = st.file_uploader("Choose a CSV file")
    if uploaded_csv:
        uploaded_aeromap_uid = uploaded_csv.name.split(".csv")[0]

        if st.button("Add this aeromap"):
            if uploaded_aeromap_uid in aeromap_uid_list:
                st.error("There is already an aeromap with this name!")
                return

            new_aeromap = st.session_state.cpacs.create_aeromap(uploaded_aeromap_uid)
            new_aeromap.df = pd.read_csv(uploaded_csv, keep_default_na=False)
            new_aeromap.save()
            st.experimental_rerun()


def mesh_file_upload():
    st.markdown("#### Upload mesh file")

    # Verifica se è stato caricato un file mesh
    uploaded_mesh = st.file_uploader(
        "Select a mesh file",
        key="00_mesh_upload",
        type=["su2", "cgns"],
    )

    if uploaded_mesh:
        # Crea la cartella "mesh" se non esiste
        mesh_dir = os.path.join(st.session_state.workflow.working_dir, "mesh")
        os.makedirs(mesh_dir, exist_ok=True)

        # Crea un nuovo percorso per il file .su2 nella cartella "mesh"
        mesh_new_path = os.path.join(mesh_dir, uploaded_mesh.name)
        print(f"mesh path: {mesh_new_path}")

        try:
            # Scrivi il file nel percorso specificato
            with open(mesh_new_path, "wb") as f:
                f.write(uploaded_mesh.getbuffer())

            # Apri il file CPACS
            cpacs_path = st.session_state.workflow.cpacs_in
            print(f"cpacs_path: {cpacs_path}")
            tixi = open_tixi(cpacs_path)

            # Definisci la variabile mesh_xpath in base alla tua struttura CPACS
            mesh_xpath = "/cpacs/toolspecific/CEASIOMpy/filesPath/su2Mesh"

            # Verifica se il percorso esiste
            if not tixi.checkElement(mesh_xpath):
                # Se il percorso non esiste, crealo
                create_branch(tixi, mesh_xpath)

            if st.button("Add this mesh"):
                # Aggiorna il percorso del file SU2 mesh nel documento CPACS
                tixi.updateTextElement(mesh_xpath, str(mesh_new_path))

                # Salva il file CPACS
                save_cpacs_file()

                return mesh_new_path

        except Exception as e:
            st.error(f"An error occurred: {e}")
            return None

    return None


def add_module_tab():
    if "cpacs" not in st.session_state:
        st.warning("No CPACS file has been selected!")
        return

    with st.expander("Edit Aeromaps"):
        section_edit_aeromap()

    # with st.expander("Add mesh"):
    #     mesh_file_upload()

    if "tabs" not in st.session_state:
        st.session_state["tabs"] = []

    if st.session_state.workflow_modules:
        st.session_state.tabs = st.tabs(st.session_state.workflow_modules)

    st.session_state.xpath_to_update = {}

    for m, (tab, module) in enumerate(
        zip(st.session_state.tabs, st.session_state.workflow_modules)
    ):
        with tab:
            st.text("")
            specs = get_specs_for_module(module)
            inputs = specs.cpacs_inout.get_gui_dict()

            if not inputs:
                st.warning("No settings to modify this module")
                continue

            groups = list(OrderedDict.fromkeys([v[6] for _, v in inputs.items()]))

            groups_container = OrderedDict()
            for group in groups:
                groups_container[group] = st.container()

                with groups_container[group]:
                    st.markdown(f"**{group}**")

            for name, default_value, var_type, unit, xpath, description, group in inputs.values():
                with groups_container[group]:
                    if not group:
                        group = "none"

                    key = f"{m}_{module}_{name.replace(' ', '')}_{group.replace(' ', '')}"

                    if unit not in ["", "1", None]:
                        name = f"{name} {unit}"

                    if name == "__AEROMAP_SELECTION":
                        aeromap_uid_list = st.session_state.cpacs.get_aeromap_uid_list()

                        if not len(aeromap_uid_list):
                            st.error("You must create an aeromap in order to use this module!")
                            continue

                        value = get_value_or_default(
                            st.session_state.cpacs.tixi, xpath, aeromap_uid_list[0]
                        )
                        if value in aeromap_uid_list:
                            idx = aeromap_uid_list.index(value)
                        else:
                            idx = 0
                        st.radio(
                            "Select an aeromap",
                            key=key,
                            options=aeromap_uid_list,
                            index=idx,
                            help=description,
                        )

                    elif name == "__AEROMAP_CHECKBOX":
                        aeromap_uid_list = st.session_state.cpacs.get_aeromap_uid_list()

                        if not len(aeromap_uid_list):
                            st.error("You must create an aeromap in order to use this module!")
                            continue

                        with st.columns([1, 2])[0]:
                            try:
                                default_otp = get_string_vector(st.session_state.cpacs.tixi, xpath)
                            except ValueError:
                                default_otp = None

                            st.multiselect(
                                "Select one or several aeromaps",
                                key=key,
                                options=aeromap_uid_list,
                                default=default_otp,
                                help=description,
                            )

                    elif name == "pathtype":
                        # Chiama la funzione mesh_file_upload() e ottieni il percorso del file mesh
                        mesh_path = mesh_file_upload()

                        with st.columns([1, 2])[0]:
                            st.text_input(
                                "Mesh Path",
                                value=mesh_path,
                                key=key,
                                help="Path to the mesh file",
                            )

                    elif var_type == int:
                        with st.columns([1, 2])[0]:
                            st.number_input(
                                name,
                                value=int(
                                    get_value_or_default(
                                        st.session_state.cpacs.tixi, xpath, default_value
                                    )
                                ),
                                key=key,
                                help=description,
                            )

                    elif var_type == float:
                        with st.columns([1, 2])[0]:
                            st.number_input(
                                name,
                                value=get_value_or_default(
                                    st.session_state.cpacs.tixi, xpath, default_value
                                ),
                                format="%g",
                                key=key,
                                help=description,
                            )

                    elif var_type == list:
                        value = get_value_or_default(
                            st.session_state.cpacs.tixi, xpath, default_value[0]
                        )
                        idx = default_value.index(value)
                        st.radio(
                            name,
                            options=default_value,
                            index=idx,
                            key=key,
                            help=description,
                        )

                    elif var_type == bool:
                        st.checkbox(
                            name,
                            value=get_value_or_default(
                                st.session_state.cpacs.tixi, xpath, default_value
                            ),
                            key=key,
                            help=description,
                        )

                    # elif var_type == "pathtype":

                    #     save_dir = "tempDir"
                    #     mesh_path = upload_and_save_file(st.file_uploader, save_dir)
                    #     print(f"mesh_path={mesh_path}")
                    #     st.text_input(get_value_or_default(
                    #       st.session_state.cpacs.tixi, xpath, mesh_path))
                    #     update_value(xpath, key)

                    else:
                        with st.columns([1, 2])[0]:
                            st.text_input(
                                name,
                                value=get_value_or_default(
                                    st.session_state.cpacs.tixi, xpath, default_value
                                ),
                                key=key,
                                help=description,
                            )

                    st.session_state.xpath_to_update[xpath] = key


def section_settings():
    if "workflow_modules" not in st.session_state:
        st.warning("No module selected!")
        return

    add_module_tab()

    if not len(st.session_state.workflow_modules):
        st.warning("You must first build a workflow in the corresponding tab.")

    if "cpacs" in st.session_state:
        with st.columns([3, 2, 3])[1]:
            if st.button("Save 💾", key="save_button", help="Save CPACS"):
                save_cpacs_file()


st.title("Settings")

section_settings()
