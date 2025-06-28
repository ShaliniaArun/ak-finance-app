import streamlit as st
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt

st.set_page_config(page_title="AK Finance Loan Management App")

excel_file = 'customer_loans.xlsx'
if not os.path.exists(excel_file):
    df = pd.DataFrame(columns=['Customer Name', 'Phone', 'Loan Amount', 'Interest Rate', 'Total Due', 'Paid Amount', 'Remaining Due', 'Due Date', 'Status', 'Profit', 'Cleared Date'])
    df.to_excel(excel_file, index=False)

def load_data():
    return pd.read_excel(excel_file)

def save_data(df):
    df.to_excel(excel_file, index=False)

def calculate_profit(df):
    df['Profit'] = df['Total Due'] - df['Loan Amount']
    save_data(df)

st.title("AK Finance Loan Management App")

df = load_data()
calculate_profit(df)

menu = ["Dashboard", "View Loans", "Add New Loan", "Record Payment", "Edit Loan", "Customer History"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Dashboard":
    st.subheader("Dashboard")
    profit_data = df[df['Status'] == 'Cleared']
    profit_data['Cleared Date'] = pd.to_datetime(profit_data['Cleared Date'], errors='coerce')
    profit_data = profit_data.dropna(subset=['Cleared Date'])

    this_week = profit_data[profit_data['Cleared Date'] >= pd.Timestamp.now() - pd.Timedelta(weeks=1)]['Profit'].sum()
    this_month = profit_data[profit_data['Cleared Date'] >= pd.Timestamp.now() - pd.DateOffset(months=1)]['Profit'].sum()
    this_year = profit_data[profit_data['Cleared Date'] >= pd.Timestamp.now() - pd.DateOffset(years=1)]['Profit'].sum()

    st.metric("Profit This Week", f"₹{this_week}")
    st.metric("Profit This Month", f"₹{this_month}")
    st.metric("Profit This Year", f"₹{this_year}")

    st.write("### Profit Trend")
    monthly = profit_data.groupby(profit_data['Cleared Date'].dt.to_period('M')).sum(numeric_only=True)
    if not monthly.empty:
        fig, ax = plt.subplots()
        ax.plot(monthly.index.astype(str), monthly['Profit'], marker='o')
        plt.xticks(rotation=45)
        st.pyplot(fig)

    st.write("### Loans Due in Next 7 Days")
    today = pd.Timestamp.today()
    upcoming = df[(df['Status'] == 'Active') & (pd.to_datetime(df['Due Date']) <= today + pd.Timedelta(days=7))]
    st.dataframe(upcoming)

elif choice == "View Loans":
    st.subheader("All Loans")
    search_name = st.text_input("Search by Customer Name")
    filtered_df = df[df['Customer Name'].str.contains(search_name, case=False, na=False)] if search_name else df
    st.dataframe(filtered_df)

    if st.button("Export Data to CSV"):
        filtered_df.to_csv('exported_loans.csv', index=False)
        st.success("Data exported to exported_loans.csv")

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

elif choice == "Record Payment":
    st.subheader("Record Payment")
    active_loans = df[df['Status'] == 'Active']
    customers = active_loans['Customer Name'].unique().tolist()
    selected_customer = st.selectbox("Select Customer", customers)

    customer_loans = active_loans[active_loans['Customer Name'] == selected_customer]
    loan_options = [f"Due: {row['Due Date']}, Amount: {row['Loan Amount']}" for idx, row in customer_loans.iterrows()]
    selected_option = st.selectbox("Select Loan", loan_options)
    selected_index = loan_options.index(selected_option)
    loan_idx = customer_loans.index[selected_index]

    payment = st.number_input("Payment Amount", min_value=0.0)

    if st.button("Record Payment"):
        df.at[loan_idx, 'Paid Amount'] += payment
        df.at[loan_idx, 'Remaining Due'] = df.at[loan_idx, 'Total Due'] - df.at[loan_idx, 'Paid Amount']
        if df.at[loan_idx, 'Remaining Due'] <= 0:
            df.at[loan_idx, 'Status'] = 'Cleared'
            df.at[loan_idx, 'Cleared Date'] = datetime.today().strftime('%Y-%m-%d')
        save_data(df)
        st.success(f"Payment of {payment} recorded for {selected_customer}")

elif choice == "Edit Loan":
    st.subheader("Edit Loan")
    active_loans = df[df['Status'] == 'Active']
    customers = active_loans['Customer Name'].unique().tolist()
    selected_customer = st.selectbox("Select Customer", customers)

    customer_loans = active_loans[active_loans['Customer Name'] == selected_customer]
    loan_options = [f"Due: {row['Due Date']}, Amount: {row['Loan Amount']}" for idx, row in customer_loans.iterrows()]
    selected_option = st.selectbox("Select Loan to Edit", loan_options)
    selected_index = loan_options.index(selected_option)
    loan_idx = customer_loans.index[selected_index]

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

elif choice == "Customer History":
    st.subheader("Customer Loan History")
    customers = df['Customer Name'].unique().tolist()
    selected_customer = st.selectbox("Select Customer", customers)

    history = df[df['Customer Name'] == selected_customer]
    st.write(f"### Loan History for {selected_customer}")
    st.dataframe(history)
