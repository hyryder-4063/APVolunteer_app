import streamlit as st
import requests
from datetime import date

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

    # --- DASHBOARDS ---
    with col3:
        st.markdown("### 📊 Dashboards")
        if st.button("Stall Performance"):
            st.session_state.page = "Stall Performance"
        if st.button("Inventory Summary"):
            st.session_state.page = "Inventory Summary"
        if st.button("Admin Monthly Dashboard"):
            st.session_state.page = "Admin Monthly Dashboard"

# ----- ADD VOLUNTEER -----
def add_volunteer_page():
    st.subheader("Add a New Volunteer")
    vol_name = st.text_input("Volunteer Name")
    vol_join_date = st.date_input("Join Date", date.today())

    if st.button("Add Volunteer"):
        if not vol_name.strip():
            st.warning("Volunteer name cannot be empty!")
        else:
            try:
                data = {"vol_name": vol_name.strip(), "vol_join_date": vol_join_date.isoformat()}
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
    volunteer_id = st.number_input("Volunteer ID", min_value=1, step=1)
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
        titles = response.json() if response.status_code == 200 else []
    except:
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
            "copies_total": copies_total
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
        inv_resp = requests.get(f"{API_URL}/books/unsold_inventory")
        inventory = inv_resp.json() if response.status_code == 200 else []
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
            "title": batch_data["title"],
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

