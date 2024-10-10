import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import os

# Set page layout to wide
st.set_page_config(layout="wide")

# Function to create a new database connection
def create_connection():
    return sqlite3.connect('skool_data.db')

# Function to execute SQL queries (with caching)
@st.cache_data
def execute_query(query, params=()):
    conn = create_connection()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

# Function to get unique topics (cached for performance)
@st.cache_data
def get_topics():
    query = 'SELECT DISTINCT topic FROM skool_data'
    return execute_query(query)['topic'].tolist()

# Function to filter data
def filter_data(topics, search_term, price_filter):
    query = '''
    SELECT topic, community_mame, link, all_skool_ranking, free, theme_rank, visibility, members, price, description
    FROM skool_data WHERE 1=1
    '''
    params = []
    if topics:
        query += ' AND topic IN ({})'.format(','.join(['?']*len(topics)))
        params.extend(topics)
    if search_term:
        query += ' AND description LIKE ?'
        params.append(f'%{search_term}%')
    if price_filter:
        if 'Free' in price_filter and 'Paid' not in price_filter:
            query += ' AND free = 1'
        elif 'Paid' in price_filter and 'Free' not in price_filter:
            query += ' AND free = 0'
    return execute_query(query, params)

st.title('Skool Data Analysis Dashboard')

# Check if the database file exists
if not os.path.exists('skool_data.db'):
    st.error("Database file 'skool_data.db' not found. Please ensure it's in the same directory as this script.")
    st.stop()

# Sidebar filters
st.sidebar.header('Filters')
selected_topics = st.sidebar.multiselect('Select Topic', get_topics())
search_term = st.sidebar.text_input('Search in Description')
price_filter = st.sidebar.multiselect('Price Type', ['Free', 'Paid'])

# Filter data
df_filtered = filter_data(selected_topics, search_term, price_filter)

# Pagination variables
rows_per_page = 20
total_rows = len(df_filtered)

# Add a session state for pagination
if 'page_number' not in st.session_state:
    st.session_state.page_number = 1

# Pagination buttons
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if st.button("Previous"):
        if st.session_state.page_number > 1:
            st.session_state.page_number -= 1

with col3:
    if st.button("Next"):
        if st.session_state.page_number < (total_rows // rows_per_page) + 1:
            st.session_state.page_number += 1

# Display current page number
st.write(f"Page {st.session_state.page_number} of {(total_rows // rows_per_page) + 1}")

# Paginate the data
start_row = (st.session_state.page_number - 1) * rows_per_page
df_paginated = df_filtered.iloc[start_row:start_row + rows_per_page]

# Create a new column with clickable links in markdown format
df_paginated['Topic Link'] = df_paginated.apply(lambda row: f'<a href="{row["link"]}" target="_blank">{row["community_mame"]}</a>', axis=1)

# Rename columns
df_paginated = df_paginated.rename(columns={
    'topic': 'Topic',
    'Topic Link': 'Community Name',
    'all_skool_ranking': 'Skool Rank',
    'theme_rank': 'Topic Rank',  # Correct this column name
    'visibility': 'Visibility',
    'members': 'Members',
    'price': 'Price',
    'description': 'Description'
})

# Reorder columns
df_paginated = df_paginated[['Topic Link', 'Topic', 'Skool Rank', 'Topic Rank', 'Visibility', 'Members', 'Price', 'Description']]

# Display filtered data with all columns, including clickable links
st.subheader('Filtered Data')

# Use st.markdown with unsafe_allow_html for rendering HTML links
st.markdown(df_paginated.to_html(escape=False, index=False), unsafe_allow_html=True)

# Analytics
st.subheader('Analytics')

# Count items per topic
topic_counts = df_filtered['topic'].value_counts()
st.write("Items per Topic:")
st.write(topic_counts)

# Price and Member statistics
col1, col2 = st.columns(2)
with col1:
    st.write("Price Statistics:")
    numeric_prices = pd.to_numeric(df_filtered['price'].replace('Paid', pd.NA), errors='coerce')
    st.write(f"Max Price: ${numeric_prices.max():.2f}")
    st.write(f"Min Price: ${numeric_prices.min():.2f}")
    st.write(f"Mean Price: ${numeric_prices.mean():.2f}")
    st.write(f"Median Price: ${numeric_prices.median():.2f}")
    st.write(f"Paid Courses: {df_filtered['price'].eq('Paid').sum()}")

with col2:
    st.write("Member Statistics:")
    st.write(f"Max Members: {df_filtered['members'].max():,.0f}")
    st.write(f"Min Members: {df_filtered['members'].min():,.0f}")
    st.write(f"Mean Members: {df_filtered['members'].mean():,.0f}")
    st.write(f"Median Members: {df_filtered['members'].median():,.0f}")

# Visualizations
st.subheader('Visualizations')

# Mean Members by Topic
member_stats = df_filtered.groupby('topic')['members'].mean().sort_values(ascending=True).reset_index()
fig = px.bar(member_stats, x='members', y='topic', orientation='h',
             title='Mean Members by Topic', labels={'members': 'Mean Members', 'topic': 'Topic'})
fig.update_layout(yaxis={'categoryorder':'total ascending'})
st.plotly_chart(fig)

# Member Distribution by Topic
fig = px.box(df_filtered, x='topic', y='members', title='Member Distribution by Topic')
st.plotly_chart(fig)

# Scatter plot of price vs members (excluding "Paid" courses)
df_numeric = df_filtered[pd.to_numeric(df_filtered['price'], errors='coerce').notnull()]
df_numeric['price'] = pd.to_numeric(df_numeric['price'])
fig = px.scatter(df_numeric, x='price', y='members', color='topic',
                 title='Price vs Members (Excluding "Paid" Courses)',
                 labels={'price': 'Price', 'members': 'Number of Members', 'topic': 'Topic'})
st.plotly_chart(fig)

# Pie chart of free vs paid courses
free_paid_counts = df_filtered['free'].map({1: 'Free', 0: 'Paid'}).value_counts()

# Print free_paid_counts to check the data
st.write(free_paid_counts)

# Only proceed if there is data to plot
if not free_paid_counts.empty:
    fig = px.pie(values=free_paid_counts.values, names=free_paid_counts.index, title='Free vs Paid Courses')
    st.plotly_chart(fig)
else:
    st.write("No data available for Free vs Paid courses")
