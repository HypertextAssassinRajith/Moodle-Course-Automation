"""
Moodle Course Automation
========================
Creates a course with N sections, each containing:
  - A Quiz
  - A Label (text/media area with embedded YouTube video)

Uses Selenium browser automation because standard Moodle Web Service
APIs do NOT have functions to add quiz/label modules.
"""

import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ─── Configuration ───────────────────────────────────────────────────────────
MOODLE_BASE = "https://samanalaeschool.lk"
ADMIN_USER = "admin"          # ← your Moodle admin username
ADMIN_PASS = "your_password"  # ← your Moodle admin password
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

course_fullname = input("Course full name: ").strip()
course_shortname = input("Course short name (unique code): ").strip()
num_sections = int(input("How many activity sections? ").strip())

sections_data: list[dict] = []
for i in range(1, num_sections + 1):
    name = input(f"  Section {i:02d} name (Enter for 'ක්‍රියාකාරකම් {i:02d}'): ").strip()
    if not name:
        name = f"ක්‍රියාකාරකම් {i:02d}"
    yt = input(f"  YouTube link for section {i:02d} (Enter to skip): ").strip()
    sections_data.append({"name": name, "yt_link": yt})

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
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(ADMIN_USER)
    driver.find_element(By.ID, "password").send_keys(ADMIN_PASS)
    driver.find_element(By.ID, "loginbtn").click()
    time.sleep(2)
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

    # Expand "Course format" and set number of sections
    try:
        header = driver.find_element(By.XPATH, "//*[contains(@id,'courseformat')]//a | //*[contains(@id,'courseformat')]/..")
        if header.get_attribute("aria-expanded") == "false":
            header.click()
            time.sleep(0.5)
    except Exception:
        pass

    try:
        sel = Select(driver.find_element(By.ID, "id_numsections"))
        sel.select_by_value(str(num_sections))
    except Exception:
        pass

    driver.find_element(By.ID, "id_saveanddisplay").click()
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

    # Save and return to course
    try:
        driver.find_element(By.ID, "id_submitbutton2").click()
    except Exception:
        driver.find_element(By.ID, "id_submitbutton").click()

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
        driver.find_element(By.ID, "id_submitbutton2").click()
    except Exception:
        driver.find_element(By.ID, "id_submitbutton").click()

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
