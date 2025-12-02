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
    "Add Book",
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

# ----- ADD BOOK -----
elif choice == "Add Book":
    st.subheader("Add New Book")
    title = st.text_input("Book Title")
    units = st.number_input("Number of Copies", min_value=1, step=1)
    mrp = st.number_input("MRP", min_value=0.0, step=1.0)

    if st.button("Add Book"):
        try:
            data = {"title": title, "units": units, "MRP": mrp}
            response = requests.post(f"{API_URL}/books/add-book", json=data)
            if response.status_code == 200:
                st.success(f"{units} copies of '{title}' added!")
                st.json(response.json())
            else:
                st.error(f"Error: {response.json()}")
        except Exception as e:
            st.error(f"Request failed: {e}")

# ----- ASSIGN BOOKS -----
elif choice == "Assign Books":
    st.subheader("Assign Books to Lead Volunteer")
    volunteer_id = st.number_input("Lead Volunteer ID", min_value=1, step=1)
    book_title = st.text_input("Book Title")
    units = st.number_input("Number of Copies", min_value=1, step=1)

    if st.button("Assign Books"):
        try:
            data = {"volunteer_id": volunteer_id, "book_title": book_title, "units": units}
            response = requests.post(f"{API_URL}/books/assign-books", json=data)
            if response.status_code == 200:
                st.success(f"{units} copies of '{book_title}' assigned to volunteer {volunteer_id}")
                st.json(response.json())
            else:
                st.error(f"Error: {response.json()}")
        except Exception as e:
            st.error(f"Request failed: {e}")

# ------------------ Add/Close Stall ------------------
elif choice == "Add/Close Stall":
    st.subheader("Add and Close a Stall")
    stall_location = st.text_input("Stall Location")
    stall_date = st.date_input("Stall Date", date.today())
    volunteer_ids = st.text_area("Volunteer IDs (comma separated)").split(",")
    volunteer_ids = [int(v.strip()) for v in volunteer_ids if v.strip().isdigit()]
    volunteer_lead_id = st.number_input("Lead Volunteer ID", min_value=1, step=1)

    st.write("Enter Sold Books (Book ID : Selling Price) comma separated, e.g. 1:250,2:300")
    sold_books_input = st.text_area("Sold Books")
    sold_books = []
    for item in sold_books_input.split(","):
        if ":" in item:
            bid, price = item.split(":")
            if bid.strip().isdigit() and price.strip().replace(".", "").isdigit():
                sold_books.append({"book_id": int(bid.strip()), "book_selling_price": float(price.strip())})

    if st.button("Add and Close Stall"):
        payload = {
            "stall_location": stall_location,
            "stall_date": stall_date.isoformat(),
            "volunteer_ids": volunteer_ids,
            "volunteer_lead_id": volunteer_lead_id,
            "sold_books": sold_books
        }
        response = requests.post(f"{API_URL}/stalls/add-close-stall", json=payload)
        if response.status_code == 200:
            st.success("Stall added and closed successfully!")
            st.json(response.json())
        else:
            st.error(response.json())

# ----- STALL PERFORMANCE -----
elif choice == "Stall Performance":
    st.subheader("View Stall Performance")
    stall_id = st.number_input("Stall ID", min_value=1, step=1)

    if st.button("Get Performance"):
        try:
            response = requests.get(f"{API_URL}/stalls/stall-performance", params={"stall_id": stall_id})
            if response.status_code == 200:
                st.json(response.json())
            else:
                st.error(f"Error: {response.json()}")
        except Exception as e:
            st.error(f"Request failed: {e}")

# ----- INVENTORY SUMMARY -----
elif choice == "Inventory Summary":
    st.subheader("Inventory Summary")
    try:
        response = requests.get(f"{API_URL}/reports/inventory_summary")
        if response.status_code == 200:
            st.json(response.json())
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
