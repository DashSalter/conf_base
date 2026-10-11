import subprocess

"""重新打包"""

subprocess.run(
    ['.venv/Scripts/python', '-m', 'build'],
    check=True
)

import shutil

shutil.rmtree('build', ignore_errors=True)
shutil.rmtree('conf_base.egg-info', ignore_errors=True)
