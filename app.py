"""
Moodle Course Automation
========================
Creates a course with N sections, each containing:
  - A Quiz
  - A Label (text/media area with embedded YouTube video)

Uses Selenium browser automation because standard Moodle Web Service
APIs do NOT have functions to add quiz/label modules.
"""

import csv
import re
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ─── Configuration ───────────────────────────────────────────────────────────
MOODLE_BASE = "http://localhost"  # local testing; change to "https://samanalaeschool.lk" for production
ADMIN_USER = "admin"          # ← your Moodle admin username
ADMIN_PASS = "Sanjaya11@"  # ← your Moodle admin password
WAIT = 20  # max seconds to wait for page elements


# ─── Helpers ─────────────────────────────────────────────────────────────────

def extract_youtube_id(url: str) -> str | None:
    m = re.search(
        r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/))([A-Za-z0-9_-]{11})",
        url,
    )
    return m.group(1) if m else None


# ─── Gather user input ──────────────────────────────────────────────────────
print("═══════════════════════════════════")
print("   Moodle Course Creator")
print("═══════════════════════════════════\n")

course_fullname = '04 ශ්‍රේණිය ගණිත ගැටලු Module 2'
course_shortname = '4 ගණිත ගැටලු Module 2'
csv_file = 'Ganith Gatalu Feb - Module 2.csv'

# course_fullname = input("Course full name: ").strip()
# course_shortname = input("Course short name (unique code): ").strip()
# csv_file = input("CSV file path (activity name, youtube link): ").strip().strip('"')

# Read sections from CSV
if not os.path.isfile(csv_file):
    print(f"❌ File not found: {csv_file}")
    exit(1)

sections_data: list[dict] = []
with open(csv_file, newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 2:
            sections_data.append({"name": row[0].strip(), "yt_link": row[1].strip()})
        elif len(row) == 1:
            sections_data.append({"name": row[0].strip(), "yt_link": ""})

num_sections = len(sections_data)

if num_sections == 0:
    print("❌ CSV file is empty!")
    exit(1)

print(f"\n📋 Loaded {num_sections} sections from CSV:")
for i, sec in enumerate(sections_data, 1):
    yt_short = sec["yt_link"][:50] + "…" if len(sec["yt_link"]) > 50 else sec["yt_link"]
    print(f"   {i:02d}. {sec['name']}  →  {yt_short or '(no video)'}")

print(f"\n🚀 Launching browser …\n")

# ─── Launch Chrome ───────────────────────────────────────────────────────────
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options,
)
wait = WebDriverWait(driver, WAIT)


# ─── Step 1: Login ───────────────────────────────────────────────────────────

def moodle_login():
    driver.get(f"{MOODLE_BASE}/login/index.php")
    time.sleep(2)

    # Wait for username field to be visible and interactable
    username_field = wait.until(EC.element_to_be_clickable((By.ID, "username")))
    username_field.clear()
    username_field.send_keys(ADMIN_USER)

    # Wait for password field to be visible and interactable
    password_field = wait.until(EC.element_to_be_clickable((By.ID, "password")))
    password_field.clear()
    password_field.send_keys(ADMIN_PASS)

    # Click login
    login_btn = wait.until(EC.element_to_be_clickable((By.ID, "loginbtn")))
    login_btn.click()
    time.sleep(3)

    # Verify login succeeded (check we're no longer on the login page)
    if "/login/" in driver.current_url:
        raise RuntimeError("Login failed – check ADMIN_USER / ADMIN_PASS in the script")

    print("✅ Logged in to Moodle\n")


# ─── Step 2: Create course ──────────────────────────────────────────────────

def create_course() -> int:
    driver.get(f"{MOODLE_BASE}/course/edit.php?category=1")
    wait.until(EC.presence_of_element_located((By.ID, "id_fullname")))

    fn = driver.find_element(By.ID, "id_fullname")
    fn.clear()
    fn.send_keys(course_fullname)

    sn = driver.find_element(By.ID, "id_shortname")
    sn.clear()
    sn.send_keys(course_shortname)

    # Scroll to the "Course format" fieldset and expand it
    try:
        fieldset = driver.find_element(By.ID, "id_courseformathdr")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", fieldset)
        time.sleep(0.5)

        # Click the collapsed toggle link to expand the section
        toggle = fieldset.find_element(
            By.CSS_SELECTOR,
            "a[data-bs-toggle='collapse'][aria-expanded='false']"
        )
        driver.execute_script("arguments[0].click();", toggle)
        time.sleep(1)
    except Exception:
        pass

    # Set number of sections to 0 (sections will be added dynamically later)
    try:
        sel = Select(driver.find_element(By.ID, "id_numsections"))
        sel.select_by_value("0")
    except Exception:
        pass

    # Scroll to the save button and click it
    save_btn = driver.find_element(By.ID, "id_saveanddisplay")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", save_btn)

    wait.until(EC.url_contains("/course/view.php"))

    cid = int(re.search(r"id=(\d+)", driver.current_url).group(1))
    print(f"✅ Course created → ID {cid}\n")
    return cid


# ─── Step 3: Turn editing on ────────────────────────────────────────────────

