from collections import defaultdict

import pandas as pd
import streamlit as st
import requests
from datetime import date
import altair as alt
from datetime import datetime
from dateutil.relativedelta import relativedelta



API_URL = "http://127.0.0.1:8000"  # Your FastAPI URL

# ----- SESSION STATE INIT -----
if "page" not in st.session_state:
    st.session_state.page = "Home"

# ----- HOME PAGE -----
def home_page():
    st.title("📚 Book Stall Management System")
    col1, col2, col3 = st.columns(3)

    # --- ADMIN ---
    with col1:
        st.markdown("### 🛠️ Admin")
        if st.button("Add New Location"):
            st.session_state.page = "Add New Location"
        if st.button("Add Volunteer"):
            st.session_state.page = "Add Volunteer"
        if st.button("Make Volunteer Lead"):
            st.session_state.page = "Make Volunteer Lead"
        if st.button("Add New Book Title"):
            st.session_state.page = "Add New Book Title"
        if st.button("Add Books To Inventory"):
            st.session_state.page = "Add Books To Inventory"
        if st.button("Assign Books to Lead"):
            st.session_state.page = "Assign Books"

    # --- VOLUNTEER ---
    with col2:
        st.markdown("### 🙋 Volunteer")
        if st.button("Add Stall"):
            st.session_state.page = "Add Stall"
        if st.button("Update Sale"):
            st.session_state.page = "Update Sale"
        if st.button("Return Book"):
            st.session_state.page = "Return Book"

    # --- DASHBOARDS ---
    with col3:
        st.markdown("### 📊 Dashboards")
        if st.button("Inventory Summary"):
            st.session_state.page = "Inventory Summary"
        if st.button("Volunteer Attendance"):
            st.session_state.page = "Volunteer Attendance"
        if st.button("Admin Performance Report"):
            st.session_state.page = "Admin Performance Report"
        if st.button("Lead Performance Report"):
            st.session_state.page = "Lead Performance Report"
        if st.button("Stall Performance"):
            st.session_state.page = "Stall Performance"
        if st.button("Location Performance"):
            st.session_state.page = "Location Performance"

# ----- ADD VOLUNTEER -----
def add_new_location_page():
    st.subheader("Add New Location")

    area = st.text_input("Area")
    location = st.text_input("Location")
    type = st.text_input("Type")

    if st.button("Add Location"):
        if not area or not location or not type:
            st.warning("Area, location and type are required!")
        else:
            data = {"area": area.lower().strip(), "location": location.lower().strip(), "type": type.lower().strip()}
            try:
                response = requests.post(f"{API_URL}/stalls/add-location", json=data)
                if response.status_code == 200:
                    st.success(f"Title '{area} | {location} | {type}' added successfully!")
                else:
                    st.error(response.json())
            except Exception as e:
                st.error(f"Request failed: {e}")

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"

# ----- ADD VOLUNTEER -----
def add_volunteer_page():
    st.subheader("Add a New Volunteer")
    vol_name = st.text_input("Volunteer Name")
    vol_join_date = st.date_input("Join Date", date.today())

    #Fetch locations
    try:
        resp_loc = requests.get(f"{API_URL}/stalls/locations")
        locs = resp_loc.json() if resp_loc.status_code == 200 else []

        # Display string → location_id
        loc_dict = {
            f"{l['area']} | {l['location']} | {l['type']} (ID: {l['id']})": l['id']
            for l in locs
        }

    except:
        loc_dict = {}
        st.error("Error fetching locations")
        st.stop()

    if not loc_dict:
        st.warning("No locations found.")
        st.stop()

    # Select location
    selected_location_key = st.selectbox(
        "Select Volunteers's Default Stall Location", list(loc_dict.keys())
    )
    vol_default_location_id = loc_dict[selected_location_key]


    if st.button("Add Volunteer"):
        if not vol_name.strip():
            st.warning("Volunteer name cannot be empty!")
        else:
            try:
                data = {"vol_name": vol_name.strip(), "vol_join_date": vol_join_date.isoformat(), "default_location_id": vol_default_location_id}
                response = requests.post(f"{API_URL}/volunteers/add-volunteer", json=data)
                if response.status_code == 200:
                    st.success("Volunteer added successfully!")
                    st.json(response.json())
                else:
                    st.error(f"Error: {response.json()}")
            except Exception as e:
                st.error(f"Request failed: {e}")

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"

