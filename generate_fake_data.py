import pandas as pd
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# --- Configuration ---
NUM_LEADERS = 5
NUM_OFFLINE_PER_LEADER = 10
NUM_ADMINS = 1
PERFORMANCE_MONTHS = 6 # Generate data for the last 6 months

# --- Generate Users ---
users_data = []
leaders = []

# Admins
for i in range(NUM_ADMINS):
    username = f"admin_{i+1}"
    password = "password" # Use a simple default password for fake data
    users_data.append({
        'username': username,
        'password': password,
        'role': 'admin',
        'leader_username': '', # Admins don't have leaders
        'can_view_funds': 'Yes' # Admins can view funds
    })

# Leaders
for i in range(NUM_LEADERS):
    username = f"leader_{i+1}"
    password = "password"
    can_view_funds = 'Yes' if i % 2 == 0 else 'No' # Alternate which leaders can view funds
    users_data.append({
        'username': username,
        'password': password,
        'role': 'leader',
        'leader_username': '', # Leaders don't have leaders
        'can_view_funds': can_view_funds
    })
    leaders.append(username)

# Offline Users
offline_user_counter = 1
for leader_username in leaders:
    for i in range(NUM_OFFLINE_PER_LEADER):
        username = f"offline_{offline_user_counter}"
        password = "password"
        users_data.append({
            'username': username,
            'password': password,
            'role': 'offline',
            'leader_username': leader_username, # Assign to a leader
            'can_view_funds': 'No' # Offline users cannot view funds
        })
        offline_user_counter += 1

# Add one offline user with no leader for testing edge case
users_data.append({
    'username': 'unassigned_offline',
    'password': 'password',
    'role': 'offline',
    'leader_username': '',
    'can_view_funds': 'No'
})


users_df = pd.DataFrame(users_data)

# --- Generate Performance Data ---
performance_data = []
offline_usernames = users_df[users_df['role'] == 'offline']['username'].tolist()

today = datetime.utcnow()
for i in range(PERFORMANCE_MONTHS):
    current_month = today - timedelta(days=30 * i)
    period = current_month.strftime('%Y-%m')
    for username in offline_usernames:
        # Generate random sales amount for the period
        sales_amount = round(random.uniform(100.0, 5000.0), 2)
        performance_data.append({
            'offline_username': username,
            'period': period,
            'sales_amount': sales_amount
        })

performance_df = pd.DataFrame(performance_data)

# --- Save to Excel ---
output_file = 'fake_affiliate_data.xlsx'
with pd.ExcelWriter(output_file) as writer:
    users_df.to_excel(writer, sheet_name='Users', index=False)
    performance_df.to_excel(writer, sheet_name='Performance', index=False)

print(f"Fake data generated and saved to '{output_file}'")
