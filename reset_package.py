import subprocess
import shutil

"""重新打包"""

shutil.rmtree('dist', ignore_errors=True)

subprocess.run(
    ['.venv/Scripts/python', '-m', 'build'],
    check=True
)



shutil.rmtree('build', ignore_errors=True)
shutil.rmtree('conf_base.egg-info', ignore_errors=True)