# ----- MAKE VOLUNTEER LEAD -----
def make_lead_page():
    st.subheader("Make Volunteer a Lead")

    # Fetch volunteers
    try:
        resp_vol = requests.get(f"{API_URL}/volunteers/volunteer-list")
        vols = resp_vol.json() if resp_vol.status_code == 200 else []
        vol_dict = {f"{v['vol_name']} | ID: {v['id']}": v['id'] for v in vols}
    except:
        vol_dict = {}
        st.error("Error fetching volunteers")
        st.stop()
    if not vol_dict:
        st.warning("No volunteers found.")
        st.stop()

    # Mark volunteer a lead
    selected_vol_label = st.selectbox("Select Volunteer to make lead", list(vol_dict.keys()))
    volunteer_id = vol_dict[selected_vol_label]

    if st.button("Make Lead"):
        try:
            response = requests.post(f"{API_URL}/volunteers/make-volunteer-lead", params={"volunteer_id": volunteer_id})
            if response.status_code == 200:
                st.success("Volunteer is now a Lead!")
                st.json(response.json())
            else:
                st.error(f"Error: {response.json()}")
        except Exception as e:
            st.error(f"Request failed: {e}")

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"

# ----- ADD NEW BOOK TITLE -----
def add_book_title_page():
    st.subheader("Create a New Book Title")
    new_title = st.text_input("Book Title")
    category = st.text_input("Category")
    if st.button("Create Title"):
        if not new_title or not category:
            st.warning("Title and Category are required!")
        else:
            data = {"title": new_title, "category": category}
            try:
                response = requests.post(f"{API_URL}/books/add-new-title", json=data)
                if response.status_code == 200:
                    st.success(f"Title '{new_title}' added successfully!")
                else:
                    st.error(response.json())
            except Exception as e:
                st.error(f"Request failed: {e}")

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"

# ----- ADD BOOKS TO INVENTORY -----
def add_books_inventory_page():
    st.subheader("Add Books To Inventory")
    try:
        response = requests.get(f"{API_URL}/books/list-titles")

        if response.status_code == 200:
            titles = response.json()
        else:
            titles = []
    except Exception as e:
        st.error(f"Error fetching titles: {e}")
        titles = []

    if not titles:
        st.info("No titles found. Add a title first.")
        st.stop()


    title = st.selectbox("Select Book Title", titles)

    try:
        resp = requests.get(f"{API_URL}/books/list-batches", params={"title": title})
        batches = resp.json() if resp.status_code == 200 else []
    except:
        batches = []

    batch_options = ["New Batch"] + [
        f"Batch {b['id']} | MRP: {b['MRP']} | Copies: {b['copies_total']} | Date: {b['entrydate']}" for b in batches
    ]

    selected_batch = st.selectbox("Select Batch", batch_options)

    if selected_batch == "New Batch":
        batch_id = None
        mrp = st.number_input("MRP (for new batch)", min_value=1.0, step=1.0)
        entrydate = st.date_input("Entry Date", date.today())
    else:
        batch_id = int(selected_batch.split()[1])
        batch_data = next(b for b in batches if b["id"] == batch_id)
        mrp = batch_data["MRP"]
        entrydate = st.date_input("Entry Date (auto-filled)", date.fromisoformat(batch_data["entrydate"]), disabled=True)

    copies_total = st.number_input("Number of Copies", min_value=1, step=1)
    if st.button("Add Copies to Inventory"):
        payload = {
            "title": title,
            "batch_id": batch_id,
            "MRP": mrp,
            "entrydate": entrydate.isoformat(),
            "units": copies_total
        }
        try:
            resp = requests.post(f"{API_URL}/books/add-book", json=payload)
            if resp.status_code == 200:
                st.success(f"Added {copies_total} copies to inventory!")
                st.json(resp.json())
            else:
                st.error(resp.json())
        except Exception as e:
            st.error(f"Request failed: {e}")

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"



# ----- ASSIGN BOOKS (ADMIN ONLY) -----
def assign_books_page():
    st.subheader("Assign Books to Lead Volunteer")
    # Fetch leads
    try:
        response = requests.get(f"{API_URL}/volunteers/list-leads")
        leads = response.json() if response.status_code == 200 else []
        # Correct field name
        lead_dict = {f"{v['vol_name']} (ID: {v['id']})": v['id'] for v in leads}
    except Exception as e:
        lead_dict = {}
        st.error(f"Error fetching lead volunteers: {e}")

    if not lead_dict:
        st.warning("No lead volunteers found. Mark a volunteer as lead first.")
        st.stop()

    selected_label = st.selectbox("Select Lead Volunteer", list(lead_dict.keys()))
    selected_volunteer_id = lead_dict[selected_label]

    # Fetch unsold inventory
    try:
        inv_resp = requests.get(f"{API_URL}/inventory/unsold_inventory")
        inventory = inv_resp.json() if inv_resp.status_code == 200 else []
    except Exception as e:
        inventory = []
        st.error(f"Error fetching inventory: {e}")

    if not inventory:
        st.warning("No unsold books available in inventory.")
        st.stop()

    # Map inventory for selection
    book_options = {f"{b['title']} | Batch {b['batch_id']} | Available: {b['available']}": b for b in inventory}
    selected_book_label = st.selectbox("Select Book", list(book_options.keys()))
    batch_data = book_options[selected_book_label]

    max_units = batch_data["available"]
    units_to_assign = st.number_input(f"Number of Copies to Assign (Max {max_units})", min_value=1, max_value=max_units, step=1)

    if st.button("Assign Books"):
        payload = {
            "volunteer_id": selected_volunteer_id,
            "batch_id": batch_data["batch_id"],
            "units": units_to_assign
        }
        try:
            resp = requests.post(f"{API_URL}/books/assign-books", json=payload)
            if resp.status_code == 200:
                st.success(f"{units_to_assign} copies of '{batch_data['title']}' assigned to {selected_label}")
                st.json(resp.json())
            else:
                st.error(resp.json())
        except Exception as e:
            st.error(f"Request failed: {e}")

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"

