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
MOODLE_BASE = "https://samanalaeschool.lk"  # local testing; change to "https://samanalaeschool.lk" for production
ADMIN_USER = "rajith"          # ← your Moodle admin username
ADMIN_PASS = "Sanjaya11@"  # ← your Moodle admin password
WAIT = 20  # max seconds to wait for page elements
QUIZ_FOLDER = r'C:\Users\Rajith Sanjaya\OneDrive\Ganith Gatalu\2026\feb\LMS\G4'
QUIZ_XML_PREFIX = "GG2602G04P"  # files are GG2602G04P01.xml, GG2602G04P02.xml, …
course_fullname = '04 ශ්‍රේණිය ගණිත ගැටලු Module 2'
course_shortname = '4 ගණිත ගැටලු Module 2'
csv_file = 'Ganith Gatalu Feb - Module 2.csv'
category='2026/Grade 04/ගණිතය'


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

def select_category_autocomplete():
    """Select the category from Moodle's autocomplete dropdown widget.
    
    The widget structure (IDs are dynamic per page load):
      <input data-fieldtype="autocomplete" role="combobox" ...>
      <span class="form-autocomplete-downarrow ...">▼</span>
    Clicking the ▼ opens:
      <ul class="form-autocomplete-suggestions" role="listbox">
        <li role="option" data-value="10">2026 / Grade 04 / ගණිතය</li>
        ...
      </ul>
    We match by normalising whitespace around '/' separators.
    """
    # Build a normalised version of the target path for comparison
    target_parts = [p.strip() for p in category.split("/")]
    target_norm = " / ".join(target_parts).lower()

    try:
        # Click the ▼ arrow to open the full suggestions list
        arrow = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "span.form-autocomplete-downarrow")
        ))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", arrow)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", arrow)
        time.sleep(1)

        # Find all <li role="option"> in the suggestions list
        options = wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "ul.form-autocomplete-suggestions li[role='option']")
        ))

        for opt in options:
            opt_text = " ".join(opt.text.split()).strip()  # collapse whitespace
            opt_norm = opt_text.lower()
            if target_norm == opt_norm:
                # Exact match – click this option
                driver.execute_script("arguments[0].click();", opt)
                time.sleep(0.5)
                print(f"   📁 Category selected: {opt_text}")
                return True

        # No exact match – try partial (target contained in option text)
        for opt in options:
            opt_text = " ".join(opt.text.split()).strip()
            opt_norm = opt_text.lower()
            if target_norm in opt_norm or opt_norm in target_norm:
                driver.execute_script("arguments[0].click();", opt)
                time.sleep(0.5)
                print(f"   📁 Category selected: {opt_text}")
                return True

        # Last resort – match by data-value using JS to find the right option
        # and click it programmatically
        leaf = target_parts[-1].lower()
        for opt in options:
            opt_text = " ".join(opt.text.split()).strip().lower()
            if leaf in opt_text:
                driver.execute_script("arguments[0].click();", opt)
                time.sleep(0.5)
                print(f"   📁 Category selected (leaf match): {opt.text.strip()}")
                return True

    except Exception as e:
        print(f"   ⚠️  Category autocomplete error: {e}")

    print(f"   ⚠️  Could not select category '{category}' – using default")
    return False


def create_course() -> int:
    driver.get(f"{MOODLE_BASE}/course/edit.php?category=1")
    wait.until(EC.presence_of_element_located((By.ID, "id_fullname")))

    # Select category from the autocomplete dropdown widget
    select_category_autocomplete()

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
            By.CSS_SELECTOR,"a[data-bs-toggle='collapse'][aria-expanded='false']"
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


# ─── Step 4: Add a new section and rename it ─────────────────────────────────

