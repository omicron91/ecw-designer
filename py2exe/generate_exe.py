import os
import subprocess
import shutil


APP_NAME = "ECW Designer"
MAIN_FILE = "ecw_designer.py"
OUTPUT_DIR = "py2exe"
SPLASH_SCREEN_FILE = "splash.png"
SPEC_FILE_PATH = os.path.join(os.getcwd(), "py2exe", "{0}.spec".format(APP_NAME))


add_binary_args = []

for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".pyd"):
            abs_pyd_path = os.path.join(root, file)
            # Path relative to py2exe (the cwd for subprocess)
            rel_pyd_path = os.path.relpath(abs_pyd_path, OUTPUT_DIR).replace("\\", "/")
            dest_dir = os.path.dirname(os.path.relpath(abs_pyd_path, "src")).replace("\\", "/")
            if not dest_dir:
                dest_dir = "."
            add_binary_args.append(f'--add-binary={rel_pyd_path}:{dest_dir}/')

# print(add_binary_args)
# import sys
# sys.exit()

# CREATE .SPEC
subprocess.run(
    [
        "pyi-makespec",
        "--noconsole",
        "--icon={0}".format(os.path.join(os.getcwd(), "src", "assets", "icons", "designer.ico")),
        "--splash={0}".format(os.path.join(os.getcwd(), "src", "assets", "splash_screen", SPLASH_SCREEN_FILE)),
        "--name={0}".format(APP_NAME),
        *add_binary_args,
        "../src/{0}".format(MAIN_FILE)
    ],
    cwd=os.path.join(os.getcwd(), OUTPUT_DIR)
)

# READ .SPEC AND EDIT text_pos & text_color FOR SPLASH PROGRESS
with open(SPEC_FILE_PATH, "r+") as spec_file:
    spec_file_content = spec_file.read()
    if "text_pos=(10, 50)" not in spec_file_content and "text_color='white'" not in spec_file_content:
        spec_file_content = spec_file_content.replace(
            "text_pos=None,",
            "text_pos=(10, 50),\n    text_color='white',"
        )
        spec_file.seek(0)
        spec_file.write(spec_file_content)
        spec_file.truncate()

# CREATE EXE FILE
subprocess.run(
    [
        "pyinstaller",
        "{0}.spec".format(APP_NAME)
    ],
    cwd=os.path.join(os.getcwd(), OUTPUT_DIR)
)

src_folder = os.path.join(os.getcwd(), "src", "assets")
dst_folder = os.path.join(os.getcwd(), OUTPUT_DIR, "dist", APP_NAME, "assets")

# Create assets folder
if not os.path.exists(dst_folder):
    os.mkdir(dst_folder)

# Copy folder to another destination
if os.path.exists(src_folder):
    shutil.copytree(src_folder, dst_folder, dirs_exist_ok=True)