# ----- RETURN BOOKS -----Lead Volunteer Only
def return_books_page():
    st.subheader("Return Books to Admin")

    # ----------------------------- #
    # 1. FETCH LEAD VOLUNTEERS
    # ----------------------------- #

    try:
        response = requests.get(f"{API_URL}/volunteers/list-leads")
        leads = response.json() if response.status_code == 200 else []

        if not leads:
            st.error("No lead volunteers found. Mark a volunteer as lead first.")
            st.stop()
        #Create display label -> ID mapping
        lead_dict = {
            f" {v['vol_name']} (ID: {v['id']})": v['id']
            for v in leads
        }

    except Exception as e:
        lead_dict = {}
        st.error(f"Error fetching lead volunteers: {e}")
        st.stop()


    selected_label = st.selectbox("Select Lead Volunteer", list(lead_dict.keys()))
    volunteer_lead_id = lead_dict[selected_label]

    # ----------------------------- #
    # 2. FETCH ASSIGNED BOOKS FOR THIS LEAD
    # ----------------------------- #

    #Get title and batch IDs assigned to this volunteer lead but not sold
    try:
        response = requests.get(f"{API_URL}/inventory/volunteer_inventory", params={"volunteer_id": volunteer_lead_id})
        vol_inventory = response.json() if response.status_code == 200 else []

        if not vol_inventory:
            st.warning("This volunteer lead has no assigned books.")
            st.stop()

        # Create display label -> Object mapping
        return_dict = {
            f" {a['title']} | Batch ID: {a['batch_id']} | available: {a['available']}":
                {
                    "batch_id": a["batch_id"],
                    "title": a["title"],
                    "available": a["available"],
                }
            for a in vol_inventory
        }

    except Exception as e:
        return_dict = {}
        st.error(f"Error fetching assigned copies to this volunteer lead: {e}")
        st.stop()

    selected_label = st.selectbox("Select title/batch to return", list(return_dict.keys()))
    selected_data = return_dict[selected_label]

    title = selected_data["title"]
    batch_id = selected_data["batch_id"]
    copies_available = selected_data["available"]
    copies_return = st.number_input("Copies Return", min_value=1, max_value=copies_available, step=1)

    # ----------------------------- #
    # 3. PROCESS RETURN
    # ----------------------------- #

    if st.button("Return Books"):
        #Prepare payload
        if copies_return < 1 or copies_return > copies_available:
            st.warning(f"You can return between 1 and {copies_available} copies.")
        else:
            payload = {
                "volunteer_id": volunteer_lead_id,
                "title": title.strip(),
                "batch_id": batch_id,
                "copies_return": copies_return
            }
        #API call
        try:
            resp = requests.post(f"{API_URL}/books/return-books", json=payload)
            if resp.status_code == 200:
                st.success(f"Returned {copies_return} copies of {title}")
                st.json(resp.json())
            else:
                st.error(resp.json())

        except Exception as e:
            st.error(f"Request failed: {e}")

    # ----------------------------- #
    # 4. BACK BUTTON
    # ----------------------------- #

    if st.button("Back to Home"):
        st.session_state.page = "Home"


