# Updated AK Finance Loan Management App with Encrypted Login, Registration, and Logout

import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from utils.drive_sync import download_from_drive, upload_to_drive
from hashlib import sha256

st.set_page_config(page_title="AK Finance Loan Management App")

# Paths
user_file = "data/users.csv"
excel_file = "data/customer_loans.xlsx"
os.makedirs("data", exist_ok=True)
download_from_drive(excel_file)

# Initialize users file if not exist
if not os.path.exists(user_file):
    hashed = sha256("admin123".encode()).hexdigest()
    user_df = pd.DataFrame([["admin", hashed, "admin"]], columns=["username", "password", "role"])
    user_df.to_csv(user_file, index=False)

# Load and save users
def load_users():
    return pd.read_csv(user_file)

def save_users(users):
    users.to_csv(user_file, index=False)

# Hash passwords
def hash_password(password):
    return sha256(password.encode()).hexdigest()

# Load and save loan data
def load_data():
    return pd.read_excel(excel_file)

def save_data(df):
    df.to_excel(excel_file, index=False)
    upload_to_drive(excel_file)

def calculate_profit(df):
    df['Profit'] = df['Total Due'] - df['Loan Amount']
    save_data(df)

# --- Authentication ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

if not st.session_state.logged_in:
    st.title("AK Finance Login/Registration")
    auth_choice = st.radio("Choose Action", ["Login", "Register"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    users = load_users()

    if auth_choice == "Login":
        if st.button("Login"):
            hashed_pw = hash_password(password)
            match = users[(users["username"] == username) & (users["password"] == hashed_pw)]
            if not match.empty:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = match.iloc[0]["role"]
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid username or password")
    else:
        if st.button("Register"):
            if username in users["username"].values:
                st.warning("Username already exists")
            else:
                hashed_pw = hash_password(password)
                new_user = pd.DataFrame([[username, hashed_pw, "customer"]], columns=["username", "password", "role"])
                users = pd.concat([users, new_user], ignore_index=True)
                save_users(users)
                st.success("Registration successful! Please log in.")
    st.stop()

# Add logout button
with st.sidebar:
    st.sidebar.title(f"Welcome {st.session_state.username.title()} ({st.session_state.role})")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.rerun()

# Load loan data and calculate
df = load_data()
calculate_profit(df)

menu = ["Dashboard", "View Loans", "Customer History"]
if st.session_state.role == "admin":
    menu += ["Add New Loan", "Record Payment", "Edit Loan"]
choice = st.sidebar.selectbox("Menu", menu)

# Due Date Reminder
today = pd.Timestamp.today()
if st.session_state.role == "customer":
    user_df = df[(df['Customer Name'].str.lower() == st.session_state.username.lower()) & (df['Status'] == 'Active')]
    upcoming = user_df[pd.to_datetime(user_df['Due Date']) <= today + timedelta(days=5)]
    if not upcoming.empty:
        st.warning("🔔 Reminder: You have a due date approaching in the next 5 days!")

# Dashboard
if choice == "Dashboard":
    if st.session_state.role == "admin":
        st.subheader("Search Customer")
        search_name = st.text_input("Enter Customer Name")
        if search_name:
            result = df[df['Customer Name'].str.contains(search_name, case=False, na=False)]
            st.dataframe(result)

        st.subheader("Loans Due in the Next 7 Days")
        upcoming = df[(df['Status'] == 'Active') & (pd.to_datetime(df['Due Date']) <= today + pd.Timedelta(days=7))]
        st.dataframe(upcoming)
    else:
        st.subheader("Your Dashboard")
        customer_df = df[df['Customer Name'].str.lower() == st.session_state.username.lower()]
        st.dataframe(customer_df)
        st.subheader("Loans Due in the Next 7 Days")
        upcoming = customer_df[
            (customer_df['Status'] == 'Active') & 
            (pd.to_datetime(customer_df['Due Date']) <= today + pd.Timedelta(days=7))
        ]
        if not upcoming.empty:
            for _, row in upcoming.iterrows():
                due_date = pd.to_datetime(row['Due Date'])
                days_left = (due_date - today).days
                urgency = "⚠️" if days_left <= 2 else "🔔"
                color = "red" if days_left <= 2 else "orange"
                st.markdown(f"<div style='background-color:{color};padding:10px;border-radius:5px;color:white;'>"
                            f"<b>{urgency} {row['Customer Name']}</b><br/>"
                            f"Loan of ₹{row['Remaining Due']} is due in {days_left} day(s) on {row['Due Date']}"
                            f"</div>", unsafe_allow_html=True)
        st.dataframe(upcoming)

# View Loans
elif choice == "View Loans":
    st.subheader("All Loans")
    if st.session_state.role == "admin":
        filtered_df = df
        search_name = st.text_input("Search by Customer Name")
        if search_name:
            filtered_df = df[df['Customer Name'].str.contains(search_name, case=False, na=False)]
    else:
        filtered_df = df[df['Customer Name'].str.lower() == st.session_state.username.lower()]
    st.dataframe(filtered_df)

# Add New Loan
elif choice == "Add New Loan":
    st.subheader("Add New Loan Entry")
    name = st.text_input("Customer Name")
    phone = st.text_input("Phone Number")
    loan_amount = st.number_input("Loan Amount", min_value=0.0)
    interest_rate = st.number_input("Interest Rate (%)", min_value=0.0)
    due_date = st.date_input("Due Date")

    if st.button("Add Loan"):
        total_due = loan_amount + (loan_amount * interest_rate / 100)
        new_data = pd.DataFrame([[name, phone, loan_amount, interest_rate, total_due, 0, total_due, due_date, 'Active', 0, '']], columns=df.columns)
        df = pd.concat([df, new_data], ignore_index=True)
        save_data(df)
        st.success("New loan added!")

# Record Payment
elif choice == "Record Payment":
    st.subheader("Record Payment")
    active_loans = df[df['Status'] == 'Active']
    customers = active_loans['Customer Name'].unique().tolist()
    selected_customer = st.selectbox("Select Customer", customers)
    customer_loans = active_loans[active_loans['Customer Name'] == selected_customer]
    loan_options = [f"Due: {row['Due Date']}, Amount: {row['Loan Amount']}" for _, row in customer_loans.iterrows()]
    selected_option = st.selectbox("Select Loan", loan_options)
    loan_idx = customer_loans.index[loan_options.index(selected_option)]

    payment = st.number_input("Payment Amount", min_value=0.0)
    if st.button("Record Payment"):
        df.at[loan_idx, 'Paid Amount'] += payment
        df.at[loan_idx, 'Remaining Due'] = df.at[loan_idx, 'Total Due'] - df.at[loan_idx, 'Paid Amount']
        if df.at[loan_idx, 'Remaining Due'] <= 0:
            df.at[loan_idx, 'Status'] = 'Cleared'
            df.at[loan_idx, 'Cleared Date'] = datetime.today().strftime('%Y-%m-%d')
        save_data(df)
        st.success(f"Payment of {payment} recorded for {selected_customer}")

# Edit Loan
elif choice == "Edit Loan":
    st.subheader("Edit Loan")
    active_loans = df[df['Status'] == 'Active']
    customers = active_loans['Customer Name'].unique().tolist()
    selected_customer = st.selectbox("Select Customer", customers)
    customer_loans = active_loans[active_loans['Customer Name'] == selected_customer]
    loan_options = [f"Due: {row['Due Date']}, Amount: {row['Loan Amount']}" for _, row in customer_loans.iterrows()]
    selected_option = st.selectbox("Select Loan to Edit", loan_options)
    loan_idx = customer_loans.index[loan_options.index(selected_option)]

    name = st.text_input("Customer Name", df.at[loan_idx, 'Customer Name'])
    phone = st.text_input("Phone Number", df.at[loan_idx, 'Phone'])
    loan_amount = st.number_input("Loan Amount", value=df.at[loan_idx, 'Loan Amount'])
    interest_rate = st.number_input("Interest Rate (%)", value=df.at[loan_idx, 'Interest Rate'])
    due_date = st.date_input("Due Date", pd.to_datetime(df.at[loan_idx, 'Due Date']))

    if st.button("Update Loan"):
        total_due = loan_amount + (loan_amount * interest_rate / 100)
        df.at[loan_idx, 'Customer Name'] = name
        df.at[loan_idx, 'Phone'] = phone
        df.at[loan_idx, 'Loan Amount'] = loan_amount
        df.at[loan_idx, 'Interest Rate'] = interest_rate
        df.at[loan_idx, 'Total Due'] = total_due
        df.at[loan_idx, 'Remaining Due'] = total_due - df.at[loan_idx, 'Paid Amount']
        df.at[loan_idx, 'Due Date'] = due_date
        save_data(df)
        st.success("Loan updated successfully!")

# Customer History
elif choice == "Customer History":
    st.subheader("Customer Loan History")
    if st.session_state.role == "admin":
        customers = df['Customer Name'].unique().tolist()
        selected_customer = st.selectbox("Select Customer", customers)
        history = df[df['Customer Name'] == selected_customer]
    else:
        history = df[df['Customer Name'].str.lower() == st.session_state.username.lower()]
    st.dataframe(history)
