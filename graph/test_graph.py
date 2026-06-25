from complaint_processing_graph import complaint_graph

state = {
    "complaint_id": "1",
    "user_id": "u1",
    "description": "road damage",
    "image_url": "test.jpg",
    "lat": 22.69,
    "lon": 72.86,

    "issue_type": None,
    "department_id": None,
    "ward_id": None,
    "officer_id": None,

    "is_duplicate": False,
    "parent_complaint_id": None,

    "status": "PENDING",
    "is_resolved": False,

    "before_image_url": None,
    "after_image_url": None,

    "location_match": None,
    "issue_solved": None
}

result = complaint_graph.invoke(state)

print(result)