# ----- ADD STALL -----
def add_stall_page():


    st.subheader("Add a Stall")
    stall_date = st.date_input("Stall Date", date.today())

    #Fetch lead volunteers
    try:
        resp_leads = requests.get(f"{API_URL}/volunteers/list-leads")
        lead_vols = resp_leads.json() if resp_leads.status_code == 200 else []
        lead_dict = {f"{v['vol_name']} | ID: {v['id']}" : v ['id'] for v in lead_vols}
    except:
        lead_dict ={}
        st.error("Error fetching lead volunteers")
        st.stop()
    if not lead_dict:
        st.warning("No lead volunteers found.")
        st.stop()

    #Select lead volunteer
    selected_lead_label = st.selectbox("Select Lead Volunteer", list(lead_dict.keys()))
    volunteer_lead_id = lead_dict[selected_lead_label]

    # Fetch volunteers
    try:
        resp_vol = requests.get(f"{API_URL}/volunteers/volunteer-list")
        vols = resp_vol.json() if resp_vol.status_code == 200 else []
        vol_dict = {f"{v['vol_name']} | ID: {v['id']}": v['id'] for v in vols}
    except:
        vol_dict = {}
        st.error("Error fetching volunteers")
        st.stop()
    if not vol_dict:
        st.warning("No volunteers found.")
        st.stop()

    # Select volunteers
    selected_vol_labels = st.multiselect("Select Volunteers for this stall", list(vol_dict.keys()))
    volunteer_ids = [vol_dict[label] for label in selected_vol_labels]
    volunteer_ids = list(set(volunteer_ids + [volunteer_lead_id])) #Auto include lead volunteer in volunteer list

    #Fetch default location of lead
    default_location_id = next(
        (v.get('default_location_id') for v in lead_vols if v['id'] == volunteer_lead_id),
        None
    )

    #Fetch Locations
    try:
        resp_loc = requests.get(f"{API_URL}/stalls/locations")
        locs = resp_loc.json() if resp_loc.status_code == 200 else []

        # Display string → location_id
        loc_dict = {
            f"{l['area']} | {l['location']} | {l['type']} (ID: {l['id']})": l['id']
            for l in locs
        }
        loc_keys = list(loc_dict.keys())

    except:
        loc_dict = {}
        st.error("Error fetching locations")
        st.stop()

    if not loc_dict:
        st.warning("No locations found.")
        st.stop()

    # Preselect default location of lead volunteer
    default_key = next(
        (k for k, v in loc_dict.items() if v == default_location_id),
        loc_keys[0]  # fallback when no default found
    )

    # Select location
    selected_location_key = st.selectbox(
        "Select Stall Location",
        loc_keys,
        index=loc_keys.index(default_key)
    )

    # Convert back to location_id
    stall_location_id = loc_dict[selected_location_key]

    # Submit
    if st.button("Create Stall"):
        st.session_state.create_stall = True

    if st.session_state.get("create_stall"):

        data = {
            "location_id": stall_location_id,
            "stall_date": stall_date.isoformat(),
            "volunteer_ids": volunteer_ids,
            "volunteer_lead_id": volunteer_lead_id
        }

        response = requests.post(f"{API_URL}/stalls/create", json=data)

        if response.status_code == 200:
            st.success("Stall created!")
            st.session_state.create_stall = False


    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"

# ----- UPDATE SALE -----
def update_sale_page():
    st.subheader("Update Sold Books for Stall")

    # Fetch all stalls
    try:
        response = requests.get(f"{API_URL}/stalls/monthly-stall-list")
        stalls_data = response.json() if response.status_code == 200 else {}
    except Exception as e:
        st.error(f"Failed to fetch stalls: {e}")
        st.stop()

    # Flatten month → list of stalls
    stalls = [s for month in stalls_data.values() for s in month]
    if not stalls:
        st.warning("No stalls available.")
        st.stop()

    # Stall dropdown
    stall_options = {
        f"{s['stall_id']} — {s['stall_location']} ({s['stall_date']})": s
        for s in stalls
    }
    selected_stall_label = st.selectbox("Select Stall", list(stall_options.keys()))
    selected_stall = stall_options[selected_stall_label]

    lead_volunteer_id = selected_stall.get("lead_volunteer_id")
    if not lead_volunteer_id:
        st.error("Lead volunteer ID missing for this stall. Please fix backend monthly list.")
        st.stop()

    # Fetch assigned books for lead volunteer
    try:
        response = requests.get(
            f"{API_URL}/books/volunteer_inventory",
            params={"volunteer_id": lead_volunteer_id}
        )
        vol_inventory = response.json() if response.status_code == 200 else []
    except Exception as e:
        vol_inventory = []
        st.error(f"Failed to fetch volunteer inventory: {e}")

    if not vol_inventory:
        st.warning("No inventory for this stall's lead volunteer.")
        if st.button("⬅️ Back to Home"):
            st.session_state.page = "Home"
        st.stop()

    # Select a book
    book_options = {
        f"{b['title']} | Batch {b['batch_id']} | Units: {b['available']}": b
        for b in vol_inventory
    }
    selected_book_label = st.selectbox("Select Book", list(book_options.keys()))
    book_data = book_options[selected_book_label]

    max_sold = book_data["available"]
    copies_sold = st.number_input(f"Number of Copies Sold (Max {max_sold})", min_value=1, max_value=max_sold, step=1)
    selling_price = st.number_input("Selling Price per Copy", min_value=1.0, step=1.0)

    # Submit button — POST only fires here
    if st.button("Update Sale"):
        payload = {
            "stall_id": int(selected_stall["stall_id"]),
            "sold_books": [
                {
                    "title": str(book_data["title"]),
                    "batch_id": int(book_data["batch_id"]),
                    "copies_sold": int(copies_sold),
                    "book_selling_price_per_copy": float(selling_price),
                }
            ]
        }

        try:
            resp = requests.post(
                f"{API_URL}/stalls/{selected_stall['stall_id']}/add-sales",
                json=payload
            )
            if resp.status_code == 200:
                st.success("Sale updated successfully!")
                st.json(resp.json())
            else:
                st.error(resp.json())
        except Exception as e:
            st.error(f"Request failed: {e}")

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"





