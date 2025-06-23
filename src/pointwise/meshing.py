import pyautogui
import time
import subprocess
import os

# Adjust these paths to your environment:
pointwise_executable = 'pointwise'
stl_file_path = '17_wheels-front.stl'
project_name = 'AeroSUV-17_wheels-front1'

def start_pointwise():
    print("info: Start Pointwise now!")
    subprocess.Popen([pointwise_executable])
    print("info: Wait 10 seconds for Pointwise to open...")
    time.sleep(10)  # wait for Pointwise GUI to load
    print("info: Pointwise started!")

def create_new_project():
    print("info: Open File menu...")
    pyautogui.hotkey('ctrl', 's')
    time.sleep(1)

    print(f"info: Type project name '{project_name}'")
    pyautogui.write(project_name)
    time.sleep(1)

    print("info: Press Enter to create project")
    pyautogui.press('enter')
    time.sleep(2)

    print("info: Project created!")

def import_stl():
    print("info: Open File menu again to import STL...")
    pyautogui.hotkey('alt', 'f')
    time.sleep(1)

    print("info: Choose Import")
    pyautogui.press('i')
    time.sleep(1)

    print("info: Choose Import")
    pyautogui.press('d')
    time.sleep(1)

    print(f"info: Type STL file path '{stl_file_path}'")
    time.sleep(5)  # wait for file dialog to open
    pyautogui.write(stl_file_path)
    time.sleep(1)

    print("info: Press Enter to load STL")
    pyautogui.press('enter')
    time.sleep(5)  # wait for geometry to load

    print("info: Press Enter to load STL")
    pyautogui.hotkey('ctrl','enter')
    time.sleep(60)  # wait for geometry to load

    print("info: STL loaded!")

    print("info: Open File menu...")
    pyautogui.hotkey('ctrl', 's') #saving
    time.sleep(1)
    print("info: Press Enter to save project")
    pyautogui.press('enter')
    time.sleep(2)

def convert_stl_to_database():
    print("info: Select STL geometry in Pointwise")
    pyautogui.hotkey('alt', 's')  # click on geometry in display window — adjust coords!
    time.sleep(1)

    pyautogui.press('enter')          # enter to complete
    time.sleep(1)
    print("info: Go to Create -> Database -> Entities")
    pyautogui.hotkey('alt', 'c')  # Open "Create" menu
    time.sleep(1)
    pyautogui.press('d')          # D for Database
    time.sleep(1)
    pyautogui.press('e')          # E for Entities
    time.sleep(3)

    print("info: Now we have database model")




def main():
    print("info: Start main script")
    start_pointwise()
    create_new_project()
    import_stl()
    print("info: All done! Project created and STL loaded.")

if __name__ == '__main__':
    main()
