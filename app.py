import requests

MOODLE_URL = "http://localhost/webservice/rest/server.php"
TOKEN = "dc987ed23f38ab70084cb6a17dbd377c"

def call_moodle(function, **params):
    payload = {
        "wstoken": TOKEN,
        "wsfunction": function,
        "moodlewsrestformat": "json"
    }
    payload.update(params)
    response = requests.post(MOODLE_URL, data=payload)
    try:
        return response.json()
    except Exception as e:
        print("Moodle response was not JSON. Status code:", response.status_code)
        print("Response text:\n", response.text)
        raise

# 1. Create course
course = call_moodle("core_course_create_courses",
    courses=[{
        "fullname": "My Auto Course",
        "shortname": "AUTO101",
        "categoryid": 1
    }]
)
course_id = course[0]["id"]

# 2. Create sections
for i in range(1, 22):  # 21 sections
    call_moodle("core_course_create_sections",
        courseid=course_id,
        sections=[{"name": f"Activity {i:02d}", "section": i}]
    )

# 3. Add quiz + label inside each section
for i in range(1, 22):
    # Add quiz
    call_moodle("mod_quiz_add_quiz",
        courseid=course_id,
        name=f"Quiz {i:02d}",
        section=i
    )
    # Add label (text/media area)
    call_moodle("core_course_add_content_item_to_section",
        courseid=course_id,
        section=i,
        itemtype="label",
        content={"text": f"This is text for Quiz {i:02d}"}
    )
