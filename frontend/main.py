import streamlit as st
import requests
from datetime import date

# ----- CONFIG -----
API_URL = "http://127.0.0.1:8000"  # Your FastAPI URL

# ----- APP TITLE -----
st.title("Volunteer Book Stall Management")

# ----- MENU -----
menu = [
    "Home",
    "Add Volunteer",
    "Make Volunteer Lead",
    "Add New Book Title",
    "Add Books To Inventory",
    "Assign Books",
    "Add/Close Stall",
    "Stall Performance",
    "Inventory Summary",
    "Admin Monthly Dashboard"
]
choice = st.sidebar.selectbox("Menu", menu)

# ----- HOME -----
if choice == "Home":
    st.subheader("Welcome to the Volunteer App Dashboard")
    st.write("Use the menu on the left to navigate through the app.")

# ----- ADD VOLUNTEER -----
elif choice == "Add Volunteer":
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
elif choice == "Make Volunteer Lead":
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

elif choice == "Add New Book Title":
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



elif choice == "Add Books To Inventory":
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

    # 1️⃣ Select Title
    title = st.selectbox("Select Book Title", titles)

    # 2️⃣ Fetch existing batches for selected title
    try:
        resp = requests.get(f"{API_URL}/books/list-batches", params={"title": title})
        batches = resp.json() if resp.status_code == 200 else []
    except:
        batches = []

    batch_options = ["New Batch"] + [
        f"Batch {b['id']} | MRP: {b['MRP']} | Date: {b['entrydate']}"
        for b in batches
    ]

    selected_batch = st.selectbox("Select Batch", batch_options)

    # Parse batch selection
    if selected_batch == "New Batch":
        batch_id = None
        mrp = st.number_input("MRP (for new batch)", min_value=1.0, step=1.0)
        entrydate = st.date_input("Entry Date", date.today())
    else:
        # Extract batch_id
        batch_id = int(selected_batch.split()[1])

        # Get batch details
        batch_data = next(b for b in batches if b["id"] == batch_id)

        mrp = batch_data["MRP"]

        # Auto-lock entrydate to backend value
        entrydate = st.date_input(
            "Entry Date (auto-filled for existing batch)",
            date.fromisoformat(batch_data["entrydate"]),
            disabled=True
        )

    # Units
    units = st.number_input("Number of Copies", min_value=1, step=1)

    # Submit
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
elif choice == "Assign Books":
    st.subheader("Assign Books to Lead Volunteer")

    # Fetch lead volunteers from backend
    try:
        response = requests.get(f"{API_URL}/volunteers/list-leads")
        if response.status_code == 200:
            leads = response.json()  # List of dicts [{id, vol_name}, ...]
            # map display label -> id
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
        # selectbox shows labels, we then look up numeric id
        selected_label = st.selectbox(
            "Select Lead Volunteer",
            list(lead_dict.keys()),
            key="assign_lead_select"
        )
        selected_volunteer_id = lead_dict.get(selected_label)

        # ----------------------------------------------
        # FETCH UNSOLD BOOK INVENTORY
        # ----------------------------------------------
        try:
            inv_resp = requests.get(f"{API_URL}/books/unsold_inventory")
            if inv_resp.status_code == 200:
                unsold_inventory = inv_resp.json()   # { "Truth": 12, "Karma": 4, ... }
            else:
                unsold_inventory = {}
                st.error("Failed to fetch inventory.")
        except Exception as e:
            unsold_inventory = {}
            st.error(f"Error fetching inventory: {e}")

        if not unsold_inventory:
            st.warning("No unsold books available in inventory.")
        else:
            # ----------------------------------------------
            # TITLE DROPDOWN
            # ----------------------------------------------
            book_title = st.selectbox(
                "Select Book Title",
                list(unsold_inventory.keys()),
                key="assign_title"
            )

            # Show available stock for that title
            available_units = unsold_inventory.get(book_title, 0)
            st.info(f"Available Copies in Inventory: **{available_units}**")

            # ----------------------------------------------
            # UNITS INPUT (LIMITED BY AVAILABLE UNITS)
            # ----------------------------------------------
            units = st.number_input(
                "Number of Copies to Assign",
                min_value=1,
                max_value=available_units,
                step=1,
                key="assign_units"
            )

            # ----------------------------------------------
            # SUBMIT ASSIGNMENT
            # ----------------------------------------------
            if st.button("Assign Books", key="assign_books_btn"):
                if selected_volunteer_id is None:
                    st.error("Please select a lead volunteer.")
                else:
                    try:
                        payload = {
                            "volunteer_id": selected_volunteer_id,   # <-- numeric ID
                            "book_title": book_title,
                            "units": units
                        }
                        resp = requests.post(f"{API_URL}/books/assign-books", json=payload)

                        if resp.status_code == 200:
                            st.success(f"{units} copies of '{book_title}' assigned to volunteer ID {selected_volunteer_id}")
                            st.json(resp.json())
                        else:
                            # backend returns JSON detail; show it
                            try:
                                st.error(resp.json())
                            except:
                                st.error(f"Error: status {resp.status_code}")
                    except Exception as e:
                        st.error(f"Request failed: {e}")