def turn_editing_on(course_id: int):
    driver.get(f"{MOODLE_BASE}/course/view.php?id={course_id}")
    time.sleep(1)

    # Moodle 4.x toggle switch
    try:
        toggle = driver.find_element(By.CSS_SELECTOR, "input[name='setmode']")
        if not toggle.is_selected():
            driver.execute_script("arguments[0].click();", toggle)
            time.sleep(1)
            print("✅ Editing mode ON\n")
            return
    except Exception:
        pass

    # Moodle 4.x data-action toggle
    try:
        toggle = driver.find_element(By.CSS_SELECTOR, "[data-action='editmode']")
        if toggle.get_attribute("aria-checked") == "false":
            toggle.click()
            time.sleep(1)
            print("✅ Editing mode ON\n")
            return
    except Exception:
        pass

    # Classic button
    try:
        btn = driver.find_element(By.XPATH,
            "//a[contains(text(),'Turn editing on')] | //input[@value='Turn editing on']"
        )
        btn.click()
        time.sleep(1)
        print("✅ Editing mode ON\n")
    except Exception:
        print("⚠️  Could not toggle editing mode – continuing anyway\n")


# ─── Step 4: Rename a section ────────────────────────────────────────────────

def rename_section(course_id: int, section_num: int, new_name: str):
    driver.get(f"{MOODLE_BASE}/course/view.php?id={course_id}")
    time.sleep(1)

    try:
        editable = driver.find_element(
            By.CSS_SELECTOR,
            f"li#section-{section_num} [data-itemtype='sectionname']"
        )
        editable.click()
        time.sleep(0.5)

        inp = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, f"li#section-{section_num} [data-itemtype='sectionname'] input")
        ))
        inp.clear()
        inp.send_keys(new_name)
        inp.send_keys(Keys.RETURN)
        time.sleep(0.5)
        print(f"   ✏️  Section renamed → '{new_name}'")
    except Exception:
        print(f"   ⚠️  Could not inline-rename section {section_num}")


# ─── Step 5: Add activity via the "add module" URL shortcut ──────────────────
# Moodle supports adding modules by navigating directly to:
#   /course/modedit.php?add=<modtype>&course=<id>&section=<num>&return=0
# This skips the chooser dialog entirely.

def add_quiz(course_id: int, section_num: int, quiz_name: str):
    url = f"{MOODLE_BASE}/course/modedit.php?add=quiz&course={course_id}&section={section_num}&return=0"
    driver.get(url)

    name_field = wait.until(EC.presence_of_element_located((By.ID, "id_name")))
    name_field.clear()
    name_field.send_keys(quiz_name)

    # Scroll to save button and click via JS to avoid interception
    try:
        save_btn = driver.find_element(By.ID, "id_submitbutton2")
    except Exception:
        save_btn = driver.find_element(By.ID, "id_submitbutton")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
    time.sleep(0.3)
    driver.execute_script("arguments[0].click();", save_btn)

    wait.until(EC.url_contains("/course/view.php"))
    time.sleep(0.5)
    print(f"   ✅ Quiz '{quiz_name}' added")


def add_label(course_id: int, section_num: int, label_html: str):
    url = f"{MOODLE_BASE}/course/modedit.php?add=label&course={course_id}&section={section_num}&return=0"
    driver.get(url)
    time.sleep(1)

    # The label editor field – try multiple approaches
    try:
        # Atto editor: contenteditable div
        editor = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "[id^='id_introeditor'] [contenteditable='true'], .editor_atto_content")
        ))
        driver.execute_script("arguments[0].innerHTML = arguments[1];", editor, label_html)
    except Exception:
        try:
            # TinyMCE: switch to iframe
            iframe = driver.find_element(By.CSS_SELECTOR, "#id_introeditor_ifr, .tox-edit-area__iframe")
            driver.switch_to.frame(iframe)
            body = driver.find_element(By.TAG_NAME, "body")
            driver.execute_script("arguments[0].innerHTML = arguments[1];", body, label_html)
            driver.switch_to.default_content()
        except Exception:
            try:
                # Plain textarea fallback
                ta = driver.find_element(By.ID, "id_introeditor")
                ta.clear()
                ta.send_keys(label_html)
            except Exception:
                print("   ⚠️  Could not fill label editor")

    # Save
    try:
        save_btn = driver.find_element(By.ID, "id_submitbutton2")
    except Exception:
        save_btn = driver.find_element(By.ID, "id_submitbutton")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
    time.sleep(0.3)
    driver.execute_script("arguments[0].click();", save_btn)

    wait.until(EC.url_contains("/course/view.php"))
    time.sleep(0.5)
    print(f"   ✅ Label (YouTube video) added")


# ─── Run ─────────────────────────────────────────────────────────────────────
try:
    moodle_login()
    course_id = create_course()
    turn_editing_on(course_id)

    for i, sec in enumerate(sections_data, start=1):
        print(f"\n📂 Section {i:02d}: {sec['name']}")

        rename_section(course_id, i, sec["name"])
        add_quiz(course_id, i, f"Quiz {i:02d}")

        if sec["yt_link"]:
            yt_id = extract_youtube_id(sec["yt_link"])
            if yt_id:
                html = (
                    f'<p>Quiz {i:02d} සඳහා video පාඩම</p>'
                    f'<div class="embed-responsive embed-responsive-16by9">'
                    f'<iframe src="https://www.youtube.com/embed/{yt_id}" '
                    f'width="560" height="315" frameborder="0" '
                    f'allow="accelerometer; autoplay; clipboard-write; '
                    f'encrypted-media; gyroscope; picture-in-picture" '
                    f'allowfullscreen></iframe></div>'
                )
            else:
                html = f'<p><a href="{sec["yt_link"]}" target="_blank">{sec["yt_link"]}</a></p>'
            add_label(course_id, i, html)

    print(f"\n{'═'*50}")
    print(f"🎉 Done! Course: {MOODLE_BASE}/course/view.php?id={course_id}")
    print(f"{'═'*50}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    input("\nPress Enter to close browser …")
    driver.quit()