def stall_performance_page():
    try:
        st.subheader("View Stall Performance")

        # ---- Session state ----
        if "stall_loaded" not in st.session_state:
            st.session_state.stall_loaded = False
        if "selected_stall_id" not in st.session_state:
            st.session_state.selected_stall_id = None
        if "stalls_data" not in st.session_state:
            st.session_state.stalls_data = {}

        # ---- Fetch all stalls ----
        if not st.session_state.stalls_data:
            try:
                response = requests.get(f"{API_URL}/stalls/monthly-stall-list")
                if response.status_code == 200:
                    st.session_state.stalls_data = response.json()
                else:
                    st.error(f"Failed to fetch stalls list: {response.status_code}")
                    return
            except Exception as e:
                st.error(f"Exception fetching stalls: {e}")
                return

        stalls = [s for month in st.session_state.stalls_data.values() for s in month]
        if not stalls:
            st.warning("No stalls available.")
            return

        stall_options = {
            f"{s['stall_id']} — {s.get('stall_location') or 'Location not entered'} ({s['stall_date']})": s
            for s in stalls
        }
        selected_label = st.selectbox("Select Stall", list(stall_options.keys()))
        selected_stall = stall_options[selected_label]
        selected_stall_id = selected_stall["stall_id"]

        # Reset on button
        if st.button("Get Performance"):
            st.session_state.selected_stall_id = selected_stall_id
            st.session_state.stall_loaded = False

        # ---- Fetch stall data ----
        if st.session_state.selected_stall_id and not st.session_state.stall_loaded:
            try:
                resp = requests.get(
                    f"{API_URL}/stalls/stall-performance",
                    params={"stall_id": st.session_state.selected_stall_id}
                )
                if resp.status_code == 200:
                    st.session_state.stall_data = resp.json()
                    st.session_state.stall_loaded = True
                else:
                    st.error(f"Failed to fetch stall performance: {resp.status_code}")
                    st.session_state.stall_data = None
            except Exception as e:
                st.error(f"Exception fetching stall performance: {e}")
                st.session_state.stall_data = None

        # ---- Render data ----
        data = st.session_state.get("stall_data")
        if data:
            stall_info = data.get("stall", {})
            st.markdown("### Stall Info")
            st.write(f"**ID:** {stall_info.get('stall_id')}")
            st.write(f"**Location:** {stall_info.get('stall_location') or 'Location not entered'}")
            st.write(f"**Date:** {stall_info.get('stall_date')}")

            volunteers = stall_info.get("volunteers", [])
            st.markdown("### Volunteers")
            st.write(", ".join(volunteers) if volunteers else "No volunteers assigned.")

            performance = data.get("performance", [])
            if performance:
                rows = [{"Title": r["Title"], "Batch ID": r["Batch ID"], "Sold": r["Sold"], "Revenue": r["Revenue"]} for r in performance]
                st.markdown("### Performance by Title & Batch")
                st.table(rows)
                st.metric("Total Sold", sum(r["Sold"] for r in rows))
                st.metric("Total Revenue", sum(r["Revenue"] for r in rows))
            else:
                st.info("No performance data for this stall.")

        # ---- Back button ----
        if st.button("⬅️ Back to Home"):
            st.session_state.page = "Home"
            st.session_state.stall_loaded = False
            st.session_state.stall_data = None
            st.session_state.selected_stall_id = None

    except Exception as e:
        st.error(f"Unexpected error in stall_performance_page: {e}")