# ----- Add/Close Stall -----
elif choice == "Add/Close Stall":
    st.subheader("Add and Close a Stall")
    stall_location = st.text_input("Stall Location")
    stall_date = st.date_input("Stall Date", date.today())


    volunteer_ids = st.text_area("Volunteer IDs (comma separated)").split(",")
    volunteer_ids = [int(v.strip()) for v in volunteer_ids if v.strip().isdigit()]
    volunteer_lead_id = st.number_input("Lead Volunteer ID", min_value=1, step=1)

    # Fetch assigned books
    try:
        response = requests.get(
            f"{API_URL}/books/assigned_books",
            params={"volunteer_id": volunteer_lead_id}
        )
        if response.status_code == 200:
            assigned_books = response.json()  # dict {id: title}
        else:
            assigned_books = {}
            st.warning("No assigned books found.")
    except Exception as e:
        assigned_books = {}
        st.error(f"Error fetching books: {e}")

    st.write("---")

    # -------------------------
    # FILTER BY TITLE
    # -------------------------
    st.subheader("Enter Sold Books")

    # -------------------------
    # GET ASSIGNED BOOKS
    # -------------------------
    try:
        response = requests.get(
            f"{API_URL}/books/assigned_books",
            params={"volunteer_id": volunteer_lead_id}
        )
        assigned_books = response.json() if response.status_code == 200 else {}
    except:
        assigned_books = {}

    # assigned_books = {book_id: title}  <-- your backend structure

    if not assigned_books:
        st.warning("No books assigned to this lead volunteer.")
    else:
        # -------------------------
        # UNIQUE TITLES FOR DROPDOWN
        # -------------------------
        all_titles = list(sorted(set(assigned_books.values())))

        selected_title = st.selectbox(
            "Choose Book Title",
            all_titles,
            key="title_dropdown"
        )

        # -------------------------
        # FILTER BOOKS BY SELECTED TITLE
        # -------------------------
        filtered_books = {
            bid: title for bid, title in assigned_books.items()
            if title == selected_title
        }

        if not filtered_books:
            st.warning(f"No copies of '{selected_title}' are assigned to you.")
            selected_book_id = None
            selling_price = 0
        else:
            # -------------------------
            # BOOK ID DROPDOWN (only IDs of that title)
            # -------------------------
            selected_book_id = st.selectbox(
                "Select Book ID",
                list(filtered_books.keys()),
                format_func=lambda x: f"{x} — {filtered_books[x]}",
                key="filtered_book_select"
            )

            selling_price = st.number_input(
                "Selling Price",
                min_value=0.0,
                step=1.0,
                key="selling_price"
            )

        # -------------------------
        # SESSION STATE FOR SOLD BOOKS
        # -------------------------
        if "sold_books" not in st.session_state:
            st.session_state.sold_books = []

        if st.button("Add Book to Sold List"):
            if selected_book_id and selling_price > 0:
                st.session_state.sold_books.append({
                    "book_id": selected_book_id,
                    "book_selling_price": selling_price,
                    "title": assigned_books[selected_book_id]
                })
            else:
                st.warning("Select a book and enter a valid selling price.")

        # -------------------------
        # DISPLAY LIST OF SOLD BOOKS
        # -------------------------
        if st.session_state.sold_books:
            st.write("### Books Marked as Sold")
            st.table(st.session_state.sold_books)

    # -------------------------
    # Submit & Close Stall
    # -------------------------
    if st.button("Close Stall"):
        if not st.session_state.sold_books:
            st.warning("Add at least one sold book before closing the stall.")
        else:
            payload = {
                "stall_location": stall_location,
                "stall_date": stall_date.isoformat(),
                "volunteer_ids": volunteer_ids,
                "volunteer_lead_id": volunteer_lead_id,
                "sold_books": [
                    {"book_id": x["book_id"], "book_selling_price": x["book_selling_price"]}
                    for x in st.session_state.sold_books
                ]
            }
            try:
                res = requests.post(f"{API_URL}/stalls/add-close-stall", json=payload)
                if res.status_code == 200:
                    st.success("Stall closed successfully!")
                    st.json(res.json())
                    st.session_state.sold_books = []  # reset
                else:
                    st.error(res.json())
            except Exception as e:
                st.error(f"Error submitting: {e}")


# ----- INVENTORY SUMMARY -----
elif choice == "Inventory Summary":
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
elif choice == "Admin Monthly Dashboard":
    st.subheader("Admin Monthly Dashboard")

    # Default to current month
    today = date.today()
    default_month = today.strftime("%Y-%m")
    selected_month = st.text_input("Enter Month (YYYY-MM)", default_month)

    # Validate month format
    try:
        year, mon = map(int, selected_month.split("-"))
        if not (1 <= mon <= 12):
            raise ValueError
    except ValueError:
        st.warning("Please enter month in correct format: YYYY-MM (e.g., 2025-12)")
    else:
        if st.button("Get Monthly Report"):
            try:
                response = requests.get(
                    f"{API_URL}/reports/admin-monthly-performance",
                    params={"month": selected_month}
                )
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"Report for {selected_month}")

                    # Basic stats
                    st.metric("Total Stalls", data.get("total_stalls", 0))
                    st.metric("Total Books Sold", data.get("total_books_sold", 0))
                    st.metric("Total Monthly Revenue", data.get("monthly_revenue", 0))

                    # Books sold category chart
                    st.subheader("#Stalls by number of books sold")
                    sold_cat = data.get("stall_bookssoldcat", {})
                    st.bar_chart(sold_cat)

                    # Revenue category chart
                    st.subheader("#Stalls by monthly revenue")
                    rev_cat = data.get("stall_revcat", {})
                    st.bar_chart(rev_cat)

                    # Volunteer attendance chart
                    st.subheader("#Volunteers by number of stalls attended")
                    vol_att = data.get("vol_attendance", {})
                    st.bar_chart(vol_att)

                elif response.status_code == 404:
                    st.info(f"No stalls found for {selected_month}")
                else:
                    st.error(f"Error fetching report: {response.json()}")
            except Exception as e:
                st.error(f"Request failed: {e}")
