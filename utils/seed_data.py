# scripts/seed_data.py

import sys
from pathlib import Path

# Ensure imports work whether this script is run from project root or utils/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.department import create_department
from models.user_model import create_user
from models.ward import create_ward

departments = [
    "Road & Infrastructure",
    "Sanitation & Waste Management",
    "Electrical & Street Lighting",
    "Water Supply",
    "Drainage & Sewerage",
    "Public Health",
    "Parks & Gardens",
    "Building & Construction",
    "Traffic & Encroachment"
]

for dept in departments:
    create_department(dept)

print("Departments inserted successfully 🚀")

# Approximate test boundaries for Rajkot city wards (dummy seed polygons).
wards = [
    {
        "name": "Rajkot Central Ward",
        "country": "India",
        "state": "Gujarat",
        "city": "Rajkot",
        "boundary": [
            [70.7900, 22.3050],
            [70.8100, 22.3050],
            [70.8100, 22.3180],
            [70.7900, 22.3180],
            [70.7900, 22.3050],
        ],
    },
    {
        "name": "Rajkot West Ward",
        "country": "India",
        "state": "Gujarat",
        "city": "Rajkot",
        "boundary": [
            [70.7650, 22.3020],
            [70.7900, 22.3020],
            [70.7900, 22.3180],
            [70.7650, 22.3180],
            [70.7650, 22.3020],
        ],
    },
    {
        "name": "Rajkot Far-West Ward",
        "country": "India",
        "state": "Gujarat",
        "city": "Rajkot",
        "boundary": [
            [70.7450, 22.2860],
            [70.7700, 22.2860],
            [70.7700, 22.3040],
            [70.7450, 22.3040],
            [70.7450, 22.2860],
        ],
    },
    {
        "name": "Rajkot East Ward",
        "country": "India",
        "state": "Gujarat",
        "city": "Rajkot",
        "boundary": [
            [70.8100, 22.3020],
            [70.8350, 22.3020],
            [70.8350, 22.3180],
            [70.8100, 22.3180],
            [70.8100, 22.3020],
        ],
    },
    {
        "name": "Rajkot North Ward",
        "country": "India",
        "state": "Gujarat",
        "city": "Rajkot",
        "boundary": [
            [70.7900, 22.3180],
            [70.8100, 22.3180],
            [70.8100, 22.3380],
            [70.7900, 22.3380],
            [70.7900, 22.3180],
        ],
    },
    {
        "name": "Rajkot South Ward",
        "country": "India",
        "state": "Gujarat",
        "city": "Rajkot",
        "boundary": [
            [70.7900, 22.2840],
            [70.8100, 22.2840],
            [70.8100, 22.3050],
            [70.7900, 22.3050],
            [70.7900, 22.2840],
        ],
    },
    {
        "name": "Rajkot South-East Ward",
        "country": "India",
        "state": "Gujarat",
        "city": "Rajkot",
        "boundary": [
            [70.8100, 22.2840],
            [70.8350, 22.2840],
            [70.8350, 22.3020],
            [70.8100, 22.3020],
            [70.8100, 22.2840],
        ],
    },
]

for ward in wards:
    create_ward(ward)

print("Rajkot wards inserted successfully")

users = [
    {
        "name": "Aarav Patel",
        "email": "aarav.patel@example.com",
        "phone": "+91-9876500001",
        "password": "test1234",
        "role": "citizen",
    },
    {
        "name": "Diya Shah",
        "email": "diya.shah@example.com",
        "phone": "+91-9876500002",
        "password": "test1234",
        "role": "citizen",
    },
    {
        "name": "Nikhil Mehta",
        "email": "nikhil.mehta@example.com",
        "phone": "+91-9876500003",
        "password": "test1234",
        "role": "citizen",
    },
    {
        "name": "RMC Admin",
        "email": "admin@rajkotcivic.in",
        "phone": "+91-9876500099",
        "password": "admin1234",
        "role": "admin",
    },
]

for user in users:
    create_user(user)

print("Users inserted successfully")