def inventory_summary_page():
    st.subheader("Inventory Summary")

    # Initialize session state for refresh
    if "inventory_loaded" not in st.session_state:
        st.session_state.inventory_loaded = False

    # Fetch lead volunteers
    try:
        resp_leads = requests.get(f"{API_URL}/volunteers/list-leads")
        lead_vols = resp_leads.json() if resp_leads.status_code == 200 else []
        lead_dict = {f"{v['vol_name']} | ID: {v['id']}": v['id'] for v in lead_vols}
    except:
        lead_dict = {}
        st.error("Error fetching lead volunteers")
        st.stop()

    if not lead_dict:
        st.warning("No lead volunteers found.")
        st.stop()

    # Add admin view to dropdown
    lead_dict = {"Admin": None, **lead_dict}

    # Select view
    selected_lead_label = st.selectbox("Select Inventory View", list(lead_dict.keys()))
    volunteer_lead_id = lead_dict[selected_lead_label]

    # Fetch inventory only once per session or when volunteer selection changes
    if not st.session_state.inventory_loaded or st.session_state.get("last_volunteer_id") != volunteer_lead_id:
        try:
            if volunteer_lead_id:
                response = requests.get(f"{API_URL}/inventory/volunteer_inventory", params={"volunteer_id": volunteer_lead_id})
                inv = response.json() if response.status_code == 200 else []
            else:
                response = requests.get(f"{API_URL}/inventory/unsold_inventory")
                inv = response.json() if response.status_code == 200 else []

            st.session_state.inventory_data = inv
            st.session_state.inventory_loaded = True
            st.session_state.last_volunteer_id = volunteer_lead_id

        except Exception as e:
            st.error(f"Failed to fetch inventory summary: {e}")
            st.stop()

    inv = st.session_state.inventory_data

    if not inv:
        st.warning("No inventory data found.")
        st.stop()

    table_data = []
    for row in inv:
        table_data.append({
            "Title": row.get("title", "N/A"),
            "Batch ID": row.get("batch_id"),
            "Total": row.get("total", row.get("assigned", 0) + row.get("sold", 0) + row.get("returned",0)),
            "Available": row.get("available"),
            "Assigned": row.get("assigned"),
            "Returned": row.get("returned"),
            "Sold": row.get("sold"),
            "Volunteers": row.get("lead_volunteer"),
        })

    st.table(table_data)

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"
        st.session_state.inventory_loaded = False  # Reset when leaving page

import streamlit as st
import pandas as pd
import altair as alt
import requests
from datetime import date

API_URL = "http://127.0.0.1:8000"  # adjust if needed


def volunteer_attendance_page():
    st.title("Volunteer Attendance")

    # ---- Load volunteers ----
    try:
        resp_vol = requests.get(f"{API_URL}/volunteers/volunteer-list")
        vols = resp_vol.json() if resp_vol.status_code == 200 else []
    except Exception as e:
        st.error(f"Failed to fetch volunteers: {e}")
        return

    if not vols:
        st.info("No volunteers found")
        return

    vol_dict = {f"{v['vol_name']} | ID {v['id']}": v['id'] for v in vols}
    selected_vol = st.selectbox("Select Volunteer", list(vol_dict.keys()))
    volunteer_id = vol_dict[selected_vol]

    # ---- Month Picker (Calendar) ----
    picked_dates = st.date_input(
        "Select Month(s)",
        value=[],
        help="Pick one or more dates — they will be converted into month names."
    )

    if isinstance(picked_dates, date):
        picked_dates = [picked_dates]  # handle single date

    months = sorted({d.strftime("%Y-%m") for d in picked_dates})

    # ---- Session state ----
    if "volreport_loaded" not in st.session_state:
        st.session_state.volreport_loaded = False

    if st.button("Get Report"):
        st.session_state.volreport_loaded = False

    if not months:
        st.info("Please select one or more months.")
        return

    # ---- Fetch only when needed ----
    if (
        not st.session_state.volreport_loaded
        or st.session_state.get("last_volunteer_id") != volunteer_id
        or st.session_state.get("last_months") != months
    ):
        try:
            # Send months as multiple query params
            response = requests.get(
                f"{API_URL}/reports/volunteer-attendance",
                params=[("month", m) for m in months] + [("volunteer_id", volunteer_id)],
            )

            if response.status_code != 200:
                st.error(f"Failed to fetch volunteer report: {response.status_code}")
                return

            st.session_state.volreport_data = response.json()
            st.session_state.volreport_loaded = True
            st.session_state.last_volunteer_id = volunteer_id
            st.session_state.last_months = months

        except Exception as e:
            st.error(f"Error fetching report: {e}")
            return

    # ---- Render ----
    render_volunteer_report(st.session_state.volreport_data, months)

    # ---- Back button ----
    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"