def create_section(course_id: int, section_num: int, new_name: str):
    """Click 'Add section' to create a new section, then rename it via the pencil icon."""
    driver.get(f"{MOODLE_BASE}/course/view.php?id={course_id}")
    time.sleep(1)

    # --- Click "Add section" button ---
    try:
        add_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "a[data-action='addSection']")
        ))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", add_btn)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", add_btn)
        time.sleep(2)  # wait for new section to appear
    except Exception:
        # Fallback: direct URL
        try:
            sesskey = driver.execute_script(
                "return document.querySelector('input[name=\"sesskey\"]')?.value || M.cfg.sesskey;"
            )
            driver.get(
                f"{MOODLE_BASE}/course/changenumsections.php?courseid={course_id}"
                f"&insertsection=0&sesskey={sesskey}"
            )
            time.sleep(2)
        except Exception:
            print(f"   ⚠️  Could not add section {section_num}")
            return

    # --- Rename the newly added section via pencil icon ---
    # The new section is the last li[id^='section-'] on the page
    driver.get(f"{MOODLE_BASE}/course/view.php?id={course_id}")
    time.sleep(1)

    try:
        # Find the last section's pencil icon
        section = driver.find_element(
            By.CSS_SELECTOR,
            f"li#section-{section_num} .quickediticon"
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", section)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", section)
        time.sleep(0.5)

        # Wait for the inline input field to appear and type the new name
        inp = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, f"li#section-{section_num} .inplaceeditable input[type='text']")
        ))
        inp.clear()
        inp.send_keys(new_name)
        inp.send_keys(Keys.RETURN)
        time.sleep(0.5)
        print(f"   ✏️  Section {section_num} created & renamed → '{new_name}'")
    except Exception:
        # Fallback: try editsection.php
        try:
            section_el = driver.find_element(By.CSS_SELECTOR, f"li#section-{section_num}")
            section_db_id = section_el.get_attribute("data-id") or section_el.get_attribute("data-sectionid")
            if section_db_id:
                driver.get(f"{MOODLE_BASE}/course/editsection.php?id={section_db_id}")
                time.sleep(1)
                # Uncheck "Use default section name" if present
                try:
                    cb = driver.find_element(By.ID, "id_name_customize")
                    if not cb.is_selected():
                        driver.execute_script("arguments[0].click();", cb)
                        time.sleep(0.3)
                except Exception:
                    pass
                name_field = wait.until(EC.presence_of_element_located((By.ID, "id_name_value")))
                name_field.clear()
                name_field.send_keys(new_name)
                save_btn = driver.find_element(By.ID, "id_submitbutton")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", save_btn)
                wait.until(EC.url_contains("/course/view.php"))
                time.sleep(0.5)
                print(f"   ✏️  Section {section_num} created & renamed (via edit page) → '{new_name}'")
            else:
                print(f"   ⚠️  Section {section_num} created but could not rename")
        except Exception:
            print(f"   ⚠️  Section {section_num} created but could not rename")


# ─── Step 5: Add activity via the "add module" URL shortcut ──────────────────
# Moodle supports adding modules by navigating directly to:
#   /course/modedit.php?add=<modtype>&course=<id>&section=<num>&return=0
# This skips the chooser dialog entirely.

def add_quiz(course_id: int, section_num: int, quiz_name: str) -> int | None:
    """Create a quiz and click 'Save and display'. Returns the cmid from the URL."""
    url = f"{MOODLE_BASE}/course/modedit.php?add=quiz&course={course_id}&section={section_num}&return=0"
    driver.get(url)

    name_field = wait.until(EC.presence_of_element_located((By.ID, "id_name")))
    name_field.clear()
    name_field.send_keys(quiz_name)

    # Click "Save and display" (id_submitbutton) instead of "Save and return to course"
    save_btn = driver.find_element(By.ID, "id_submitbutton")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
    time.sleep(0.3)
    driver.execute_script("arguments[0].click();", save_btn)

    # Wait for the quiz view page to load
    wait.until(EC.url_contains("/mod/quiz/view.php"))
    time.sleep(1)

    # Extract cmid from URL (e.g. /mod/quiz/view.php?id=1233)
    cmid_match = re.search(r"id=(\d+)", driver.current_url)
    cmid = int(cmid_match.group(1)) if cmid_match else None
    print(f"   ✅ Quiz '{quiz_name}' added (cmid={cmid})")
    return cmid


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


