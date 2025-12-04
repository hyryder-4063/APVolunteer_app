import streamlit as st
import requests
from datetime import date

# ----- CONFIG -----
API_URL = "http://127.0.0.1:8000"  # Your FastAPI URL

# ----- APP TITLE -----
st.title("Volunteer Book Stall Management")

# ----- SESSION STATE FOR PAGE NAVIGATION -----
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

    # --- VOLUNTEER ---
    with col2:
        st.markdown("### 🙋 Volunteer")
        if st.button("Assign Books"):
            st.session_state.page = "Assign Books"
        if st.button("Add/Close Stall"):
            st.session_state.page = "Add/Close Stall"

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
        try:
            data = {"vol_name": vol_name, "vol_join_date": vol_join_date.isoformat()}
            response = requests.post(f"{API_URL}/volunteers/add-volunteer", json=data)
            if response.status_code == 200:
                st.success("Volunteer added successfully!")
                st.json(response.json())
            else:
                st.error(f"Error: {response.json()}")
        except Exception as e:
            st.error(f"Request failed: {e}")

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

# ----- ADD BOOKS TO INVENTORY -----
def add_books_inventory_page():
    st.subheader("Add Books To Inventory")

    # Fetch existing titles
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
        f"Batch {b['id']} | MRP: {b['MRP']} | Date: {b['entrydate']}" for b in batches
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
        entrydate = st.date_input(
            "Entry Date (auto-filled for existing batch)",
            date.fromisoformat(batch_data["entrydate"]),
            disabled=True
        )

    units = st.number_input("Number of Copies", min_value=1, step=1)
    if st.button("Add Copies to Inventory"):
        payload = {
            "title": title,
            "units": units,
            "batch_id": batch_id,
            "MRP": mrp,
            "entrydate": entrydate.isoformat()
        }
        try:
            resp = requests.post(f"{API_URL}/books/add-book", json=payload)
            if resp.status_code == 200:
                st.success(f"Added {units} copies to inventory!")
                st.json(resp.json())
            else:
                st.error(resp.json())
        except Exception as e:
            st.error(f"Request failed: {e}")

# ----- ASSIGN BOOKS -----
def assign_books_page():
    st.subheader("Assign Books to Lead Volunteer")
    try:
        response = requests.get(f"{API_URL}/volunteers/list-leads")
        if response.status_code == 200:
            leads = response.json()
            lead_dict = {f"{v['vol_name']} (ID: {v['id']})": v['id'] for v in leads}
        else:
            lead_dict = {}
            st.error("Failed to fetch lead volunteers from server.")
    except Exception as e:
        lead_dict = {}
        st.error(f"Error fetching lead volunteers: {e}")

    if not lead_dict:
        st.warning("No lead volunteers found. Mark a volunteer as lead first.")
    else:
        selected_label = st.selectbox("Select Lead Volunteer", list(lead_dict.keys()), key="assign_lead_select")
        selected_volunteer_id = lead_dict.get(selected_label)

        try:
            inv_resp = requests.get(f"{API_URL}/books/unsold_inventory")
            if inv_resp.status_code == 200:
                unsold_inventory = inv_resp.json()
            else:
                unsold_inventory = {}
                st.error("Failed to fetch inventory.")
        except Exception as e:
            unsold_inventory = {}
            st.error(f"Error fetching inventory: {e}")

        if not unsold_inventory:
            st.warning("No unsold books available in inventory.")
        else:
            book_title = st.selectbox("Select Book Title", list(unsold_inventory.keys()), key="assign_title")
            available_units = unsold_inventory.get(book_title, 0)
            st.info(f"Available Copies in Inventory: **{available_units}**")
            units = st.number_input("Number of Copies to Assign", min_value=1, max_value=available_units, step=1, key="assign_units")

            if st.button("Assign Books", key="assign_books_btn"):
                if selected_volunteer_id is None:
                    st.error("Please select a lead volunteer.")
                else:
                    try:
                        payload = {"volunteer_id": selected_volunteer_id, "book_title": book_title, "units": units}
                        resp = requests.post(f"{API_URL}/books/assign-books", json=payload)
                        if resp.status_code == 200:
                            st.success(f"{units} copies of '{book_title}' assigned to volunteer ID {selected_volunteer_id}")
                            st.json(resp.json())
                        else:
                            try:
                                st.error(resp.json())
                            except:
                                st.error(f"Error: status {resp.status_code}")
                    except Exception as e:
                        st.error(f"Request failed: {e}")