def render_volunteer_report(data, months_selected):
    if not data or not data.get("mom"):
        st.info("No data available for selected months")
        return

    st.success(f"Volunteer Attendance: {', '.join(months_selected)}")

    st.metric("Total Stalls Attended", data.get("stalls_attended", 0))

    # Convert mom to DataFrame
    mom_list = data.get("mom", [])
    df = pd.DataFrame([
        {"month": d["month"], "stalls": d["stalls_attended"]}
        for d in mom_list
    ])

    # Altair chart
    chart = alt.Chart(df).mark_bar().encode(
        x="month:N",
        y="stalls:Q",
        tooltip=["month", "stalls"]
    )
    st.altair_chart(chart, use_container_width=True)

    # Table
    st.subheader("Monthly Stalls Attended")
    st.table(df[["month", "stalls"]])

def admin_performance_page():
    st.title("Admin Performance Report")

    # ---- Session state ----
    if "admin_loaded" not in st.session_state:
        st.session_state.admin_loaded = False

    # ---- Month Picker ----
    picked_dates = st.date_input(
        "Select Month(s)",
        value=[],
        help="Pick one or more dates — they will be converted into months."
    )

    # Convert selected dates to unique YYYY-MM strings
    months = sorted({d.strftime("%Y-%m") for d in picked_dates})

    if not months:
        st.info("Please select one or more months.")
        return

    # ---- Fetch report ----
    if not st.session_state.admin_loaded or st.session_state.get("last_months") != months:
        try:
            # Send as repeated query params
            params = [("months", m) for m in months]
            response = requests.get(f"{API_URL}/reports/admin-performance", params=params)

            if response.status_code != 200:
                st.error("Failed to fetch admin report.")
                return

            st.session_state.admin_data = response.json()
            st.session_state.admin_loaded = True
            st.session_state.last_months = months

        except Exception as e:
            st.error(f"Error: {e}")
            return

    # ---- Render ----
    render_admin_report(st.session_state.admin_data, months)

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"
        st.session_state.admin_loaded = False


def render_admin_report(data, months):
    st.success(f"Admin Performance Report: {', '.join(months)}")

    # Metrics summary
    st.metric("Total Stalls", data.get("total_stalls", 0))
    st.metric("Total Books Sold", data.get("books_sold", 0))
    st.metric("Total Revenue", data.get("revenue", 0))

    # MoM table
    if "mom" in data:
        st.subheader("📊 Month-wise Performance")
        st.table(pd.DataFrame(data["mom"]))

    st.subheader("#Stalls")
    st.bar_chart({m["month"]: m["total_stalls"] for m in data.get("mom", [])})

    st.subheader("#Books Sold")
    st.bar_chart({m["month"]: m["books_sold"] for m in data.get("mom", [])})

    st.subheader("Revenue, INR")
    st.bar_chart({m["month"]: m["revenue"] for m in data.get("mom", [])})


    titles = data.get("titles", [])

    if titles:
        st.subheader("📚 Title-wise Summary")

        try:
            df_titles = pd.DataFrame(titles)
            st.dataframe(df_titles)

            # --- Title-wise Books Sold Chart ---
            st.subheader("Books Sold per Title")
            st.bar_chart({
                row["title"]: row["sold"]
                for _, row in df_titles.iterrows()
            })

            # --- Title-wise Revenue Chart ---
            st.subheader("Revenue per Title (INR)")
            st.bar_chart({
                row["title"]: row["revenue"]
                for _, row in df_titles.iterrows()
            })

        except Exception as e:
            st.error(f"Error rendering titles table: {e}")


def lead_performance_page():
    st.title("Lead Performance Report")

    if "lead_loaded" not in st.session_state:
        st.session_state.lead_loaded = False

    # Fetch leads
    resp_leads = requests.get(f"{API_URL}/volunteers/list-leads")
    leads = resp_leads.json() if resp_leads.status_code == 200 else []
    lead_dict = {f"{v['vol_name']} | ID {v['id']}": v['id'] for v in leads}

    selected_lead = st.selectbox("Select Lead Volunteer", list(lead_dict.keys()))
    lead_id = lead_dict[selected_lead]

    # Month picker
    picked_dates = st.date_input(
        "Select Month(s)", value=[], help="Pick one or more dates."
    )
    if isinstance(picked_dates, date):
        picked_dates = [picked_dates]
    months = sorted({d.strftime("%Y-%m") for d in picked_dates})

    if st.button("Get Report"):
        st.session_state.lead_loaded = False

    if not months:
        st.info("Please select one or more months.")
        return

    # ---- Fetch only if needed ----
    if (
        not st.session_state.lead_loaded
        or st.session_state.get("last_lead_id") != lead_id
        or st.session_state.get("last_months") != months
    ):
        try:
            params = [("lead_id", lead_id)] + [("months", m) for m in months]
            response = requests.get(f"{API_URL}/reports/lead-performance", params=params)

            if response.status_code != 200:
                st.error(f"Failed to fetch lead report ({response.status_code})")
                return

            st.session_state.lead_data = response.json()
            st.session_state.lead_loaded = True
            st.session_state.last_lead_id = lead_id
            st.session_state.last_months = months

        except Exception as e:
            st.error(f"Error: {e}")
            return

    render_lead_report(st.session_state.lead_data, months)

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"
        st.session_state.lead_loaded = False