# ─── Step 6: Import questions from XML via Question Bank tab ──────────────────

def import_questions_from_xml(cmid: int, xml_path: str, quiz_name: str = ""):
    """Navigate to quiz → Question bank tab → Import dropdown → upload XML."""
    # Go to the quiz view page
    driver.get(f"{MOODLE_BASE}/mod/quiz/view.php?id={cmid}")
    time.sleep(1)

    # Click the "Question bank" tab
    try:
        qb_tab = wait.until(EC.element_to_be_clickable(
            (By.XPATH,
             "//a[contains(text(),'Question bank')] | "
             "//a[contains(@href,'question/edit.php')]")
        ))
        driver.execute_script("arguments[0].click();", qb_tab)
        time.sleep(1)
    except Exception:
        # Direct fallback: go to question bank page
        driver.get(f"{MOODLE_BASE}/question/edit.php?cmid={cmid}")
        time.sleep(1)

    # Select "Import" from the question bank dropdown
    try:
        qb_select = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "select.urlselect[name='jump']")
        ))
        import_option_value = None
        for opt in qb_select.find_elements(By.TAG_NAME, "option"):
            if "import" in opt.get_attribute("value").lower():
                import_option_value = opt.get_attribute("value")
                break

        if import_option_value:
            sel = Select(qb_select)
            sel.select_by_value(import_option_value)
            time.sleep(1)
            # The urlselect triggers navigation automatically, but just in case:
            if "import" not in driver.current_url.lower():
                driver.get(f"{MOODLE_BASE}{import_option_value}")
                time.sleep(1)
        else:
            # Fallback: navigate directly
            driver.get(f"{MOODLE_BASE}/question/bank/importquestions/import.php?cmid={cmid}")
            time.sleep(1)
    except Exception:
        driver.get(f"{MOODLE_BASE}/question/bank/importquestions/import.php?cmid={cmid}")
        time.sleep(1)

    # Select "Moodle XML format"
    try:
        fmt_radio = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[name='format'][value='xml']")
        ))
        driver.execute_script("arguments[0].click();", fmt_radio)
        time.sleep(0.3)
    except Exception:
        # Try selecting from a dropdown if it's not radio buttons
        try:
            sel = Select(driver.find_element(By.ID, "id_format"))
            sel.select_by_value("xml")
        except Exception:
            print(f"   ⚠️  Could not select XML format")
            return False

    # Select the import category: "Default for <quiz_name>"
    if quiz_name:
        try:
            # Expand the "General" fieldset if it's collapsed
            try:
                general_toggle = driver.find_element(
                    By.CSS_SELECTOR,
                    "a[href='#id_generalcontainer'][aria-expanded='false']"
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", general_toggle)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", general_toggle)
                time.sleep(1)
            except Exception:
                pass  # Already expanded or different structure

            # Uncheck "Get the category from the file" (id_catfromfile)
            try:
                catfromfile = driver.find_element(By.ID, "id_catfromfile")
                if catfromfile.is_selected():
                    driver.execute_script("arguments[0].click();", catfromfile)
                    time.sleep(0.3)
            except Exception:
                pass

            # Uncheck "Get the context from the file" (id_contextfromfile)
            try:
                contextfromfile = driver.find_element(By.ID, "id_contextfromfile")
                if contextfromfile.is_selected():
                    driver.execute_script("arguments[0].click();", contextfromfile)
                    time.sleep(0.3)
            except Exception:
                pass

            # Now select the category from the dropdown
            cat_select = Select(driver.find_element(By.ID, "id_category"))
            target_text = f"Default for {quiz_name}"
            matched = False
            for opt in cat_select.options:
                opt_text = opt.text.strip()
                if target_text in opt_text:
                    cat_select.select_by_value(opt.get_attribute("value"))
                    matched = True
                    print(f"   📁 Import category: {opt_text}")
                    break
            if not matched:
                print(f"   ⚠️  Could not find category '{target_text}' – using default")
            time.sleep(0.5)
        except Exception:
            print(f"   ⚠️  Could not select import category – using default")

    # Upload the file via "Choose a file..." button → Moodle file picker
    try:
        # Click the "Choose a file..." button to open the file picker dialog
        choose_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "input.fp-btn-choose[type='button']")
        ))
        driver.execute_script("arguments[0].click();", choose_btn)
        time.sleep(2)

        # In the file picker dialog, click "Upload a file" in the left panel
        upload_link = wait.until(EC.element_to_be_clickable(
            (By.XPATH,
             "//span[contains(@class,'fp-repo-name') and contains(text(),'Upload a file')] | "
             "//a[contains(@class,'fp-repo-name') and contains(text(),'Upload a file')] | "
             "//span[contains(text(),'Upload a file')]")
        ))
        driver.execute_script("arguments[0].click();", upload_link)
        time.sleep(1)

        # Find the actual file input inside the file picker dialog and send the file path
        file_input = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, ".fp-upload-form input[type='file'], .file-picker input[type='file'], input[type='file'][name='repo_upload_file']")
        ))
        file_input.send_keys(xml_path)
        time.sleep(2)

        # Click "Upload this file" button in the dialog
        upload_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, ".fp-upload-btn, .fp-upload-form .btn-primary")
        ))
        driver.execute_script("arguments[0].click();", upload_btn)
        time.sleep(3)
    except Exception:
        # Last resort: try to find any hidden file input on the page
        try:
            file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            file_input.send_keys(xml_path)
            time.sleep(3)
        except Exception:
            print(f"   ⚠️  Could not upload file")
            return False

    # Click the Import button
    try:
        import_btn = driver.find_element(By.ID, "id_submitbutton")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", import_btn)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", import_btn)
        time.sleep(3)
    except Exception:
        print(f"   ⚠️  Could not click Import button")
        return False

    # After import, Moodle shows a results page with a "Continue" button
    try:
        continue_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'Continue')] | //a[contains(text(),'Continue')] | //input[@value='Continue']")
        ))
        driver.execute_script("arguments[0].click();", continue_btn)
        time.sleep(1)
    except Exception:
        pass  # May not always have a continue button

    print(f"   ✅ Questions imported from {os.path.basename(xml_path)}")
    return True