# ----- ADD/CLOSE STALL -----
def stall_page():
    st.subheader("Add and Close a Stall")
    stall_location = st.text_input("Stall Location")
    stall_date = st.date_input("Stall Date", date.today())
    volunteer_ids = [int(v.strip()) for v in st.text_area("Volunteer IDs (comma separated)").split(",") if v.strip().isdigit()]
    volunteer_lead_id = st.number_input("Lead Volunteer ID", min_value=1, step=1)

    try:
        response = requests.get(f"{API_URL}/books/assigned_books", params={"volunteer_id": volunteer_lead_id})
        assigned_books = response.json() if response.status_code == 200 else {}
    except:
        assigned_books = {}

    st.write("---")
    st.subheader("Enter Sold Books")
    if not assigned_books:
        st.warning("No books assigned to this lead volunteer.")
    else:
        all_titles = list(sorted(set(assigned_books.values())))
        selected_title = st.selectbox("Choose Book Title", all_titles, key="title_dropdown")
        filtered_books = {bid: title for bid, title in assigned_books.items() if title == selected_title}

        if not filtered_books:
            selected_book_id = None
            selling_price = 0
            st.warning(f"No copies of '{selected_title}' are assigned to you.")
        else:
            selected_book_id = st.selectbox("Select Book ID", list(filtered_books.keys()), format_func=lambda x: f"{x} — {filtered_books[x]}", key="filtered_book_select")
            selling_price = st.number_input("Selling Price", min_value=0.0, step=1.0, key="selling_price")

        if "sold_books" not in st.session_state:
            st.session_state.sold_books = []

        if st.button("Add Book to Sold List"):
            if selected_book_id and selling_price > 0:
                st.session_state.sold_books.append({"book_id": selected_book_id, "book_selling_price": selling_price, "title": assigned_books[selected_book_id]})
            else:
                st.warning("Select a book and enter a valid selling price.")

        if st.session_state.sold_books:
            st.write("### Books Marked as Sold")
            st.table(st.session_state.sold_books)

    if st.button("Close Stall"):
        if not st.session_state.sold_books:
            st.warning("Add at least one sold book before closing the stall.")
        else:
            payload = {
                "stall_location": stall_location,
                "stall_date": stall_date.isoformat(),
                "volunteer_ids": volunteer_ids,
                "volunteer_lead_id": volunteer_lead_id,
                "sold_books": [{"book_id": x["book_id"], "book_selling_price": x["book_selling_price"]} for x in st.session_state.sold_books]
            }
            try:
                res = requests.post(f"{API_URL}/stalls/add-close-stall", json=payload)
                if res.status_code == 200:
                    st.success("Stall closed successfully!")
                    st.json(res.json())
                    st.session_state.sold_books = []
                else:
                    st.error(res.json())
            except Exception as e:
                st.error(f"Error submitting: {e}")

# ----- STALL PERFORMANCE -----
def stall_performance_page():
    st.subheader("View Stall Performance")
    try:
        monthly_resp = requests.get(f"{API_URL}/stalls/monthly-list")
        if monthly_resp.status_code != 200:
            st.error("Unable to fetch stall list")
            st.stop()
        monthly_data = monthly_resp.json()
    except Exception as e:
        st.error(f"Backend not reachable: {e}")
        st.stop()

    month_options = ["Select month"] + sorted(list(monthly_data.keys()))
    selected_month = st.selectbox("Select Month", month_options)

    if selected_month != "Select month":
        stall_options = monthly_data.get(selected_month, [])
        formatted_stalls = [f"{stall['stall_id']} — {stall['stall_location']} — {stall['stall_date']}" for stall in stall_options]
        selected_stall = st.selectbox("Select Stall", ["Select stall"] + formatted_stalls)

        if selected_stall != "Select stall":
            stall_id = int(selected_stall.split("—")[0].strip())
            if st.button("Get Performance", key="get_stall_perf"):
                try:
                    resp = requests.get(f"{API_URL}/stalls/stall-performance", params={"stall_id": stall_id})
                except Exception as e:
                    st.error(f"Failed to contact backend: {e}")
                    st.stop()

                if resp.status_code == 200:
                    data = resp.json()
                    stall_info = data.get("stall", {})
                    volunteers = stall_info.get("volunteers", [])
                    st.markdown("### Volunteers")
                    if volunteers:
                        st.write(", ".join(volunteers))
                    else:
                        st.write("No volunteers assigned.")

                    performance = data.get("performance", {})
                    st.markdown("### Stall")
                    st.write(f"**ID:** {stall_info.get('stall_id')}")
                    st.write(f"**Location:** {stall_info.get('stall_location')}")
                    st.write(f"**Date:** {stall_info.get('stall_date')}")

                    if performance:
                        rows = []
                        for row in performance:
                            rows.append({
                                "Title": row.get("Title"),
                                "Assigned": row.get("Assigned", 0),
                                "Sold": row.get("Sold", 0),
                                "Unsold": row.get("Unsold", 0),
                                "Remaining": row.get("Remaining", 0),
                                "Revenue": row.get("Revenue", 0)
                            })

                        st.markdown("### Performance by Title")
                        st.table(rows)
                        total_assigned = sum(r.get("Assigned", 0) for r in rows)
                        total_sold = sum(r.get("Sold", 0) for r in rows)
                        total_revenue = sum(r.get("Revenue", 0) for r in rows)
                        st.metric("Total Assigned", total_assigned)
                        st.metric("Total Sold", total_sold)
                        st.metric("Total Revenue", total_revenue)
                    else:
                        st.info("No performance data for this stall.")
                else:
                    try:
                        st.error(resp.json())
                    except:
                        st.error(resp.text)

# ----- INVENTORY SUMMARY -----
def inventory_summary_page():
    st.subheader("Inventory Summary")
    try:
        response = requests.get(f"{API_URL}/reports/inventory_summary")
        if response.status_code == 200:
            inv = response.json()
            table_data = []
            for title, counts in inv.items():
                table_data.append({
                    "Title": title,
                    "Unsold": counts.get("Unsold", 0),
                    "Assigned": counts.get("Assigned", 0),
                    "Sold": counts.get("Sold", 0)
                })
            st.table(table_data)
        else:
            st.error(f"Error: {response.json()}")
    except Exception as e:
        st.error(f"Failed to fetch inventory summary: {e}")

# ----- ADMIN MONTHLY DASHBOARD -----
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
                    st.metric("Total Stalls", data.get("total_stalls", 0))
                    st.metric("Total Books Sold", data.get("total_books_sold", 0))
                    st.metric("Total Monthly Revenue", data.get("monthly_revenue", 0))
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
elif page == "Add/Close Stall":
    stall_page()
elif page == "Stall Performance":
    stall_performance_page()
elif page == "Inventory Summary":
    inventory_summary_page()
elif page == "Admin Monthly Dashboard":
    admin_monthly_dashboard_page()