def render_lead_report(data, months):
    st.success(f"Lead Performance Report: {months[0]}")

    # Metrics summary
    total_stalls = sum([r.get("stalls_led", 0) for r in data])
    total_books = sum([r.get("books_sold_total", 0) for r in data])
    total_revenue = sum([r.get("revenue_total", 0) for r in data])

    st.metric("Total Stalls Led", total_stalls)
    st.metric("Total Books Sold", total_books)
    st.metric("Total Revenue", total_revenue)

    # Title-wise table
    if "title_wise" in data[0]:
        st.subheader("📚 Title-wise Performance")
        title_rows = []
        for r in data:
            for t in r.get("title_wise", []):
                title_rows.append(t)
        if title_rows:
            st.table(pd.DataFrame(title_rows))

    # MoM chart
    df = pd.DataFrame(data)
    if not df.empty:
        df['month_label'] = df['month']
        chart = alt.Chart(df).mark_line(point=True).encode(
            x='month_label:N',
            y='books_sold_total:Q',
            tooltip=['month_label', 'stalls_led', 'books_sold_total', 'revenue_total']
        )
        st.altair_chart(chart, use_container_width=True)


def location_performance_page():
    st.title("Location Performance")

    #Sessions state
    if "location_loaded" not in st.session_state:
        st.session_state.location_loaded = False

    #Month Picker
    picked_dates = st.date_input("Select Month(s)", value=[], help = "Pick one or more dates - the will be converted into months.")

    months = sorted({d.strftime("%Y-%M") for d in picked_dates})

    if not months:
        st.info("Please select one or more months.")
        return

    #Fetch report
    if not st.session_state.location_loaded or st.session_state.get("last month") != months:
        try:
            params = [("months", m) for m in months]
            response = requests.get(f"{API_URL}/reports/location-performance", params= params)
            if response.status_code != 200:
                st.error(f"Failed to fetch location report ({response.status_code})")
                return

            st.session_state.location_data = response.json()
            st.session_state.location_loaded = True
            st.session_state.last_months = months

        except Exception as e:
            st.error(f"Error: {e}")
            return

    #Render report

    render_location_performance(st.session_state.location_data, months)
    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"
        st.session_state.location_loaded = False
        st.session_state.last_months = months

#Render Location Report
def render_location_performance(data, months):
    st.success(f"Location Performance Report: {', '.join(months)}")

    #Metrics Summary
    total_stalls = sum(loc["stalls"] for loc in data)
    total_books = sum(loc["sold"] for loc in data)
    total_rev = sum(loc["revenue"] for loc in data)

    st.metric("Total Stalls Led", total_stalls)
    st.metric("Total Books Sold", total_books)
    st.metric("Total Revenue", total_rev)

    #Table view
    st.subheader("📍Location-wise performance")
    st.table(pd.DataFrame(data))

    #Charts
    st.subheader("#Stalls By Location")
    st.bar_chart({loc["location"]: loc["stalls"] for loc in data})

    st.subheader("#Books Sold By Location")
    st.bar_chart({loc["location"]: loc["sold"] for loc in data})

    st.subheader("Revenue (INR) By Location")
    st.bar_chart({loc["location"]: loc["revenue"] for loc in data})




# ----- PAGE ROUTING -----
page = st.session_state.page
if page == "Home":
    home_page()
elif page == "Add New Location":
    add_new_location_page()
elif page == "Add Volunteer":
    add_volunteer_page()
elif page == "Make Volunteer Lead":
    make_lead_page()
elif page == "Add New Book Title":
    add_book_title_page()
elif page == "Add Books To Inventory":
    add_books_inventory_page()
elif page == "Assign Books":
    assign_books_page()
elif page == "Add Stall":
    add_stall_page()
elif page == "Update Sale":
    update_sale_page()
elif page == "Return Book":
    return_books_page()
elif page == "Inventory Summary":
    inventory_summary_page()
elif page == "Admin Performance Report":
    admin_performance_page()
elif page == "Lead Performance Report":
    lead_performance_page()
elif page == "Stall Performance":
    stall_performance_page()
elif page == "Location Performance":
    location_performance_page()
elif page == "Volunteer Attendance":
    volunteer_attendance_page()