# ─── Step 7: Add all imported questions to a quiz ────────────────────────────

def add_all_questions_to_quiz(cmid: int):
    """Go to Questions tab (quiz edit page), click Add → from question bank,
    select all questions and add them to the quiz.
    Handles pagination: if there are multiple pages of questions,
    repeats the Add → from question bank → select all → add flow for each page."""

    page = 1
    while True:
        # Navigate to the quiz edit page
        driver.get(f"{MOODLE_BASE}/mod/quiz/edit.php?cmid={cmid}")
        time.sleep(1)

        # Click the "Add" dropdown button
        try:
            add_dropdown = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR,
                 "a.dropdown-toggle[aria-label='Add'], "
                 "#action-menu-toggle-1, "
                 ".add-menu-outer a.dropdown-toggle")
            ))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", add_dropdown)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", add_dropdown)
            time.sleep(1)
        except Exception:
            print(f"   ⚠️  Could not find 'Add' dropdown")
            return

        # Click "from question bank" in the dropdown menu
        try:
            from_bank = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR,
                 "a[data-action='questionbank'], "
                 "a.questionbank.menu-action")
            ))
            driver.execute_script("arguments[0].click();", from_bank)
            time.sleep(2)
        except Exception:
            print(f"   ⚠️  Could not find 'from question bank' option")
            return

        # If this is page 2+, click the correct page number in the pagination
        if page > 1:
            try:
                page_link = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR,
                     f".categoryquestionscontainer li.page-item[data-page-number='{page}'] a.page-link")
                ))
                driver.execute_script("arguments[0].click();", page_link)
                time.sleep(2)
            except Exception:
                # No more pages – we're done
                print(f"   ✅ All questions added to quiz (no page {page})")
                return

        # Check if there are any question checkboxes on this page
        checkboxes = driver.find_elements(
            By.CSS_SELECTOR,
            "#categoryquestions input[type='checkbox'][id^='checkq']"
        )
        if not checkboxes:
            if page == 1:
                print(f"   ⚠️  No questions found in question bank")
            return

        # Select all questions using the "select all" header checkbox
        try:
            select_all = driver.find_element(By.ID, "qbheadercheckbox")
            if not select_all.is_selected():
                driver.execute_script("arguments[0].click();", select_all)
                time.sleep(0.5)
        except Exception:
            # Fallback: click each checkbox individually
            for cb in checkboxes:
                if not cb.is_selected():
                    driver.execute_script("arguments[0].click();", cb)
            time.sleep(0.5)

        num_selected = len(checkboxes)

        # Click "Add selected questions to the quiz"
        try:
            add_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH,
                 "//input[@value='Add selected questions to the quiz'] | "
                 "//button[contains(text(),'Add selected questions')] | "
                 "//input[contains(@value,'Add to quiz')] | "
                 "//button[contains(text(),'Add to quiz')]")
            ))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", add_btn)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", add_btn)
            time.sleep(2)
        except Exception:
            print(f"   ⚠️  Could not add questions to quiz (page {page})")
            return

        print(f"   ✅ Added {num_selected} questions from page {page}")

        # Check if there's a next page: look for a non-active page item
        # with a page number greater than the current page
        has_next = driver.find_elements(
            By.CSS_SELECTOR,
            f".categoryquestionscontainer li.page-item[data-page-number='{page + 1}']"
        )
        if not has_next:
            # Also check before we added — the dialog is now closed,
            # so we can't check. We'll try and the page_link click above
            # will fail gracefully if there's no next page.
            # Use a simple heuristic: if we selected exactly 20 (page size),
            # there might be more.
            if num_selected < 20:
                break
        
        page += 1

    print(f"   ✅ All questions added to quiz")