# ----- ADD STALL -----
def add_stall_page():
    st.subheader("Add a Stall")
    stall_location = st.text_input("Stall Location")
    stall_date = st.date_input("Stall Date", date.today())
    volunteer_ids_text = st.text_area("Volunteer IDs (comma separated)")
    volunteer_lead_id = st.number_input("Lead Volunteer ID", min_value=1, step=1)

    volunteer_ids = [int(v.strip()) for v in volunteer_ids_text.split(",") if v.strip().isdigit()]

    if st.button("Add Stall"):
        payload = {
            "stall_location": stall_location,
            "stall_date": stall_date.isoformat(),
            "volunteer_ids": volunteer_ids,
            "volunteer_lead_id": volunteer_lead_id
        }
        try:
            res = requests.post(f"{API_URL}/stalls/create", json=payload)
            if res.status_code == 200:
                st.success("Stall added successfully!")
                st.json(res.json())
            else:
                st.error(res.json())
        except Exception as e:
            st.error(f"Error submitting: {e}")

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

    # Correct lead volunteer ID from backend
    lead_volunteer_id = selected_stall["lead_volunteer_id"]
    if not lead_volunteer_id:
        st.error("Lead volunteer ID missing for this stall. Please fix backend monthly list.")
        st.stop()

    # Fetch assigned books for the lead volunteer of this stall
    try:
        response = requests.get(
            f"{API_URL}/books/assigned_books",
            params={"volunteer_id": lead_volunteer_id}
        )
        assigned_books = response.json() if response.status_code == 200 else []

    except Exception as e:
        assigned_books = []
        st.error(f"Failed to fetch assigned books: {e}")

    if not assigned_books:
        st.warning("No books assigned for this stall's lead volunteer.")
        st.stop()

    # Select a book
    book_options = {
        f"{b['title']} | Batch {b['batch_id']} | Units: {b['copies_assigned']}": b
        for b in assigned_books
    }
    selected_book_label = st.selectbox("Select Book", list(book_options.keys()))
    book_data = book_options[selected_book_label]

    max_sold = book_data["copies_assigned"]
    copies_sold = st.number_input(f"Number of Copies Sold (Max {max_sold})", min_value=1, max_value=max_sold, step=1)
    selling_price = st.number_input("Selling Price per Copy", min_value=1.0, step=1.0)

    if st.button("Update Sale"):
        payload = {
            "stall_id": selected_stall["stall_id"],
            "sold_books": [
                {
                    "title": book_data["title"],
                    "batch_id": book_data["batch_id"],
                    "copies_sold": copies_sold,
                    "book_selling_price_per_copy": selling_price,
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
    st.subheader("View Stall Performance")

    # Fetch all stalls
    try:
        response = requests.get(f"{API_URL}/stalls/monthly-stall-list")
        stalls_data = response.json() if response.status_code == 200 else {}
    except Exception as e:
        st.error(f"Failed to fetch stalls: {e}")
        st.stop()

    # Flatten stalls from monthly map
    stalls = [s for month in stalls_data.values() for s in month]
    if not stalls:
        st.warning("No stalls available.")
        st.stop()

    # Prepare selectbox options with default location if missing
    stall_options = {
        f"{s['stall_id']} — {s.get('stall_location') or 'Location not entered'} ({s['stall_date']})": s
        for s in stalls
    }
    selected_stall_label = st.selectbox("Select Stall", list(stall_options.keys()))
    selected_stall = stall_options[selected_stall_label]

    if st.button("Get Performance"):
        try:
            resp = requests.get(
                f"{API_URL}/stalls/stall-performance",
                params={"stall_id": selected_stall["stall_id"]}
            )
            if resp.status_code == 200:
                data = resp.json()
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
                    rows = []
                    for row in performance:
                        rows.append({
                            "Title": row.get("Title"),
                            "Batch ID": row.get("Batch ID", "N/A"),
                            "Sold": row.get("Sold", 0),
                            "Revenue": row.get("Revenue", 0)
                        })
                    st.markdown("### Performance by Title & Batch")
                    st.table(rows)

                    st.metric("Total Sold", sum(r["Sold"] for r in rows))
                    st.metric("Total Revenue", sum(r["Revenue"] for r in rows))
                else:
                    st.info("No performance data for this stall.")
            else:
                st.error(resp.json())
        except Exception as e:
            st.error(f"Failed to fetch stall performance: {e}")

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"

def inventory_summary_page():
    st.subheader("Inventory Summary (Batch-wise)")

    try:
        response = requests.get(f"{API_URL}/books/unsold_inventory")
        if response.status_code == 200:
            inv = response.json()
            if not inv:
                st.warning("No inventory data found.")
                st.stop()

            table_data = []
            for row in inv:
                table_data.append({
                    "Title": row.get("title", "N/A"),
                    "Batch ID": row.get("batch_id"),
                    "Available": row.get("available")
                })
            st.table(table_data)
        else:
            st.error(f"Error fetching inventory: {response.text}")
            st.stop()
    except Exception as e:
        st.error(f"Failed to fetch inventory summary: {e}")
        st.stop()

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"



def admin_monthly_dashboard_page():
    st.subheader("Admin Monthly Dashboard")
    today = date.today()
    default_month = today.strftime("%Y-%m")
    selected_month = st.text_input("Enter Month (YYYY-MM)", default_month)

    try:
        year, mon = map(int, selected_month.split("-"))
        if not (1 <= mon <= 12):
            raise ValueError
    except ValueError:
        st.warning("Please enter month in correct format: YYYY-MM (e.g., 2025-12)")
    else:
        if st.button("Get Monthly Report"):
            try:
                response = requests.get(f"{API_URL}/reports/admin-monthly-performance", params={"month": selected_month})
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"Report for {selected_month}")

                    # Original metrics
                    st.metric("Total Stalls", data.get("total_stalls", 0))
                    st.metric("Total Books Sold", data.get("total_books_sold", 0))
                    st.metric("Total Monthly Revenue", data.get("monthly_revenue", 0))

                    # NEW: Title-wise table
                    if "title_wise" in data and data["title_wise"]:
                        st.subheader("📚 Title-wise Performance")
                        title_rows = []
                        for t in data["title_wise"]:
                            title_rows.append({
                                "Title": t["title"],
                                "Sold Units": t["total_sold"],
                                "Revenue": t["total_revenue"]
                            })
                        st.table(title_rows)

                    # NEW: Stall-wise table
                    if "stall_wise" in data and data["stall_wise"]:
                        st.subheader("🏪 Stall-wise Performance")
                        stall_rows = []
                        for s in data["stall_wise"]:
                            stall_rows.append({
                                "Stall ID": s["stall_id"],
                                "Books Sold": s["books_sold"],
                                "Revenue": s["revenue"]
                            })
                        st.table(stall_rows)

                    # Existing charts
                    st.subheader("#Stalls by number of books sold")
                    sold_cat = data.get("stall_bookssoldcat", {})
                    st.bar_chart(sold_cat)

                    st.subheader("#Stalls by monthly revenue")
                    rev_cat = data.get("stall_revcat", {})
                    st.bar_chart(rev_cat)

                    st.subheader("#Volunteers by number of stalls attended")
                    vol_att = data.get("vol_attendance", {})
                    st.bar_chart(vol_att)

                elif response.status_code == 404:
                    st.info(f"No stalls found for {selected_month}")
                else:
                    st.error(f"Error fetching report: {response.json()}")
            except Exception as e:
                st.error(f"Request failed: {e}")

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "Home"





# ----- PAGE ROUTING -----
page = st.session_state.page
if page == "Home":
    home_page()
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
elif page == "Stall Performance":
    stall_performance_page()
elif page == "Inventory Summary":
    inventory_summary_page()
elif page == "Admin Monthly Dashboard":
    admin_monthly_dashboard_page()