# ─── Step 8: Export (backup) the course to a .mbz file ───────────────────────

def export_course(course_id: int):
    """Walk through Moodle's backup wizard to download the course as .mbz.
    
    The wizard has these steps:
      1. Initial settings  → click "Next"
      2. Schema settings   → click "Next"
      3. Confirmation      → click "Perform backup"
      4. Complete          → click "Continue"
      5. User-data area    → click "Download" on the latest backup file
    """
    import glob

    print(f"\n📦 Exporting course (ID {course_id}) …")

    # Step 1: Go to backup page
    driver.get(f"{MOODLE_BASE}/backup/backup.php?id={course_id}")
    time.sleep(2)

    # Step 1→2: Click "Next" on initial settings
    try:
        next_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "input[type='submit'][value='Next'], button[type='submit']")
        ))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", next_btn)
        time.sleep(2)
    except Exception:
        print("   ⚠️  Could not proceed past initial settings")
        return None

    # Step 2→3: Click "Next" on schema settings
    try:
        next_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "input[type='submit'][value='Next'], button[type='submit']")
        ))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", next_btn)
        time.sleep(2)
    except Exception:
        print("   ⚠️  Could not proceed past schema settings")
        return None

    # Step 3→4: Click "Perform backup"
    try:
        perform_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR,
             "input[type='submit'][value='Perform backup'], "
             "button[type='submit']")
        ))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", perform_btn)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", perform_btn)
        # Backup can take a while
        time.sleep(5)
    except Exception:
        print("   ⚠️  Could not click 'Perform backup'")
        return None

    # Wait for backup to complete — look for success message
    try:
        wait.until(EC.presence_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'completed successfully')] | "
             "//*[contains(text(),'backup completed')]")
        ))
    except Exception:
        # May already be done, continue anyway
        pass

    # Step 4→5: Click "Continue"
    try:
        continue_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH,
             "//button[contains(text(),'Continue')] | "
             "//a[contains(text(),'Continue')] | "
             "//input[@value='Continue']")
        ))
        driver.execute_script("arguments[0].click();", continue_btn)
        time.sleep(2)
    except Exception:
        # Navigate directly to the restore/backup file area
        driver.get(f"{MOODLE_BASE}/backup/restorefile.php?contextid={course_id}")
        time.sleep(2)

    # Step 5: Download the backup file
    # We're now on the backup files page — find the "Download" link for the latest .mbz
    try:
        download_link = wait.until(EC.element_to_be_clickable(
            (By.XPATH,
             "//a[contains(text(),'Download')] | "
             "//a[contains(@href,'.mbz')] | "
             "//a[contains(@href,'backupfilearea')]")
        ))
        download_url = download_link.get_attribute("href")
        driver.execute_script("arguments[0].click();", download_link)
        time.sleep(3)

        # Wait for download to finish — check browser's download directory
        # Give it some extra time for larger courses
        time.sleep(5)

        print(f"   ✅ Course backup downloaded!")
        print(f"   📥 Check your browser's Downloads folder for the .mbz file")

        # Try to find the downloaded file in common download locations
        download_dirs = [
            os.path.expanduser("~/Downloads"),
            os.path.expandvars(r"%USERPROFILE%\Downloads"),
        ]
        for dl_dir in download_dirs:
            if os.path.isdir(dl_dir):
                mbz_files = glob.glob(os.path.join(dl_dir, "backup-moodle2-course-*.mbz"))
                if mbz_files:
                    latest = max(mbz_files, key=os.path.getmtime)
                    print(f"   📁 File: {latest}")
                    return latest

        return download_url

    except Exception:
        print("   ⚠️  Could not find download link — trying direct download via URL")
        # Fallback: try to get the backup file URL from the page
        try:
            file_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='.mbz']")
            if file_links:
                driver.execute_script("arguments[0].click();", file_links[0])
                time.sleep(5)
                print(f"   ✅ Course backup download initiated")
                return True
        except Exception:
            pass

        print("   ⚠️  Could not download course backup automatically")
        print(f"   💡 You can manually export from: {MOODLE_BASE}/backup/backup.php?id={course_id}")
        return None


# ─── Run ─────────────────────────────────────────────────────────────────────
try:
    moodle_login()
    course_id = create_course()
    turn_editing_on(course_id)

    for i, sec in enumerate(sections_data, start=1):
        print(f"\n📂 Section {i:02d}: {sec['name']}")

        create_section(course_id, i, sec["name"])
        quiz_name = f"ප්‍රශ්නාවලිය {i:02d}"
        cmid = add_quiz(course_id, i, quiz_name)

        # Import questions from XML and add to quiz
        xml_file = os.path.join(QUIZ_FOLDER, f"{QUIZ_XML_PREFIX}{i:02d}.xml")
        if cmid and os.path.isfile(xml_file):
            if import_questions_from_xml(cmid, xml_file, quiz_name):
                add_all_questions_to_quiz(cmid)
        elif not os.path.isfile(xml_file):
            print(f"   ⚠️  XML file not found: {os.path.basename(xml_file)}")

        if sec["yt_link"]:
            yt_id = extract_youtube_id(sec["yt_link"])
            if yt_id:
                html = (
                    f'<p>ප්‍රශ්නාවලිය {i:02d} සඳහා video පාඩම</p>'
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

    # Export the course to .mbz for uploading to another Moodle instance
    export_course(course_id)

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
